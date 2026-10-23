#!/usr/bin/env python3
"""Validate example configs and build the lightweight site manifest."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "configs" / "examples"
OUTPUT = ROOT / "public" / "data" / "manifest.json"
SAMPLES_DIR = ROOT / "samples"
REQUIRED = {"schemaVersion", "id", "label", "fps", "frameCount", "baselines", "split"}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def sample_html(sample_id: str, label: str) -> str:
    escaped_id = sample_id.replace("&", "&amp;").replace('"', "&quot;")
    escaped_label = label.replace("&", "&amp;").replace("<", "&lt;")
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="HOI reconstruction sample {escaped_label}" />
    <title>{escaped_label} · HL Experiments</title>
  </head>
  <body data-sample-id="{escaped_id}">
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
'''


def main() -> None:
    examples = []
    seen = set()
    for path in sorted(CONFIG_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        missing = REQUIRED - payload.keys()
        if missing:
            raise ValueError(f"{path}: missing {sorted(missing)}")
        if payload["schemaVersion"] != 2:
            raise ValueError(f"{path}: unsupported schemaVersion")
        if not isinstance(payload["id"], str) or not SAFE_ID.fullmatch(payload["id"]):
            raise ValueError(f"{path}: id is not URL-safe")
        if payload["id"] in seen:
            raise ValueError(f"{path}: duplicate id {payload['id']!r}")
        if not isinstance(payload["frameCount"], int) or payload["frameCount"] <= 0:
            raise ValueError(f"{path}: frameCount must be a positive integer")
        if not isinstance(payload["fps"], (int, float)) or payload["fps"] <= 0:
            raise ValueError(f"{path}: fps must be positive")
        baseline_ids = [item.get("id") for item in payload["baselines"]]
        if baseline_ids != ["input", "refined-20261023"]:
            raise ValueError(f"{path}: expected input and refined-20261023 baselines")
        seen.add(payload["id"])
        examples.append(payload)
        page = SAMPLES_DIR / payload["id"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(sample_html(payload["id"], payload["label"]), encoding="utf-8")

    if not examples:
        raise ValueError(f"no example configs found below {CONFIG_DIR}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"schemaVersion": 2, "examples": examples}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(examples)} example(s) to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
