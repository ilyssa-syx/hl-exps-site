#!/usr/bin/env python3
"""Export the five DexYCB train-overfit examples at query/iteration 150."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
DATA = HOI_ROOT / "data/dexycb_hl_v3_100_20_20_cleaned"
RUN = HOI_ROOT / "runs/run-20261113-five-case-from-zero"
ITERATION = 150
ITERATION_ROOT = RUN / f"queries/{ITERATION:04d}/results/train"
INPUT_METRICS = HOI_ROOT / "runs/run-20261106/baseline/results/train/per_sequence.csv"
ITERATION_METRICS = ITERATION_ROOT / "per_sequence.csv"
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
MANO = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")
RELEASE = "20261122-five-examples-train-overfit-q0150"
CATALOG_SPLIT = "5 examples train overfit"
SEQUENCE_IDS = (
    "20200709-subject-01__20200709_141931__932122060861",
    "20200813-subject-02__20200813_154917__932122060857",
    "20200820-subject-03__20200820_145035__932122062010",
    "20200903-subject-04__20200903_103749__839512060362",
    "20200918-subject-06__20200918_113441__932122061900",
)
BASELINES = (
    {"id": "input", "label": "input", "color": "#fb923c"},
    {
        "id": "iteration-150",
        "label": "5 examples overfitting refinement (iter 150)",
        "color": "#f43f5e",
    },
)


def _stat(
    row: dict[str, str], prefix: str, unit: str, *, scored: bool = False,
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
        result[row["sequence_id"]] = {
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


def ensure_reconstruction(source: Path, output: Path, hand_side: str) -> None:
    if (output / "reconstruction.json").exists():
        return
    subprocess.run([
        str(PYTHON), str(ROOT / "scripts/export_reconstruction.py"),
        "--result-dir", str(source), "--mano-dir", str(MANO),
        "--output", str(output), "--hand-side", hand_side,
    ], check=True)


def ensure_rgb_video(source_root: Path, output: Path) -> None:
    if output.exists():
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    packaged = source_root / "input/color_video.mp4"
    if packaged.exists():
        shutil.copy2(packaged, output)
        return
    subprocess.run([
        str(PYTHON.parent / "ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "30", "-pattern_type", "glob", "-i", "*.jpg",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output),
    ], cwd=source_root / "rgb", check=True)


def main() -> None:
    config_root = ROOT / "configs/examples"
    asset_root = ROOT / "r2_assets/experiments" / RELEASE
    metrics = {
        "input": load_metrics(INPUT_METRICS),
        "iteration-150": load_metrics(ITERATION_METRICS),
    }
    exported_ids = set()

    for sequence_id in SEQUENCE_IDS:
        source_root = DATA / "train" / sequence_id
        result_root = ITERATION_ROOT / sequence_id
        if not source_root.is_dir() or not result_root.is_dir():
            raise FileNotFoundError(sequence_id)
        for baseline_id, rows in metrics.items():
            if sequence_id not in rows:
                raise ValueError(f"missing {baseline_id} metrics for {sequence_id}")

        groundtruth = json.loads(
            (source_root / "groundtruth/manifest.json").read_text(encoding="utf-8")
        )
        page_id = f"dexycb-five-examples-train-overfit--{sequence_id}"
        exported_ids.add(page_id)
        sample_assets = asset_root / sequence_id
        ensure_rgb_video(source_root, sample_assets / "input-rgb.mp4")

        baselines = []
        for baseline in BASELINES:
            baseline_id = baseline["id"]
            source = source_root / "input/final" if baseline_id == "input" else result_root
            reconstruction = sample_assets / baseline_id / "reconstruction"
            ensure_reconstruction(source, reconstruction, groundtruth["hand"]["side"])
            reconstruction_url = (
                f"experiments/{RELEASE}/{sequence_id}/{baseline_id}"
                "/reconstruction/reconstruction.json"
            )
            baselines.append({
                **baseline,
                "metrics": metrics[baseline_id][sequence_id],
                "views": {
                    "overlay2d": {
                        "rgb": {
                            "type": "video",
                            "url": f"experiments/{RELEASE}/{sequence_id}/input-rgb.mp4",
                        },
                        "reconstruction": reconstruction_url,
                    },
                    "scene3d": {"reconstruction": reconstruction_url},
                },
            })

        config = {
            "schemaVersion": 2,
            "id": page_id,
            "label": sequence_id.replace("__", " / "),
            "description": (
                "One of the five fixed DexYCB train-overfit examples, comparing "
                "input with 5 examples overfitting refinement (iter 150)."
            ),
            "dataset": "DexYCB",
            "split": CATALOG_SPLIT,
            "objectName": groundtruth["objects"]["target_name"],
            "fps": 30,
            "frameCount": int(groundtruth["timeline"]["frame_count"]),
            "baselines": baselines,
        }
        (config_root / f"{page_id}.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8",
        )

    for old_config in config_root.glob("dexycb-five-examples-train-overfit--*.json"):
        if old_config.stem not in exported_ids:
            old_config.unlink()
    print(f"Exported {len(exported_ids)} five-example train-overfit configs")


if __name__ == "__main__":
    main()
