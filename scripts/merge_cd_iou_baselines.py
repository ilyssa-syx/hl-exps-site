#!/usr/bin/env python3
"""Append CD-H/IoU checkpoint baselines to selected primary-site samples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "configs/examples"
CHECKPOINTS = ROOT / "configs/experiments/cd-iou-20261026/examples"
COLORS = {
    "input": "#55a7ff",
    "refined-20261023": "#ff6f91",
    "first-e0001-i0002": "#f6c85f",
    "third-e0003-i0000": "#62e0c5",
    "fourth-e0002-i0001": "#a78bfa",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence-id", action="append", required=True)
    args = parser.parse_args()
    for sequence_id in args.sequence_id:
        primary_path = PRIMARY / f"{sequence_id}.json"
        checkpoint_path = CHECKPOINTS / f"{sequence_id}.json"
        primary = json.loads(primary_path.read_text(encoding="utf-8"))
        checkpoints = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if primary["frameCount"] != checkpoints["frameCount"]:
            raise ValueError(f"{sequence_id}: frame counts differ")
        if primary["objectName"] != checkpoints["objectName"]:
            raise ValueError(f"{sequence_id}: object names differ")
        original = primary["baselines"][:2]
        if [item["id"] for item in original] != ["input", "refined-20261023"]:
            raise ValueError(f"{sequence_id}: primary baselines do not start with input/refined")
        primary["baselines"] = original + checkpoints["baselines"]
        for baseline in primary["baselines"]:
            baseline["color"] = COLORS[baseline["id"]]
        primary["description"] = (
            "DexYCB sequence comparing input, refined-20261023, and three CD-H/IoU checkpoints."
        )
        primary_path.write_text(json.dumps(primary, indent=2) + "\n", encoding="utf-8")
        print(f"Merged five baselines into {primary_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
