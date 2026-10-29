#!/usr/bin/env python3
"""Merge scaled-input, exp4, and exp5 into the primary experiment catalog."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
RESULTS = HOI_ROOT / "analysis_results/amodal_iou_comparison_reviewed"
DATA = HOI_ROOT / "data/dexycb_hl_v3_100_20_20"
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
MANO = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")
RELEASE = "20261029-amodal-iou"
BASELINES = (
    ("scaled-input-20261029", "scaled input-20261029", "scaled", "#fb923c"),
    ("exp4-20261029", "exp4-20261029", "old", "#22d3ee"),
    ("exp5-20261029", "exp5-20261029", "new", "#ef4444"),
)
NEW_IDS = {item[0] for item in BASELINES}


def read_metrics(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    result = {row["sequence_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"{path}: duplicate sequence_id")
    return result


def metrics_payload(row: dict[str, str]) -> dict[str, float | int]:
    object_count = int(row["object_amodal_count"])
    hand_count = int(row["hand_amodal_count"])
    return {
        "objectAmodalScoredMeanIou": float(row["object_amodal_scored_mean_iou"]),
        "objectAmodalEvaluatedFrames": object_count,
        "objectAmodalEligibleFrames": object_count,
        "handAmodalScoredMeanIou": float(row["hand_amodal_scored_mean_iou"]),
        "handAmodalEvaluatedFrames": hand_count,
        "handAmodalEligibleFrames": hand_count,
    }


def prediction_dir(result_id: str, split: str, sample_id: str) -> Path:
    if result_id == "scaled":
        return RESULTS / f"predictions/scaled-compatible/{split}/{sample_id}"
    return RESULTS / f"predictions/{result_id}/{split}/{split}/{sample_id}"


def main() -> None:
    config_root = ROOT / "configs/examples"
    asset_root = ROOT / "r2_assets/experiments" / RELEASE
    expected = {"validation": 8, "test": 20}
    touched = 0

    for split, expected_count in expected.items():
        metrics_by_baseline = {
            baseline_id: read_metrics(RESULTS / f"metrics_final/{result_id}/{split}/per_sequence.csv")
            for baseline_id, _label, result_id, _color in BASELINES
        }
        sequence_ids = sorted(metrics_by_baseline[BASELINES[0][0]])
        if len(sequence_ids) != expected_count:
            raise ValueError(f"{split}: expected {expected_count} sequences, found {len(sequence_ids)}")
        if any(set(metrics_by_baseline[item[0]]) != set(sequence_ids) for item in BASELINES[1:]):
            raise ValueError(f"{split}: scaled/exp4/exp5 sequence sets differ")

        for sample_id in sequence_ids:
            source_root = DATA / split / sample_id
            groundtruth = json.loads((source_root / "groundtruth/manifest.json").read_text())
            side = groundtruth["hand"]["side"]
            rgb = asset_root / sample_id / "input-rgb.mp4"
            rgb.parent.mkdir(parents=True, exist_ok=True)
            if not rgb.exists():
                shutil.copy2(source_root / "input/color_video.mp4", rgb)

            added = []
            for baseline_id, label, result_id, color in BASELINES:
                reconstruction = asset_root / sample_id / baseline_id / "reconstruction"
                if not (reconstruction / "reconstruction.json").exists():
                    subprocess.run([
                        str(PYTHON), str(ROOT / "scripts/export_reconstruction.py"),
                        "--result-dir", str(prediction_dir(result_id, split, sample_id)),
                        "--mano-dir", str(MANO), "--output", str(reconstruction),
                        "--hand-side", side,
                    ], check=True)
                reconstruction_url = (
                    f"experiments/{RELEASE}/{sample_id}/{baseline_id}/reconstruction/reconstruction.json"
                )
                added.append({
                    "id": baseline_id,
                    "label": label,
                    "color": color,
                    "metrics": metrics_payload(metrics_by_baseline[baseline_id][sample_id]),
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

            config_path = config_root / f"{sample_id}.json"
            if config_path.exists():
                config = json.loads(config_path.read_text(encoding="utf-8"))
                retained = [item for item in config["baselines"] if item["id"] not in NEW_IDS]
                config["baselines"] = retained + added
                config["description"] = (
                    "DexYCB sequence with legacy and 2026-10-29 scaled-input baselines "
                    "for side-by-side comparison."
                )
            else:
                config = {
                    "schemaVersion": 2,
                    "id": sample_id,
                    "label": sample_id.replace("__", " / "),
                    "description": (
                        "DexYCB sequence comparing the scaled input baseline with exp4 and exp5."
                    ),
                    "dataset": "DexYCB",
                    "split": "val" if split == "validation" else "test",
                    "objectName": groundtruth["objects"]["target_name"],
                    "fps": 30,
                    "frameCount": int(groundtruth["timeline"]["frame_count"]),
                    "baselines": added,
                }
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            touched += 1

    print(f"Merged three scaled-input baselines into {touched} primary-catalog samples")


if __name__ == "__main__":
    main()
