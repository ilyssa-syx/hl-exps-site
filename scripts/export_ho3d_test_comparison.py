#!/usr/bin/env python3
"""Export the 13-sample HO3D v3 test comparison."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
DATA = HOI_ROOT / "data/ho3d_test"
FOURTH_RESULTS = HOI_ROOT / "eval_runs/cd-iou-fourth-run-0005-0004-ho3d-test/test"
DIFF_FIRST_RESULTS = HOI_ROOT / "eval_runs/successful-differentiable-first-run-0002-0001-ho3d-test/test"
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
MANO = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")
RELEASE = "20261102-ho3d-v3-test"
SPLIT = "test"
EXPECTED_COUNT = 13
BASELINES = (
    {
        "id": "input",
        "label": "input",
        "asset_id": "scaled-input",
        "source": lambda sample_id: DATA / SPLIT / sample_id / "input/final",
        "color": "#fb923c",
        "metrics": HOI_ROOT / "eval_runs/ho3d-test-input-eval-v1/per_sequence.csv",
    },
    {
        "id": "cd-iou-fourth-run-20261029",
        "label": "cd-iou-fourth-run-20261029",
        "asset_id": "cd-iou-fourth-run-20261029",
        "source": lambda sample_id: FOURTH_RESULTS / sample_id,
        "color": "#22d3ee",
        "metrics": HOI_ROOT / "eval_runs/cd-iou-fourth-run-0005-0004-ho3d-test-eval-v1/per_sequence.csv",
    },
    {
        "id": "successful-differentiable-first-run",
        "label": "successful-differentiable-first-run",
        "asset_id": "successful-differentiable-first-run",
        "source": lambda sample_id: DIFF_FIRST_RESULTS / sample_id,
        "color": "#a78bfa",
        "metrics": HOI_ROOT / "eval_runs/successful-differentiable-first-run-0002-0001-ho3d-test-eval-v1/per_sequence.csv",
    },
)


def _stat(row: dict[str, str], prefix: str, unit: str, *, scored: bool = False) -> dict:
    result = {
        "count": int(row[f"{prefix}_count"]),
        "mean": float(row[f"{prefix}_mean_{unit}"]),
        "median": float(row[f"{prefix}_median_{unit}"]),
    }
    if scored:
        result["scoredMean"] = float(row[f"{prefix}_scored_mean_{unit}"])
    return result


def load_metrics(path: Path) -> dict[str, dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return {
        row["sequence_id"]: {
            "addAligned": _stat(row, "add_aligned", "cm"),
            "objectAmodalIou": _stat(row, "object_amodal", "iou", scored=True),
            "handAmodalIou": _stat(row, "hand_amodal", "iou", scored=True),
            "cdH": _stat(row, "cd_h", "cm", scored=True),
            "objRel": _stat(row, "obj_rel", "cm"),
            "wristTranslation": {
                "count": int(row["wrist_pose_translation_count"]),
                "mean": float(row["wrist_pose_translation_mean_mm"]),
                "median": float(row["wrist_pose_translation_median_mm"]),
            },
        }
        for row in rows
    }


def ensure_reconstruction(source: Path, output: Path, hand_side: str) -> None:
    if (output / "reconstruction.json").exists():
        return
    subprocess.run([
        str(PYTHON), str(ROOT / "scripts/export_reconstruction.py"),
        "--result-dir", str(source), "--mano-dir", str(MANO),
        "--output", str(output), "--hand-side", hand_side,
    ], check=True)


def main() -> None:
    config_root = ROOT / "configs/HO3D_v3-TEST/examples"
    config_root.mkdir(parents=True, exist_ok=True)
    asset_root = ROOT / "r2_assets/experiments" / RELEASE
    dataset_ids = sorted(path.name for path in (DATA / SPLIT).iterdir() if path.is_dir())
    if len(dataset_ids) != EXPECTED_COUNT:
        raise ValueError(f"expected {EXPECTED_COUNT} test sequences, found {len(dataset_ids)}")

    for result_root in (FOURTH_RESULTS, DIFF_FIRST_RESULTS):
        result_ids = sorted(path.name for path in result_root.iterdir() if path.is_dir())
        if result_ids != dataset_ids:
            raise ValueError(f"result sequence set differs from dataset: {result_root}")
    metrics_by_baseline = {item["id"]: load_metrics(item["metrics"]) for item in BASELINES}
    for baseline_id, rows in metrics_by_baseline.items():
        if sorted(rows) != dataset_ids:
            raise ValueError(f"{baseline_id} metric sequence set differs from dataset")

    for sample_id in dataset_ids:
        source_root = DATA / SPLIT / sample_id
        groundtruth = json.loads((source_root / "groundtruth/manifest.json").read_text())
        rgb = asset_root / sample_id / "input-rgb.mp4"
        rgb.parent.mkdir(parents=True, exist_ok=True)
        if not rgb.exists():
            shutil.copy2(source_root / f"input/dyn_hamr/videos/{sample_id}.mp4", rgb)

        baselines = []
        for item in BASELINES:
            reconstruction = asset_root / sample_id / item["asset_id"] / "reconstruction"
            ensure_reconstruction(item["source"](sample_id), reconstruction, groundtruth["hand"]["side"])
            reconstruction_url = (
                f"experiments/{RELEASE}/{sample_id}/{item['asset_id']}"
                "/reconstruction/reconstruction.json"
            )
            baselines.append({
                "id": item["id"], "label": item["label"], "color": item["color"],
                "metrics": metrics_by_baseline[item["id"]][sample_id],
                "views": {
                    "overlay2d": {
                        "rgb": {"type": "video", "url": f"experiments/{RELEASE}/{sample_id}/input-rgb.mp4"},
                        "reconstruction": reconstruction_url,
                    },
                    "scene3d": {"reconstruction": reconstruction_url},
                },
            })

        config = {
            "schemaVersion": 2,
            "id": sample_id,
            "label": sample_id,
            "description": (
                "HO3D v3 test sequence comparing scaled input, cd-iou-fourth-run-20261029, "
                "and successful-differentiable-first-run."
            ),
            "dataset": "HO3D v3",
            "split": "test",
            "objectName": groundtruth["object"]["name"],
            "fps": 30,
            "frameCount": int(groundtruth["frame_count"]),
            "metricLabel": "Evaluation v1",
            "metricNote": (
                "Per-sequence means from HO3D evaluation v1. Missing eligible hand "
                "predictions score 0 in scored metrics; raw means include evaluated frames only."
            ),
            "baselines": baselines,
        }
        (config_root / f"{sample_id}.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )

    for old_config in config_root.glob("*.json"):
        if old_config.stem not in dataset_ids:
            old_config.unlink()
    print(f"Exported {len(dataset_ids)} HO3D v3 test configs and visualization assets")


if __name__ == "__main__":
    main()
