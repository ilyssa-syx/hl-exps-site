#!/usr/bin/env python3
"""Export RGB-only repeat comparisons on the report test sequence sets."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
from fractions import Fraction


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
FFMPEG = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/ffmpeg")
FFPROBE = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/ffprobe")
MANO = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")

RUNS = (
    {
        "id": "rgb-only-overfit-r1",
        "label": "A1",
        "ho3d_label": "RGB-only overfit R1",
        "color": "#f43f5e",
        "dexycb_eval": "rgb-only-5-case-overfit-repeat-1-q0138-dexycb-test",
        "ho3d_eval": "rgb-only-5-case-overfit-repeat-1-q0138-ho3d-test",
    },
    {
        "id": "rgb-only-overfit-r2",
        "label": "A2",
        "ho3d_label": "RGB-only overfit R2",
        "color": "#14b8a6",
        "dexycb_eval": "rgb-only-5-case-overfit-repeat-2-q0162-dexycb-test",
        "ho3d_eval": "rgb-only-5-case-overfit-repeat-2-q0162-ho3d-test",
    },
    {
        "id": "rgb-only-overfit-r3",
        "label": "A3",
        "ho3d_label": "RGB-only overfit R3",
        "color": "#3b82f6",
        "dexycb_eval": "rgb-only-5-case-overfit-repeat-3-q0168-dexycb-test",
        "ho3d_eval": "rgb-only-5-case-overfit-repeat-3-q0168-ho3d-test",
    },
    {
        "id": "rgb-only-train-gt-assisted-overfit-r1",
        "label": "B1",
        "color": "#a855f7",
        "dexycb_eval": (
            "rgb-only-5-case-train-gt-assisted-overfit-repeat-1-q0199-dexycb-test"
        ),
        "dexycb_release": (
            "20261128-rgb-only-train-gt-assisted-repeats-dexycb-report20"
        ),
    },
    {
        "id": "rgb-only-train-gt-assisted-overfit-r2",
        "label": "B2",
        "color": "#f59e0b",
        "dexycb_eval": (
            "rgb-only-5-case-train-gt-assisted-overfit-repeat-2-q0139-dexycb-test"
        ),
        "dexycb_release": (
            "20261128-rgb-only-train-gt-assisted-repeats-dexycb-report20"
        ),
    },
    {
        "id": "rgb-only-train-gt-assisted-overfit-r3",
        "label": "B3",
        "color": "#84cc16",
        "dexycb_eval": (
            "rgb-only-5-case-train-gt-assisted-overfit-repeat-3-q0175-dexycb-test"
        ),
        "dexycb_release": (
            "20261128-rgb-only-train-gt-assisted-repeats-dexycb-report20"
        ),
    },
)

DATASETS = (
    {
        "key": "dexycb",
        "data": HOI_ROOT / "data/dexycb_report",
        "expected_count": 20,
        "dataset": "DexYCB report",
        "split": "report test",
        "id_prefix": "dexycb-report--",
        "config_root": ROOT / "configs/DEXYCB_REPORT_TEST/examples",
        "release": "20261128-rgb-only-repeats-dexycb-report20",
        "fps": 30,
        "hide_metrics": False,
    },
    {
        "key": "ho3d",
        "data": HOI_ROOT / "data/ho3d_report_stride5",
        "expected_count": 18,
        "dataset": "HO3D report stride-5",
        "split": "report test stride-5",
        "id_prefix": "ho3d-report-stride5--",
        "config_root": ROOT / "configs/HO3D_REPORT_STRIDE5_TEST/examples",
        "release": "20261128-rgb-only-repeats-ho3d-report18-stride5",
        "fps": 30,
        "hide_metrics": False,
    },
)


def stat(row: dict[str, str], prefix: str, unit: str, *, scored: bool = False) -> dict:
    value = {
        "count": int(row[f"{prefix}_count"]),
        "mean": float(row[f"{prefix}_mean_{unit}"]),
        "median": float(row[f"{prefix}_median_{unit}"]),
    }
    if scored:
        value["scoredMean"] = float(row[f"{prefix}_scored_mean_{unit}"])
    return value


def load_metrics(path: Path) -> dict[str, dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    result = {}
    for row in rows:
        if int(row["add_aligned_count"]) == 0:
            continue
        metrics = {
            "addAligned": stat(row, "add_aligned", "cm"),
            "objectAmodalIou": stat(row, "object_amodal", "iou", scored=True),
            "handAmodalIou": stat(row, "hand_amodal", "iou", scored=True),
            "cdH": stat(row, "cd_h", "cm", scored=True),
            "objRel": stat(row, "obj_rel", "cm"),
            "wristTranslation": stat(row, "wrist_pose_translation", "mm"),
        }
        if "wrist_pose_rotation_count" in row:
            metrics["wristRotation"] = stat(row, "wrist_pose_rotation", "deg")
        result[row["sequence_id"]] = metrics
    return result


def ensure_video(source: Path, output: Path, fps: int) -> None:
    if output.is_file():
        frame_rate = subprocess.check_output([
            str(FFPROBE), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "default=nokey=1:noprint_wrappers=1", str(output),
        ], text=True).strip()
        if Fraction(frame_rate) == fps:
            return
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(fps), "-pattern_type", "glob", "-i", "*.jpg",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ], cwd=source, check=True)


def ensure_reconstruction(source: Path, output: Path, hand_side: str) -> None:
    if (output / "reconstruction.json").is_file():
        return
    subprocess.run([
        str(PYTHON), str(ROOT / "scripts/export_reconstruction.py"),
        "--result-dir", str(source), "--mano-dir", str(MANO),
        "--output", str(output), "--hand-side", hand_side,
    ], check=True)


def export_dataset(dataset: dict) -> int:
    runs = tuple(item for item in RUNS if f"{dataset['key']}_eval" in item)
    data_root = dataset["data"]
    sequence_ids = sorted(
        path.name for path in (data_root / "test").iterdir() if path.is_dir()
    )
    if len(sequence_ids) != dataset["expected_count"]:
        raise ValueError(
            f"expected {dataset['expected_count']} {dataset['key']} sequences, "
            f"found {len(sequence_ids)}"
        )

    result_roots = {
        item["id"]: HOI_ROOT / "eval_runs" / item[f"{dataset['key']}_eval"]
        / "predictions/test"
        for item in runs
    }
    unavailable = {}
    for run_id, result_root in result_roots.items():
        result_ids = sorted(path.name for path in result_root.iterdir() if path.is_dir())
        if not set(result_ids) <= set(sequence_ids):
            raise ValueError(f"{run_id} has predictions outside {dataset['data']}")
        evaluation = next(item for item in runs if item["id"] == run_id)
        failures_path = (
            HOI_ROOT / "eval_runs" / evaluation[f"{dataset['key']}_eval"]
            / "metrics/failures.json"
        )
        failures = {
            item["sequence_id"]: item["reason"]
            for item in json.loads(failures_path.read_text(encoding="utf-8"))
        }
        missing = set(sequence_ids) - set(result_ids)
        if missing != set(failures):
            raise ValueError(
                f"{run_id} missing predictions do not match evaluator failures"
            )
        unavailable[run_id] = failures

    metrics = {}
    if not dataset["hide_metrics"]:
        for item in runs:
            path = (
                HOI_ROOT / "eval_runs" / item[f"{dataset['key']}_eval"]
                / "metrics/per_sequence.csv"
            )
            metrics[item["id"]] = load_metrics(path)
            expected_ids = sorted(
                set(sequence_ids) - set(unavailable[item["id"]])
            )
            if sorted(metrics[item["id"]]) != expected_ids:
                raise ValueError(
                    f"{item['id']} valid metrics differ from available predictions"
                )

    config_root = dataset["config_root"]
    config_root.mkdir(parents=True, exist_ok=True)
    asset_root = ROOT / "r2_assets/experiments" / dataset["release"]
    exported_ids = set()

    for sequence_id in sequence_ids:
        source_root = data_root / "test" / sequence_id
        groundtruth = json.loads(
            (source_root / "groundtruth/manifest.json").read_text(encoding="utf-8")
        )
        page_id = f"{dataset['id_prefix']}{sequence_id}"
        exported_ids.add(page_id)
        ensure_video(
            source_root / "rgb", asset_root / sequence_id / "input-rgb.mp4",
            dataset["fps"],
        )

        baselines = []
        unavailable_baselines = []
        for item in runs:
            label = item.get(f"{dataset['key']}_label", item["label"])
            if sequence_id in unavailable[item["id"]]:
                unavailable_baselines.append({
                    "id": item["id"],
                    "label": label,
                    "color": item["color"],
                    "reason": unavailable[item["id"]][sequence_id],
                })
                continue
            release = item.get(f"{dataset['key']}_release", dataset["release"])
            run_asset_root = ROOT / "r2_assets/experiments" / release
            reconstruction = (
                run_asset_root / sequence_id / item["id"] / "reconstruction"
            )
            ensure_reconstruction(
                result_roots[item["id"]] / sequence_id,
                reconstruction,
                groundtruth["hand"]["side"],
            )
            reconstruction_url = (
                f"experiments/{release}/{sequence_id}/{item['id']}"
                "/reconstruction/reconstruction.json"
            )
            baseline = {
                "id": item["id"],
                "label": label,
                "color": item["color"],
                "views": {
                    "overlay2d": {
                        "rgb": {
                            "type": "video",
                            "url": (
                                f"experiments/{dataset['release']}/{sequence_id}"
                                "/input-rgb.mp4"
                            ),
                        },
                        "reconstruction": reconstruction_url,
                    },
                    "scene3d": {"reconstruction": reconstruction_url},
                },
            }
            if not dataset["hide_metrics"]:
                baseline["metrics"] = metrics[item["id"]][sequence_id]
            baselines.append(baseline)

        if dataset["key"] == "dexycb":
            object_name = groundtruth["objects"]["target_name"]
            frame_count = int(groundtruth["timeline"]["frame_count"])
            description = (
                "DexYCB report test sequence comparing A1–A3 RGB-only repeats with "
                "B1–B3 train-GT-assisted RGB-only repeats."
            )
        else:
            object_name = groundtruth["object"]["name"]
            frame_count = int(groundtruth["frame_count"])
            description = (
                "HO3D report test sequence comparing three independently optimized "
                "RGB-only five-case overfit runs on stride-5 frames."
            )

        config = {
            "schemaVersion": 2,
            "id": page_id,
            "label": sequence_id.replace("__", " / "),
            "description": description,
            "dataset": dataset["dataset"],
            "split": dataset["split"],
            "objectName": object_name,
            "fps": dataset["fps"],
            "frameCount": frame_count,
            "baselines": baselines,
        }
        if unavailable_baselines:
            config["unavailableBaselines"] = unavailable_baselines
        if dataset["hide_metrics"]:
            config["hideMetrics"] = True
        else:
            config["metricLabel"] = "RGB-only report evaluation"
            if dataset["key"] == "dexycb":
                config["metricNote"] = (
                    "Per-sequence means from each frozen DexYCB report-test evaluator "
                    "output. Unavailable runs have no frozen prediction for this sequence."
                )
            else:
                config["metricNote"] = (
                    "Per-sequence means from the completed 18-sequence HO3D "
                    "release-full-coverage evaluations on stride-5 predictions."
                )
        (config_root / f"{page_id}.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8",
        )

    for old_config in config_root.glob("*.json"):
        if old_config.stem not in exported_ids:
            old_config.unlink()
    return len(exported_ids)


def main() -> None:
    counts = {dataset["key"]: export_dataset(dataset) for dataset in DATASETS}
    print(
        f"Exported {counts['dexycb']} DexYCB report and "
        f"{counts['ho3d']} HO3D stride-5 report configs"
    )


if __name__ == "__main__":
    main()
