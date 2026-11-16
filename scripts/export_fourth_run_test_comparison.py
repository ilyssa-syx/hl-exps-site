#!/usr/bin/env python3
"""Export the 20-sample DexYCB test comparison."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
DATA = HOI_ROOT / "data/dexycb_hl_v3_100_20_20"
FOURTH_RESULTS = HOI_ROOT / "eval_runs/cd-iou-fourth-run-0005-0004-dexycb-test"
DIFF_FIRST_RESULTS = (
    HOI_ROOT
    / "eval_runs/successful-differentiable-first-run-0002-0001-dexycb-test/test"
)
EXP8_LATEST_RESULTS = (
    HOI_ROOT
    / "eval_runs/run-20261106-latest-e0011-i0001-dexycb-test-pred/test"
)
FIVE_EXAMPLES_OVERFIT_RESULTS = (
    HOI_ROOT
    / "eval_runs/5-cases-q0154-dexycb-hl-v3-test/predictions/test"
)
EXP11_RESULTS = (
    HOI_ROOT
    / "eval_runs/linear-batch-3-e0000-i0010-dexycb-test/predictions/test"
)
INPUT_METRICS = (
    HOI_ROOT
    / "eval_runs/dexycb-hl-v3-100-20-20-cleaned-test-input-eval-v12/per_sequence.csv"
)
FOURTH_METRICS = (
    HOI_ROOT
    / "eval_runs/cd-iou-fourth-run-0005-0004-dexycb-test-eval-v12/per_sequence.csv"
)
DIFF_FIRST_METRICS = (
    HOI_ROOT
    / "eval_runs/successful-differentiable-first-run-0002-0001-dexycb-test-eval-v12/per_sequence.csv"
)
EXP8_LATEST_METRICS = (
    HOI_ROOT
    / "eval_runs/run-20261106-latest-e0011-i0001-dexycb-test-metrics/per_sequence.csv"
)
FIVE_EXAMPLES_OVERFIT_METRICS = (
    HOI_ROOT
    / "eval_runs/5-cases-q0154-dexycb-hl-v3-test/metrics/per_sequence.csv"
)
EXP11_METRICS = (
    HOI_ROOT
    / "eval_runs/linear-batch-3-e0000-i0010-dexycb-test/metrics/per_sequence.csv"
)
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
        "metrics": INPUT_METRICS,
    },
    {
        "id": "exp-4",
        "label": "Exp 4",
        "result_id": "old",
        "asset_id": "exp4-20261029",
        "color": "#22d3ee",
        "metrics": FOURTH_METRICS,
    },
    {
        "id": "exp-7",
        "label": "Exp 7",
        "result_id": "diff-first",
        "asset_id": "exp7-20261102",
        "color": "#a78bfa",
        "metrics": DIFF_FIRST_METRICS,
    },
    {
        "id": "exp-8-latest",
        "label": "Exp 8 (latest)",
        "result_id": "exp8-latest",
        "asset_id": "exp8-latest-20261106",
        "color": "#34d399",
        "metrics": EXP8_LATEST_METRICS,
    },
    {
        "id": "five-examples-overfit",
        "label": "5 examples overfit",
        "result_id": "five-examples-overfit",
        "asset_id": "five-examples-overfit-q0154-20261114",
        "color": "#f43f5e",
        "metrics": FIVE_EXAMPLES_OVERFIT_METRICS,
    },
    {
        "id": "exp-11",
        "label": "exp11",
        "result_id": "exp-11",
        "asset_id": "exp11-e0000-i0010-20261115",
        "color": "#3b82f6",
        "metrics": EXP11_METRICS,
    },
)


def _stat(
    row: dict[str, str],
    prefix: str,
    unit: str,
    *,
    scored: bool = False,
) -> dict[str, int | float]:
    result: dict[str, int | float] = {
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
    result = {}
    for row in rows:
        sequence_id = row["sequence_id"]
        result[sequence_id] = {
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
            "wristRotation": {
                "count": int(row["wrist_pose_rotation_count"]),
                "mean": float(row["wrist_pose_rotation_mean_deg"]),
                "median": float(row["wrist_pose_rotation_median_deg"]),
            },
        }
    return result


def result_dir(result_id: str, sample_id: str) -> Path:
    if result_id == "scaled":
        # This compatibility copy only adds the derived joints_camera cache. The
        # exporter reads the unchanged MANO parameters from input/final.
        return DATA / SPLIT / sample_id / "input/final"
    if result_id == "old":
        return FOURTH_RESULTS / sample_id
    if result_id == "diff-first":
        return DIFF_FIRST_RESULTS / sample_id
    if result_id == "exp8-latest":
        return EXP8_LATEST_RESULTS / sample_id
    if result_id == "five-examples-overfit":
        return FIVE_EXAMPLES_OVERFIT_RESULTS / sample_id
    if result_id == "exp-11":
        return EXP11_RESULTS / sample_id
    raise ValueError(f"unknown result ID: {result_id}")


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
        path.name for path in FOURTH_RESULTS.iterdir()
        if path.is_dir()
    )
    if fourth_result_ids != dataset_ids:
        raise ValueError("fourth-run result sequence set differs from dataset test split")
    diff_first_result_ids = sorted(
        path.name for path in DIFF_FIRST_RESULTS.iterdir()
        if path.is_dir()
    )
    if diff_first_result_ids != dataset_ids:
        raise ValueError(
            "differentiable-first-run result sequence set differs from dataset test split"
        )
    exp8_latest_result_ids = sorted(
        path.name for path in EXP8_LATEST_RESULTS.iterdir()
        if path.is_dir()
    )
    if exp8_latest_result_ids != dataset_ids:
        raise ValueError("Exp 8 latest result sequence set differs from dataset test split")
    five_examples_overfit_result_ids = sorted(
        path.name for path in FIVE_EXAMPLES_OVERFIT_RESULTS.iterdir()
        if path.is_dir()
    )
    if five_examples_overfit_result_ids != dataset_ids:
        raise ValueError(
            "5 examples overfit result sequence set differs from dataset test split"
        )
    exp11_result_ids = sorted(
        path.name for path in EXP11_RESULTS.iterdir()
        if path.is_dir()
    )
    if exp11_result_ids != dataset_ids:
        raise ValueError("exp11 result sequence set differs from dataset test split")
    metrics_by_baseline = {
        item["id"]: load_metrics(item["metrics"])
        for item in BASELINES
    }
    for baseline_id, rows in metrics_by_baseline.items():
        if sorted(rows) != dataset_ids:
            raise ValueError(
                f"{baseline_id} metric sequence set differs from dataset test split"
            )

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
                "metrics": metrics_by_baseline[item["id"]][sample_id],
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
                "DexYCB test sequence comparing input, Exp 4, Exp 7, "
                "Exp 8 (latest), 5 examples overfit, and exp11."
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
        payload = json.loads(old_config.read_text(encoding="utf-8"))
        if (
            payload.get("dataset") == "DexYCB"
            and payload.get("split") == "test"
            and old_config.stem not in dataset_ids
        ):
            old_config.unlink()
    print(f"Exported {len(dataset_ids)} test configs using existing comparison assets")


if __name__ == "__main__":
    main()
