#!/usr/bin/env python3
"""Export curated, visible DexYCB train/validation comparisons."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
DATA = HOI_ROOT / "data/dexycb_hl_v3_100_20_20_cleaned"
REVIEW_ROOT = HOI_ROOT / "eval_runs/dexycb-train-val-visual-review"
EXP4_RESULTS = REVIEW_ROOT / "exp-4"
EXP7_NEW_RESULTS = REVIEW_ROOT / "exp-7"
EXP7_VERSION = (
    HOI_ROOT / "runs/run-20261101-dr-sequence/epochs/0002/iterations/0001"
)
EXP8_RUN = HOI_ROOT / "runs/run-20261106"
EXP8_VERSION = EXP8_RUN / "epochs/0011/iterations/0001"
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
MANO = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")
RELEASE = "20261108-dexycb-train-val-review"

SELECTED = {
    "train": (
        "20200928-subject-07__20200928_145724__836212060125",  # banana
        "20200709-subject-01__20200709_151543__840412060917",  # power drill
        "20200918-subject-06__20200918_113441__932122061900",  # sugar box
        "20201002-subject-08__20201002_104758__932122060857",  # master chef can
    ),
    "validation": (
        "20200709-subject-01__20200709_151948__836212060125",  # wood block
        "20200709-subject-01__20200709_153148__932122062010",  # clamp
        "20200709-subject-01__20200709_142123__932122061900",  # master chef can
        "20200813-subject-02__20200813_152513__839512060362",  # potted meat can
    ),
}

BASELINES = (
    {"id": "input", "label": "input", "color": "#fb923c"},
    {"id": "exp-4", "label": "Exp 4", "color": "#22d3ee"},
    {"id": "exp-7", "label": "Exp 7", "color": "#a78bfa"},
    {"id": "exp-8-latest", "label": "Exp 8 (latest)", "color": "#34d399"},
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


def load_metrics(*paths: Path) -> dict[str, dict]:
    rows: dict[str, dict[str, str]] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                rows[row["sequence_id"]] = row
    result = {}
    for sequence_id, row in rows.items():
        result[sequence_id] = {
            "addAligned": _stat(row, "add_aligned", "cm"),
            "objectAmodalIou": _stat(
                row, "object_amodal", "iou", scored=True,
            ),
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


def metrics_for(baseline_id: str, split: str) -> dict[str, dict]:
    if baseline_id == "input":
        return load_metrics(
            EXP8_RUN / f"baseline/results/{split}/per_sequence.csv"
        )
    if baseline_id == "exp-4":
        return load_metrics(REVIEW_ROOT / f"exp-4-metrics/{split}/per_sequence.csv")
    if baseline_id == "exp-7":
        return load_metrics(
            REVIEW_ROOT / f"exp-7-metrics/{split}/per_sequence.csv"
        )
    if baseline_id == "exp-8-latest":
        return load_metrics(EXP8_VERSION / f"results/{split}/per_sequence.csv")
    raise ValueError(f"unknown baseline: {baseline_id}")


def result_dir(baseline_id: str, split: str, sample_id: str) -> Path:
    if baseline_id == "input":
        return DATA / split / sample_id / "input/final"
    if baseline_id == "exp-4":
        return EXP4_RESULTS / split / sample_id
    if baseline_id == "exp-7":
        supplemental = EXP7_NEW_RESULTS / split / sample_id
        return supplemental if supplemental.is_dir() else EXP7_VERSION / f"results/{split}/{sample_id}"
    if baseline_id == "exp-8-latest":
        return EXP8_VERSION / f"results/{split}/{sample_id}"
    raise ValueError(f"unknown baseline: {baseline_id}")


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
    exported_ids = set()

    for split, sample_ids in SELECTED.items():
        metrics = {
            baseline["id"]: metrics_for(baseline["id"], split)
            for baseline in BASELINES
        }
        for sample_id in sample_ids:
            source_root = DATA / split / sample_id
            groundtruth = json.loads(
                (source_root / "groundtruth/manifest.json").read_text()
            )
            page_id = f"dexycb-{split}--{sample_id}"
            exported_ids.add(page_id)
            sample_assets = asset_root / split / sample_id
            rgb = sample_assets / "input-rgb.mp4"
            ensure_rgb_video(source_root, rgb)

            baselines = []
            for baseline in BASELINES:
                baseline_id = baseline["id"]
                if sample_id not in metrics[baseline_id]:
                    raise ValueError(
                        f"missing {baseline_id} {split} metrics for {sample_id}"
                    )
                source = result_dir(baseline_id, split, sample_id)
                if not source.is_dir():
                    raise FileNotFoundError(source)
                reconstruction = sample_assets / baseline_id / "reconstruction"
                ensure_reconstruction(
                    source, reconstruction, groundtruth["hand"]["side"],
                )
                reconstruction_url = (
                    f"experiments/{RELEASE}/{split}/{sample_id}/{baseline_id}"
                    "/reconstruction/reconstruction.json"
                )
                baselines.append({
                    **baseline,
                    "metrics": metrics[baseline_id][sample_id],
                    "views": {
                        "overlay2d": {
                            "rgb": {
                                "type": "video",
                                "url": (
                                    f"experiments/{RELEASE}/{split}/{sample_id}"
                                    "/input-rgb.mp4"
                                ),
                            },
                            "reconstruction": reconstruction_url,
                        },
                        "scene3d": {"reconstruction": reconstruction_url},
                    },
                })

            config = {
                "schemaVersion": 2,
                "id": page_id,
                "label": sample_id.replace("__", " / "),
                "description": (
                    f"Curated DexYCB {split} sequence with a clearly visible target "
                    "and non-trivial reconstruction error. Compare input, Exp 4, "
                    "Exp 7, and Exp 8 (latest)."
                ),
                "dataset": "DexYCB",
                "split": split,
                "objectName": groundtruth["objects"]["target_name"],
                "fps": 30,
                "frameCount": int(groundtruth["timeline"]["frame_count"]),
                "baselines": baselines,
            }
            (config_root / f"{page_id}.json").write_text(
                json.dumps(config, indent=2) + "\n", encoding="utf-8",
            )

    for old_config in config_root.glob("dexycb-train--*.json"):
        if old_config.stem not in exported_ids:
            old_config.unlink()
    for old_config in config_root.glob("dexycb-validation--*.json"):
        if old_config.stem not in exported_ids:
            old_config.unlink()
    print(f"Exported {len(exported_ids)} curated DexYCB train/validation configs")


if __name__ == "__main__":
    main()
