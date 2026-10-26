#!/usr/bin/env python3
"""Export one HOI bundle to compact browser-readable geometry buffers."""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
import sys
import types

import numpy as np
import torch
import trimesh


class _LegacyCh:
    def __setstate__(self, state: dict) -> None:
        self.__dict__.update(state)

    def array(self) -> np.ndarray:
        for name in ("r", "x"):
            if name in self.__dict__:
                return np.asarray(self.__dict__[name])
        raise ValueError("unsupported legacy Chumpy state")


class _LegacySelect(_LegacyCh):
    def array(self) -> np.ndarray:
        base = self.a.array() if isinstance(self.a, _LegacyCh) else np.asarray(self.a)
        return base.ravel()[np.asarray(self.idxs)].reshape(self.preferred_shape)


def load_mano_pickle(path: Path) -> dict:
    previous = {name: sys.modules.get(name) for name in ("chumpy", "chumpy.ch", "chumpy.reordering")}
    chumpy = types.ModuleType("chumpy")
    ch = types.ModuleType("chumpy.ch")
    reordering = types.ModuleType("chumpy.reordering")
    _LegacyCh.__module__ = "chumpy.ch"
    _LegacySelect.__module__ = "chumpy.reordering"
    ch.Ch = _LegacyCh
    reordering.Select = _LegacySelect
    chumpy.ch, chumpy.reordering = ch, reordering
    sys.modules.update({"chumpy": chumpy, "chumpy.ch": ch, "chumpy.reordering": reordering})
    try:
        with path.open("rb") as stream:
            value = pickle.load(stream, encoding="latin1")
    finally:
        for name, old_value in previous.items():
            if old_value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old_value
    return {key: item.array() if isinstance(item, _LegacyCh) else item for key, item in value.items()}


def mano_model_path(mano_dir: Path) -> Path:
    """Return the MANO model used by the prediction producer.

    Dyn-HaMR represents both handednesses with the right-hand MANO model and
    mirrors the decoded output for left hands.  Loading MANO_LEFT directly
    changes the meaning of the exported axis-angle pose parameters.
    """
    return mano_dir / "MANO_RIGHT.pkl"


def apply_handedness(vertices: np.ndarray, side: str) -> np.ndarray:
    """Convert the producer's right-hand MANO output to the requested side."""
    if side not in {"left", "right"}:
        raise ValueError(f"unsupported hand side: {side!r}")
    if side == "left":
        vertices[..., 0] *= -1
    return vertices


def decode_hand(
    result_dir: Path, mano_dir: Path, frame_count: int, hand_side: str | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import smplx
    from smplx.utils import Struct

    source = np.load(result_dir / "hand_results.npz", allow_pickle=False)
    handedness = [str(value).lower() for value in source["handedness"]]
    if hand_side is None:
        if len(source["track_indices"]) != 1:
            raise ValueError("multiple hand tracks require --hand-side")
        track_index = 0
    else:
        matches = [index for index, side in enumerate(handedness) if side == hand_side]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one {hand_side!r} hand track, found {len(matches)}")
        track_index = matches[0]
    side = handedness[track_index]
    mano_path = mano_model_path(mano_dir)
    data = load_mano_pickle(mano_path)
    model = smplx.MANO(
        str(mano_path), data_struct=Struct(**data), is_rhand=True, use_pca=False,
        flat_hand_mean=True, create_hand_pose=False,
    ).eval()
    frames = len(source["frame_indices"])
    tensor = lambda value: torch.as_tensor(value, dtype=torch.float32)
    with torch.inference_mode():
        output = model(
            global_orient=tensor(source["root_orient_camera"][track_index]).reshape(frames, 3),
            hand_pose=tensor(source["pose_body"][track_index]).reshape(frames, 45),
            betas=tensor(np.broadcast_to(source["betas"][track_index], (frames, 10)).copy()),
            transl=tensor(source["trans_camera"][track_index]).reshape(frames, 3),
            return_verts=True,
        )
    decoded = apply_handedness(output.vertices.cpu().numpy().astype("<f4"), side)
    vertices = np.full((frame_count, decoded.shape[1], 3), np.nan, dtype="<f4")
    frame_indices = np.asarray(source["frame_indices"], dtype=int)
    vertices[frame_indices] = decoded
    valid = np.isfinite(vertices).all(axis=(1, 2))
    return vertices, np.asarray(model.faces, dtype="<u2"), valid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--mano-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hand-side", choices=("left", "right"))
    args = parser.parse_args()
    result_dir = args.result_dir.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    scene = np.load(result_dir / "scene.npz", allow_pickle=False)
    obj = np.load(result_dir / "object_results.npz", allow_pickle=False)
    frame_count = len(scene["frame_indices"])
    hand_vertices, hand_faces, hand_valid = decode_hand(
        result_dir, args.mano_dir.resolve(), frame_count, args.hand_side,
    )
    object_path = result_dir / "object_mesh" / "mesh.obj"
    object_mesh = trimesh.load(object_path, force="mesh", process=False)
    object_vertices = np.asarray(object_mesh.vertices, dtype="<f4")
    object_faces = np.asarray(object_mesh.faces, dtype="<u2")
    object_poses = np.asarray(obj["poses_camera"], dtype="<f4")
    object_valid = np.isfinite(object_poses).all(axis=(1, 2))

    assets = {
        "hand-vertices.bin": hand_vertices,
        "hand-faces.bin": hand_faces,
        "object-vertices.bin": object_vertices,
        "object-faces.bin": object_faces,
        "object-poses.bin": object_poses,
    }
    for name, array in assets.items():
        (output / name).write_bytes(array.tobytes(order="C"))

    height, width = 480, 640
    metadata = {
        "schemaVersion": 1,
        "coordinateConvention": "opencv-camera-x-right-y-down-z-forward-meters",
        "frameCount": int(len(hand_vertices)),
        "imageWidth": width,
        "imageHeight": height,
        "intrinsics": np.asarray(scene["intrinsics"], dtype=float).tolist(),
        "hand": {
            "vertices": "hand-vertices.bin",
            "faces": "hand-faces.bin",
            "vertexCount": int(hand_vertices.shape[1]),
            "faceCount": int(hand_faces.shape[0]),
            "valid": hand_valid.tolist(),
        },
        "object": {
            "vertices": "object-vertices.bin",
            "faces": "object-faces.bin",
            "poses": "object-poses.bin",
            "vertexCount": int(len(object_vertices)),
            "faceCount": int(len(object_faces)),
            "valid": object_valid.tolist(),
        },
    }
    (output / "reconstruction.json").write_text(json.dumps(metadata, separators=(",", ":")) + "\n")
    print(f"Exported {len(hand_vertices)} frames to {output}")


if __name__ == "__main__":
    main()
