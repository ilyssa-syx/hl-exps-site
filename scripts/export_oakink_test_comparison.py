#!/usr/bin/env python3
"""Export the 20-sample OakInk test comparison and its R2 assets."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
DATA = HOI_ROOT / "data/oakink1_sp0_sample20"
INPUT_RESULTS = HOI_ROOT / "eval_runs/input-baseline-oakink-test/predictions/test"
EXP8_RESULTS = HOI_ROOT / "eval_runs/linear-batch-20-e0005-i0003-oakink-test/predictions/test"
OVERFIT_RESULTS = HOI_ROOT / "eval_runs/5-cases-q0154-oakink-test/predictions/test"
EXP11_RESULTS = HOI_ROOT / "eval_runs/linear-batch-3-e0000-i0028-oakink-test/predictions/test"
EXP13_RESULTS = HOI_ROOT / "eval_runs/linear-bs3-batch-v1-e0000-i0024-oakink-test/predictions/test"
RECONSTRUCTION_RESULTS = HOI_ROOT / "eval_runs/5-examples-overfit-reconstruction-q0154-oakink-test/predictions/test"
INPUT_METRICS = HOI_ROOT / "eval_runs/input-baseline-oakink-test/metrics/per_sequence.csv"
EXP8_METRICS = HOI_ROOT / "eval_runs/linear-batch-20-e0005-i0003-oakink-test/metrics/per_sequence.csv"
OVERFIT_METRICS = HOI_ROOT / "eval_runs/5-cases-q0154-oakink-test/metrics/per_sequence.csv"
EXP11_METRICS = HOI_ROOT / "eval_runs/linear-batch-3-e0000-i0028-oakink-test/metrics/per_sequence.csv"
EXP13_METRICS = HOI_ROOT / "eval_runs/linear-bs3-batch-v1-e0000-i0024-oakink-test/metrics/per_sequence.csv"
RECONSTRUCTION_METRICS = HOI_ROOT / "eval_runs/5-examples-overfit-reconstruction-q0154-oakink-test/metrics/per_sequence.csv"
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
FFMPEG = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/ffmpeg")
MANO = HOI_ROOT / "assets/mano"
RELEASE = "20261116-oakink-sample20"
SPLIT = "test"
FPS = 30
EXPECTED_COUNT = 20
BASELINES = (
    {"id": "input", "label": "input", "color": "#fb923c", "results": INPUT_RESULTS, "metrics": INPUT_METRICS, "asset": "input"},
    {"id": "exp-8", "label": "exp8", "color": "#34d399", "results": EXP8_RESULTS, "metrics": EXP8_METRICS, "asset": "exp8"},
    {"id": "five-examples-overfit", "label": "5 examples overfit", "color": "#f43f5e", "results": OVERFIT_RESULTS, "metrics": OVERFIT_METRICS, "asset": "five-examples-overfit"},
    {"id": "exp-11", "label": "exp11", "color": "#3b82f6", "results": EXP11_RESULTS, "metrics": EXP11_METRICS, "asset": "exp11-e0000-i0028-20261123"},
    {"id": "exp-13", "label": "exp13", "color": "#e879f9", "results": EXP13_RESULTS, "metrics": EXP13_METRICS, "asset": "exp13-e0000-i0024-batch-v1-20261123"},
)
RECONSTRUCTION = {
    "id": "five-examples-overfit-reconstruction",
    "label": "5 examples overfitting reconstruction",
    "color": "#14b8a6",
    "results": RECONSTRUCTION_RESULTS,
    "metrics": RECONSTRUCTION_METRICS,
    "asset": "five-examples-overfit-reconstruction-q0154-20261123",
}


def stat(row: dict[str, str], prefix: str, unit: str, *, scored: bool = False) -> dict:
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
    result = {}
    for row in rows:
        result[row["sequence_id"]] = {
            "addAligned": stat(row, "add_aligned", "cm"),
            "objectAmodalIou": stat(row, "object_amodal", "iou", scored=True),
            "handAmodalIou": stat(row, "hand_amodal", "iou", scored=True),
            "cdH": stat(row, "cd_h", "cm", scored=True),
            "objRel": stat(row, "obj_rel", "cm"),
            "wristTranslation": stat(row, "wrist_pose_translation", "mm"),
            "wristRotation": stat(row, "wrist_pose_rotation", "deg"),
        }
    return result


def ensure_rgb(source: Path, output: Path) -> None:
    if output.is_file():
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(FPS), "-i", str(source / "%06d.jpg"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ], check=True)


def ensure_reconstruction(source: Path, output: Path) -> None:
    if (output / "reconstruction.json").is_file():
        return
    subprocess.run([
        str(PYTHON), str(ROOT / "scripts/export_reconstruction.py"),
        "--result-dir", str(source), "--mano-dir", str(MANO),
        "--output", str(output), "--hand-side", "right",
    ], check=True)


def main() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    rows = [row for row in manifest["sequences"] if row["split"] == SPLIT]
    if len(rows) != EXPECTED_COUNT:
        raise ValueError(f"expected {EXPECTED_COUNT} OakInk test sequences, found {len(rows)}")
    sequence_ids = [row["sequence_id"] for row in rows]
    metrics = {item["id"]: load_metrics(item["metrics"]) for item in BASELINES}
    for item in BASELINES:
        result_ids = sorted(path.name for path in item["results"].iterdir() if path.is_dir())
        if result_ids != sorted(sequence_ids):
            raise ValueError(f"{item['label']} result sequence set differs from OakInk sample20")
        if sorted(metrics[item["id"]]) != sorted(sequence_ids):
            raise ValueError(f"{item['label']} metric sequence set differs from OakInk sample20")
    reconstruction_ids = sorted(
        path.name for path in RECONSTRUCTION_RESULTS.iterdir() if path.is_dir()
    )
    reconstruction_metrics = load_metrics(RECONSTRUCTION_METRICS)
    if reconstruction_ids != sorted(reconstruction_metrics):
        raise ValueError("reconstruction result and metric sequence sets differ")
    if not set(reconstruction_ids) < set(sequence_ids):
        raise ValueError("reconstruction sequence set must be a proper subset of sample20")
    metrics[RECONSTRUCTION["id"]] = reconstruction_metrics

    asset_root = ROOT / "r2_assets/experiments" / RELEASE
    config_root = ROOT / "configs/examples"
    for row in rows:
        sequence_id = row["sequence_id"]
        source = DATA / SPLIT / sequence_id
        rgb = asset_root / sequence_id / "input-rgb.mp4"
        ensure_rgb(source / "rgb", rgb)
        baselines = []
        page_baselines = BASELINES + ((RECONSTRUCTION,) if sequence_id in reconstruction_metrics else ())
        for item in page_baselines:
            reconstruction = asset_root / sequence_id / item["asset"] / "reconstruction"
            ensure_reconstruction(item["results"] / sequence_id, reconstruction)
            reconstruction_url = (
                f"experiments/{RELEASE}/{sequence_id}/{item['asset']}"
                "/reconstruction/reconstruction.json"
            )
            baselines.append({
                "id": item["id"], "label": item["label"], "color": item["color"],
                "metrics": metrics[item["id"]][sequence_id],
                "views": {
                    "overlay2d": {
                        "rgb": {"type": "video", "url": f"experiments/{RELEASE}/{sequence_id}/input-rgb.mp4"},
                        "reconstruction": reconstruction_url,
                    },
                    "scene3d": {"reconstruction": reconstruction_url},
                },
            })
        config = {
            "schemaVersion": 2,
            "id": sequence_id,
            "label": sequence_id.replace("__", " / "),
            "description": (
                "OakInk SP0 test sequence comparing shared input, exp8, 5 examples "
                "overfit, exp11, exp13, and 5 examples overfitting reconstruction."
                if sequence_id in reconstruction_metrics else
                "OakInk SP0 test sequence comparing shared input, exp8, 5 examples overfit, exp11, and exp13."
            ),
            "dataset": "OakInk",
            "split": "GT-texture 11 test" if sequence_id in reconstruction_metrics else SPLIT,
            "objectName": row["object_id"], "fps": FPS,
            "frameCount": int(row["frame_count"]),
            "metricLabel": "OakInk evaluation",
            "metricNote": "Per-sequence OakInk metrics. No visible-segmentation eligibility filter; missing hand predictions score 0 in scored metrics.",
            "baselines": baselines,
        }
        (config_root / f"{sequence_id}.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8",
        )
    print(f"Exported {len(rows)} OakInk configs and staged assets below {asset_root}")


if __name__ == "__main__":
    main()
