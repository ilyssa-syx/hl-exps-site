#!/usr/bin/env python3
"""Export the dated 20-val/10-test evaluation run used by the public site."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = Path("/home/ilyssa_syx/models/hoi-recon-hl/eval_runs/cd-spider-e0005-i0003-dexycb-v3-100-20-10")
DEFAULT_DATA = Path("/home/ilyssa_syx/models/hoi-recon-hl/data/dexycb_hl_v3_100_20_10")
DEFAULT_MANO = Path("/home/ilyssa_syx/models/hoi-from-rgb-d/mano_v1_2/models")
DEFAULT_PYTHON = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/python")
DEFAULT_FFMPEG = Path("/home/ilyssa_syx/miniforge3/envs/dynhamr/bin/ffmpeg")
BASELINES = (("input", "input"), ("refined", "refined-20261023"))
LEFT_HAND_RECONSTRUCTION_VERSION = "20261023-mano-left-v2"


def command(*parts: object) -> None:
    subprocess.run([str(part) for part in parts], check=True)


def find_trial(metrics_dir: Path, sample_id: str) -> Path | None:
    matches = list((metrics_dir / "spider" / "work").glob(
        f"processed/hoi_reconstruction_eval/sharpa/*/{sample_id}/0/trajectory_mjwp.npz"
    ))
    return matches[0].parent if len(matches) == 1 else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--mano-dir", type=Path, default=DEFAULT_MANO)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--skip-spider-render", action="store_true")
    args = parser.parse_args()

    asset_root = ROOT / "r2_assets" / "experiments" / "20261023"
    config_root = ROOT / "configs" / "examples"
    config_root.mkdir(parents=True, exist_ok=True)

    expected = {"validation": 20, "test": 10}
    written: set[str] = set()
    for split, expected_count in expected.items():
        samples = sorted((args.run / f"refined-{split}-predictions" / split).glob("*/manifest.json"))
        if len(samples) != expected_count:
            raise ValueError(f"{split}: expected {expected_count} samples, found {len(samples)}")
        for manifest_path in samples:
            sample_id = manifest_path.parent.name
            written.add(sample_id)
            source_root = args.data / split / sample_id
            groundtruth = json.loads((source_root / "groundtruth" / "manifest.json").read_text())
            frame_count = int(groundtruth["timeline"]["frame_count"])
            object_name = groundtruth["objects"]["target_name"]
            side = groundtruth["hand"]["side"]
            sample_assets = asset_root / sample_id
            rgb_out = sample_assets / "input-rgb.mp4"
            rgb_out.parent.mkdir(parents=True, exist_ok=True)
            if not rgb_out.exists():
                shutil.copy2(source_root / "input" / "color_video.mp4", rgb_out)

            baselines = []
            for source_name, public_name in BASELINES:
                prediction = args.run / f"{source_name}-{split}-predictions" / split / sample_id
                metrics_dir = args.run / f"{source_name}-{split}-metrics"
                reconstruction = sample_assets / public_name / "reconstruction"
                reconstruction_json = reconstruction / "reconstruction.json"
                if not reconstruction_json.exists():
                    command(
                        args.python, ROOT / "scripts" / "export_reconstruction.py",
                        "--result-dir", prediction, "--mano-dir", args.mano_dir,
                        "--output", reconstruction,
                    )
                reconstruction_url = (
                    f"experiments/20261023/{sample_id}/{public_name}/reconstruction/reconstruction.json"
                )
                if side == "left":
                    reconstruction_url += f"?v={LEFT_HAND_RECONSTRUCTION_VERSION}"
                baseline = {
                    "id": public_name,
                    "label": public_name,
                    "views": {
                        "overlay2d": {
                            "rgb": {"type": "video", "url": f"experiments/20261023/{sample_id}/input-rgb.mp4"},
                            "reconstruction": reconstruction_url,
                        },
                        "scene3d": {
                            "reconstruction": reconstruction_url,
                        },
                    },
                }
                metric_path = metrics_dir / "spider" / "metrics" / f"{sample_id}.json"
                trial = find_trial(metrics_dir, sample_id)
                if metric_path.exists() and trial is not None:
                    video = sample_assets / public_name / "spider.mp4"
                    if not video.exists() and not args.skip_spider_render:
                        command(
                            args.python, ROOT / "scripts" / "render_spider.py",
                            "--trial-dir", trial, "--output", video, "--ffmpeg", args.ffmpeg,
                        )
                    if video.exists():
                        metrics = json.loads(metric_path.read_text(), parse_constant=lambda _: None)
                        baseline["views"]["spider"] = {
                            "robot": "sharpa", "embodiment": side, "status": "evaluated",
                            "video": f"experiments/20261023/{sample_id}/{public_name}/spider.mp4",
                            "metrics": {
                                "addAuc10": metrics.get("add_auc10_mean"),
                                "positionErrorMeters": metrics.get("obj_pos_err"),
                                "rotationErrorRadians": metrics.get("obj_quat_err"),
                            },
                        }
                baselines.append(baseline)

            label = sample_id.replace("__", " / ")
            config = {
                "schemaVersion": 2, "id": sample_id, "label": label,
                "description": f"DexYCB {split} sequence comparing input with the 2026-10-23 refinement run.",
                "dataset": "DexYCB", "split": "val" if split == "validation" else "test",
                "objectName": object_name, "fps": 30, "frameCount": frame_count,
                "baselines": baselines,
            }
            (config_root / f"{sample_id}.json").write_text(json.dumps(config, indent=2) + "\n")

    for old in config_root.glob("*.json"):
        if old.stem not in written:
            old.unlink()
    print(f"Exported {len(written)} sample configs and assets below {asset_root}")


if __name__ == "__main__":
    main()
