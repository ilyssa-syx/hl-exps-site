#!/usr/bin/env python3
"""Export the three-checkpoint CD-H/amodal-IoU comparison release."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
RUN = HOI_ROOT / "eval_runs/cd-iou-checkpoint-comparison-dexycb-v3-100-20-10"
DATA = HOI_ROOT / "data/dexycb_hl_v3_100_20_10"
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
MANO = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")
RELEASE = "20261026-cd-iou"
BASELINES = (
    ("first-e0001-i0002", "first · epoch 1 / iteration 2", "#55a7ff"),
    ("third-e0003-i0000", "third · epoch 3 / iteration 0", "#ff6f91"),
    ("fourth-e0002-i0001", "fourth · epoch 2 / iteration 1", "#62e0c5"),
)
LEFT_HAND_RECONSTRUCTION_VERSION = "20261023-mano-left-v2"


def read_metrics(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    result = {row["sequence_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"{path}: duplicate sequence_id")
    return result


def metrics_payload(row: dict[str, str]) -> dict[str, float | int]:
    return {
        "score": float(row["score"]),
        "cdHScoredMeanCm": float(row["cd_h_scored_mean_cm"]),
        "cdHEvaluatedFrames": int(row["cd_h_evaluated_frames"]),
        "cdHEligibleFrames": int(row["cd_h_eligible_frames"]),
        "objectAmodalScoredMeanIou": float(row["object_amodal_scored_mean_iou"]),
        "objectAmodalEvaluatedFrames": int(row["object_amodal_evaluated_frames"]),
        "objectAmodalEligibleFrames": int(row["object_amodal_eligible_frames"]),
        "handAmodalScoredMeanIou": float(row["hand_amodal_scored_mean_iou"]),
        "handAmodalEvaluatedFrames": int(row["hand_amodal_evaluated_frames"]),
        "handAmodalEligibleFrames": int(row["hand_amodal_eligible_frames"]),
    }


def main() -> None:
    config_root = ROOT / "configs/examples"
    asset_root = ROOT / "r2_assets/experiments" / RELEASE
    expected = {"validation": 20, "test": 10}
    written: set[str] = set()

    for split, expected_count in expected.items():
        metrics_by_baseline = {
            baseline_id: read_metrics(RUN / f"{baseline_id}-{split}-metrics/per_sequence.csv")
            for baseline_id, _label, _color in BASELINES
        }
        sequence_ids = sorted(metrics_by_baseline[BASELINES[0][0]])
        if len(sequence_ids) != expected_count:
            raise ValueError(f"{split}: expected {expected_count} sequences, found {len(sequence_ids)}")
        for baseline_id, _label, _color in BASELINES[1:]:
            if set(metrics_by_baseline[baseline_id]) != set(sequence_ids):
                raise ValueError(f"{split}: {baseline_id} sequence set differs")

        for sample_id in sequence_ids:
            written.add(sample_id)
            source_root = DATA / split / sample_id
            groundtruth = json.loads((source_root / "groundtruth/manifest.json").read_text())
            side = groundtruth["hand"]["side"]
            rgb = asset_root / sample_id / "input-rgb.mp4"
            rgb.parent.mkdir(parents=True, exist_ok=True)
            if not rgb.exists():
                shutil.copy2(source_root / "input/color_video.mp4", rgb)
            baselines = []
            for baseline_id, label, color in BASELINES:
                prediction = RUN / f"{baseline_id}-{split}-predictions" / split / sample_id
                reconstruction = asset_root / sample_id / baseline_id / "reconstruction"
                reconstruction_json = reconstruction / "reconstruction.json"
                if not reconstruction_json.exists():
                    subprocess.run([
                        str(PYTHON), str(ROOT / "scripts/export_reconstruction.py"),
                        "--result-dir", str(prediction), "--mano-dir", str(MANO),
                        "--output", str(reconstruction), "--hand-side", side,
                    ], check=True)
                reconstruction_url = (
                    f"experiments/{RELEASE}/{sample_id}/{baseline_id}/reconstruction/reconstruction.json"
                )
                if side == "left":
                    reconstruction_url += f"?v={LEFT_HAND_RECONSTRUCTION_VERSION}"
                baselines.append({
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

            config = {
                "schemaVersion": 2,
                "id": sample_id,
                "label": sample_id.replace("__", " / "),
                "description": "DexYCB checkpoint comparison optimized for CD-H and amodal IoU.",
                "dataset": "DexYCB",
                "split": "val" if split == "validation" else "test",
                "objectName": groundtruth["objects"]["target_name"],
                "fps": 30,
                "frameCount": int(groundtruth["timeline"]["frame_count"]),
                "baselines": baselines,
            }
            (config_root / f"{sample_id}.json").write_text(json.dumps(config, indent=2) + "\n")

    for old in config_root.glob("*.json"):
        if old.stem not in written:
            old.unlink()
    print(f"Exported {len(written)} configs and reconstruction assets below {asset_root}")


if __name__ == "__main__":
    main()
