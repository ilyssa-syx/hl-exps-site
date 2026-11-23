#!/usr/bin/env python3
"""Export the final DexYCB 20 and OakInk GT-texture 11 test comparison."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOI_ROOT = Path("/home/ilyssa_syx/models/hoi-recon-hl")
PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
DEXYCB_DATA = HOI_ROOT / "data/dexycb_hl_v3_100_20_20"
OAKINK_DATA = HOI_ROOT / "data/oakink1_sp0_sample11_rgb_unitless_textured_mesh_first_mask_v1"
DEXYCB_RELEASE = "20261029-amodal-iou"
OAKINK_RELEASE = "20261116-oakink-sample20"


def method(
    method_id: str,
    label: str,
    color: str,
    eval_name: str,
    asset: str,
) -> dict:
    run = HOI_ROOT / "eval_runs" / eval_name
    return {
        "id": method_id,
        "label": label,
        "color": color,
        "results": run / "predictions/test",
        "metrics": run / "metrics/per_sequence.csv",
        "asset": asset,
    }


DEXYCB_METHODS = (
    method(
        "baseline", "baseline", "#34d399",
        "exp8-e0005-i0003-dexycb-test",
        "baseline-e0005-i0003-up-to-30-20261123",
    ),
    method(
        "five-examples-overfitting-refinement", "5 examples overfitting refinement", "#f43f5e",
        "5-cases-q0154-dexycb-hl-v3-test",
        "five-examples-overfit-q0154-20261114",
    ),
    method(
        "baseline-lower-batch", "baseline + lower batch", "#3b82f6",
        "linear-batch-3-e0000-i0028-dexycb-test",
        "exp11-e0000-i0028-20261123",
    ),
    method(
        "baseline-lower-batch-batch-inference", "baseline + lower batch + batch inference", "#e879f9",
        "linear-bs3-batch-v1-e0000-i0024-dexycb-test",
        "exp13-e0000-i0024-batch-v1-20261123",
    ),
    method(
        "five-examples-overfitting-reconstruction", "5 examples overfitting reconstruction", "#14b8a6",
        "5-examples-overfit-reconstruction-q0154-dexycb-test",
        "five-examples-overfit-reconstruction-q0154-20261123",
    ),
    method(
        "baseline-lower-batch-reconstruction", "baseline + lower batch + reconstruction", "#f59e0b",
        "linear-bs3-reconstruction-e0000-i0029-dexycb-test",
        "baseline-lower-batch-reconstruction-e0000-i0029-20261123",
    ),
)


OAKINK_METHODS = (
    method(
        "baseline", "baseline", "#34d399",
        "baseline-e0005-i0003-oakink-test", "exp8",
    ),
    method(
        "five-examples-overfitting-refinement", "5 examples overfitting refinement", "#f43f5e",
        "5-examples-overfitting-refinement-q0154-oakink-test", "five-examples-overfit",
    ),
    method(
        "baseline-lower-batch", "baseline + lower batch", "#3b82f6",
        "linear-batch-3-e0000-i0028-oakink-test", "exp11-e0000-i0028-20261123",
    ),
    method(
        "baseline-lower-batch-batch-inference", "baseline + lower batch + batch inference", "#e879f9",
        "baseline-lower-batch-batch-inference-e0000-i0024-oakink-test",
        "exp13-e0000-i0024-batch-v1-20261123",
    ),
    method(
        "five-examples-overfitting-reconstruction", "5 examples overfitting reconstruction", "#14b8a6",
        "5-examples-overfit-reconstruction-q0154-oakink-test",
        "five-examples-overfit-reconstruction-q0154-20261123",
    ),
    method(
        "baseline-lower-batch-reconstruction", "baseline + lower batch + reconstruction", "#f59e0b",
        "linear-bs3-reconstruction-e0000-i0029-oakink-test",
        "baseline-lower-batch-reconstruction-e0000-i0029-20261123",
    ),
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
    return {
        row["sequence_id"]: {
            "addAligned": stat(row, "add_aligned", "cm"),
            "objectAmodalIou": stat(row, "object_amodal", "iou", scored=True),
            "handAmodalIou": stat(row, "hand_amodal", "iou", scored=True),
            "cdH": stat(row, "cd_h", "cm", scored=True),
            "objRel": stat(row, "obj_rel", "cm"),
            "wristTranslation": stat(row, "wrist_pose_translation", "mm"),
            "wristRotation": stat(row, "wrist_pose_rotation", "deg"),
        }
        for row in rows
    }


def ensure_reconstruction(source: Path, output: Path, mano: Path, hand_side: str) -> None:
    if (output / "reconstruction.json").is_file():
        return
    subprocess.run([
        str(PYTHON), str(ROOT / "scripts/export_reconstruction.py"),
        "--result-dir", str(source), "--mano-dir", str(mano),
        "--output", str(output), "--hand-side", hand_side,
    ], check=True)


def validate_methods(methods: tuple[dict, ...], sequence_ids: list[str]) -> dict[str, dict]:
    expected = set(sequence_ids)
    metrics = {}
    for item in methods:
        result_ids = {path.name for path in item["results"].iterdir() if path.is_dir()}
        if not expected <= result_ids:
            missing = sorted(expected - result_ids)
            raise ValueError(f"{item['label']} is missing final test results: {missing}")
        metrics[item["id"]] = load_metrics(item["metrics"])
        if not expected <= set(metrics[item["id"]]):
            missing = sorted(expected - set(metrics[item["id"]]))
            raise ValueError(f"{item['label']} is missing final test metrics: {missing}")
    return metrics


def baseline_payload(
    item: dict,
    metrics: dict[str, dict],
    sequence_id: str,
    release: str,
) -> dict:
    reconstruction = (
        f"experiments/{release}/{sequence_id}/{item['asset']}"
        "/reconstruction/reconstruction.json"
    )
    return {
        "id": item["id"],
        "label": item["label"],
        "color": item["color"],
        "metrics": metrics[item["id"]][sequence_id],
        "views": {
            "overlay2d": {
                "rgb": {
                    "type": "video",
                    "url": f"experiments/{release}/{sequence_id}/input-rgb.mp4",
                },
                "reconstruction": reconstruction,
            },
            "scene3d": {"reconstruction": reconstruction},
        },
    }


def export_dexycb() -> set[str]:
    sequence_ids = sorted(path.name for path in (DEXYCB_DATA / "test").iterdir() if path.is_dir())
    if len(sequence_ids) != 20:
        raise ValueError(f"expected 20 DexYCB test sequences, found {len(sequence_ids)}")
    metrics = validate_methods(DEXYCB_METHODS, sequence_ids)
    asset_root = ROOT / "r2_assets/experiments" / DEXYCB_RELEASE
    config_root = ROOT / "configs/examples"
    mano = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")
    for sequence_id in sequence_ids:
        source = DEXYCB_DATA / "test" / sequence_id
        groundtruth = json.loads((source / "groundtruth/manifest.json").read_text())
        if not (asset_root / sequence_id / "input-rgb.mp4").is_file():
            raise FileNotFoundError(f"missing staged RGB for {sequence_id}")
        baselines = []
        for item in DEXYCB_METHODS:
            ensure_reconstruction(
                item["results"] / sequence_id,
                asset_root / sequence_id / item["asset"] / "reconstruction",
                mano,
                groundtruth["hand"]["side"],
            )
            baselines.append(baseline_payload(item, metrics, sequence_id, DEXYCB_RELEASE))
        config = {
            "schemaVersion": 2,
            "id": sequence_id,
            "label": sequence_id.replace("__", " / "),
            "description": "DexYCB held-out test sequence comparing the six finalized methods.",
            "dataset": "DexYCB",
            "split": "test",
            "objectName": groundtruth["objects"]["target_name"],
            "fps": 30,
            "frameCount": int(groundtruth["timeline"]["frame_count"]),
            "baselines": baselines,
        }
        (config_root / f"{sequence_id}.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8",
        )
    return set(sequence_ids)


def export_oakink() -> set[str]:
    manifest = json.loads((OAKINK_DATA / "manifest.json").read_text(encoding="utf-8"))
    rows = [row for row in manifest["sequences"] if row["split"] == "test"]
    sequence_ids = [row["sequence_id"] for row in rows]
    if len(sequence_ids) != 11:
        raise ValueError(f"expected 11 OakInk GT-texture test sequences, found {len(sequence_ids)}")
    metrics = validate_methods(OAKINK_METHODS, sequence_ids)
    asset_root = ROOT / "r2_assets/experiments" / OAKINK_RELEASE
    config_root = ROOT / "configs/examples"
    mano = HOI_ROOT / "assets/mano"
    for row in rows:
        sequence_id = row["sequence_id"]
        if not (asset_root / sequence_id / "input-rgb.mp4").is_file():
            raise FileNotFoundError(f"missing staged RGB for {sequence_id}")
        baselines = []
        for item in OAKINK_METHODS:
            ensure_reconstruction(
                item["results"] / sequence_id,
                asset_root / sequence_id / item["asset"] / "reconstruction",
                mano,
                "right",
            )
            baselines.append(baseline_payload(item, metrics, sequence_id, OAKINK_RELEASE))
        config = {
            "schemaVersion": 2,
            "id": sequence_id,
            "label": sequence_id.replace("__", " / "),
            "description": "OakInk SP0 GT-texture held-out test sequence comparing the six finalized methods.",
            "dataset": "OakInk",
            "split": "test",
            "objectName": row["object_id"],
            "fps": 30,
            "frameCount": int(row["frame_count"]),
            "metricLabel": "OakInk evaluation",
            "metricNote": "Per-sequence OakInk metrics on the shared GT-texture 11 test set.",
            "baselines": baselines,
        }
        (config_root / f"{sequence_id}.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8",
        )
    return set(sequence_ids)


def remove_retired_oakink_configs(keep: set[str]) -> int:
    removed = 0
    for path in (ROOT / "configs/examples").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("dataset") == "OakInk" and payload.get("id") not in keep:
            path.unlink()
            removed += 1
    return removed


def main() -> None:
    dexycb = export_dexycb()
    oakink = export_oakink()
    removed = remove_retired_oakink_configs(oakink)
    print(
        f"Exported {len(dexycb)} DexYCB and {len(oakink)} OakInk final test configs; "
        f"removed {removed} retired OakInk configs"
    )


if __name__ == "__main__":
    main()
