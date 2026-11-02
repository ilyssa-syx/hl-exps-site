#!/usr/bin/env python3
"""Export the 20-sample scaled-input vs. CD-IoU fourth-run comparison."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
DATA = HOI_ROOT / "data/dexycb_hl_v3_100_20_20"
RESULTS = HOI_ROOT / "legendary_analysis/analysis_results/amodal_iou_comparison_reviewed"
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
MANO = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")
RELEASE = "20261029-amodal-iou"
SPLIT = "test"
EXPECTED_COUNT = 20
BASELINES = (
    {
        "id": "input",
        "label": "input",
        "result_id": "scaled",
        "asset_id": "scaled-input-20261029",
        "color": "#fb923c",
    },
    {
        "id": "cd-iou-fourth-run-20261029",
        "label": "cd-iou-fourth-run-20261029",
        "result_id": "old",
        "asset_id": "exp4-20261029",
        "color": "#22d3ee",
    },
)


def result_dir(result_id: str, sample_id: str) -> Path:
    if result_id == "scaled":
        # This compatibility copy only adds the derived joints_camera cache. The
        # exporter reads the unchanged MANO parameters from input/final.
        return DATA / SPLIT / sample_id / "input/final"
    return RESULTS / "predictions/old/test/test" / sample_id


def ensure_reconstruction(source: Path, output: Path, hand_side: str) -> None:
    if (output / "reconstruction.json").exists():
        return
    subprocess.run([
        str(PYTHON), str(ROOT / "scripts/export_reconstruction.py"),
        "--result-dir", str(source), "--mano-dir", str(MANO),
        "--output", str(output), "--hand-side", hand_side,
    ], check=True)


def main() -> None:
    config_root = ROOT / "configs/examples"
    asset_root = ROOT / "r2_assets/experiments" / RELEASE
    dataset_ids = sorted(path.name for path in (DATA / SPLIT).iterdir() if path.is_dir())
    if len(dataset_ids) != EXPECTED_COUNT:
        raise ValueError(f"expected {EXPECTED_COUNT} test sequences, found {len(dataset_ids)}")

    fourth_result_ids = sorted(
        path.name for path in (RESULTS / "predictions/old/test/test").iterdir()
        if path.is_dir()
    )
    if fourth_result_ids != dataset_ids:
        raise ValueError("fourth-run result sequence set differs from dataset test split")

    for sample_id in dataset_ids:
        source_root = DATA / SPLIT / sample_id
        groundtruth = json.loads((source_root / "groundtruth/manifest.json").read_text())
        rgb = asset_root / sample_id / "input-rgb.mp4"
        rgb.parent.mkdir(parents=True, exist_ok=True)
        if not rgb.exists():
            shutil.copy2(source_root / "input/color_video.mp4", rgb)

        baselines = []
        for item in BASELINES:
            reconstruction = asset_root / sample_id / item["asset_id"] / "reconstruction"
            ensure_reconstruction(
                result_dir(item["result_id"], sample_id),
                reconstruction,
                groundtruth["hand"]["side"],
            )
            reconstruction_url = (
                f"experiments/{RELEASE}/{sample_id}/{item['asset_id']}"
                "/reconstruction/reconstruction.json"
            )
            baselines.append({
                "id": item["id"],
                "label": item["label"],
                "color": item["color"],
                "views": {
                    "overlay2d": {
                        "rgb": {
                            "type": "video",
                            "url": f"experiments/{RELEASE}/{sample_id}/input-rgb.mp4",
                        },
                        "reconstruction": reconstruction_url,
                    },
                    "scene3d": {"reconstruction": reconstruction_url},
                },
            })

        config = {
            "schemaVersion": 2,
            "id": sample_id,
            "label": sample_id.replace("__", " / "),
            "description": (
                "DexYCB test sequence comparing input with "
                "cd-iou-fourth-run-20261029."
            ),
            "dataset": "DexYCB",
            "split": "test",
            "objectName": groundtruth["objects"]["target_name"],
            "fps": 30,
            "frameCount": int(groundtruth["timeline"]["frame_count"]),
            "baselines": baselines,
        }
        (config_root / f"{sample_id}.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )

    for old_config in config_root.glob("*.json"):
        if old_config.stem not in dataset_ids:
            old_config.unlink()
    print(f"Exported {len(dataset_ids)} test configs using existing comparison assets")


if __name__ == "__main__":
    main()
