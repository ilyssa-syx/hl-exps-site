#!/usr/bin/env python3
"""Validate example configs and build the lightweight site manifest."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs" / "examples"
OUTPUT = ROOT / "public" / "data" / "manifest.json"
REQUIRED = {"schemaVersion", "id", "label", "fps", "frameCount", "views"}


def main() -> None:
    examples = []
    seen = set()
    for path in sorted(CONFIG_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        missing = REQUIRED - payload.keys()
        if missing:
            raise ValueError(f"{path}: missing {sorted(missing)}")
        if payload["schemaVersion"] != 1:
            raise ValueError(f"{path}: unsupported schemaVersion")
        if payload["id"] in seen:
            raise ValueError(f"{path}: duplicate id {payload['id']!r}")
        if not isinstance(payload["frameCount"], int) or payload["frameCount"] <= 0:
            raise ValueError(f"{path}: frameCount must be a positive integer")
        if not isinstance(payload["fps"], (int, float)) or payload["fps"] <= 0:
            raise ValueError(f"{path}: fps must be positive")
        seen.add(payload["id"])
        examples.append(payload)

    if not examples:
        raise ValueError(f"no example configs found below {CONFIG_DIR}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"schemaVersion": 1, "examples": examples}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(examples)} example(s) to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
