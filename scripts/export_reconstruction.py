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


def decode_hand(bundle: Path, mano_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import smplx
    from smplx.utils import Struct

    source = np.load(bundle / "input" / "final" / "hand_results.npz", allow_pickle=False)
    if len(source["track_indices"]) != 1:
        raise ValueError("the initial browser exporter requires exactly one hand track")
    data = load_mano_pickle(mano_path)
    model = smplx.MANO(
        str(mano_path), data_struct=Struct(**data), is_rhand=True, use_pca=False,
        flat_hand_mean=True, create_hand_pose=False,
    ).eval()
    frames = len(source["frame_indices"])
    tensor = lambda value: torch.as_tensor(value, dtype=torch.float32)
    with torch.inference_mode():
        output = model(
            global_orient=tensor(source["root_orient_camera"][0]).reshape(frames, 3),
            hand_pose=tensor(source["pose_body"][0]).reshape(frames, 45),
            betas=tensor(np.broadcast_to(source["betas"][0], (frames, 10)).copy()),
            transl=tensor(source["trans_camera"][0]).reshape(frames, 3),
            return_verts=True,
        )
    vertices = output.vertices.cpu().numpy().astype("<f4")
    is_right = source["is_right"][0].astype(bool)
    vertices[~is_right, :, 0] *= -1
    valid = np.isfinite(vertices).all(axis=(1, 2))
    return vertices, np.asarray(model.faces, dtype="<u2"), valid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--mano", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    hand_vertices, hand_faces, hand_valid = decode_hand(bundle, args.mano.resolve())
    scene = np.load(bundle / "input" / "final" / "scene.npz", allow_pickle=False)
    obj = np.load(bundle / "input" / "final" / "object_results.npz", allow_pickle=False)
    object_path = next((bundle / "input" / "form").glob("*_obj.obj"))
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
