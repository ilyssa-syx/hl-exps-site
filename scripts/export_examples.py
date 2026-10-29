#!/usr/bin/env python3
"""Validate experiment configs and build site manifests and HTML entries."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public/data"
REQUIRED = {"schemaVersion", "id", "label", "fps", "frameCount", "baselines", "split"}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
COLLECTIONS = (
    {
        "config_dir": ROOT / "configs/examples",
        "output": PUBLIC_DATA / "manifest.json",
        "samples_dir": ROOT / "samples",
        "manifest_path": "data/manifest.json",
        "catalog_path": "",
        "expected_baselines": (
            ["input", "refined-20261023"],
            ["input", "refined-20261023", "first-e0001-i0002", "third-e0003-i0000", "fourth-e0002-i0001"],
            ["scaled-input-20261029", "exp4-20261029", "exp5-20261029"],
            ["input", "refined-20261023", "scaled-input-20261029", "exp4-20261029", "exp5-20261029"],
            ["input", "refined-20261023", "first-e0001-i0002", "third-e0003-i0000", "fourth-e0002-i0001", "scaled-input-20261029", "exp4-20261029", "exp5-20261029"],
        ),
        "catalog": {
            "eyebrow": "DexYCB · 2026-10-23 evaluation",
            "title": "Experiment samples",
            "description": "41 sequences · legacy and scaled-input baselines · per-sequence 2D/3D comparison",
            "metricSet": "spider", "sampleRoot": "samples",
            "relatedCatalogs": [{"label": "CD-H / IoU checkpoint comparison →", "url": "experiments/cd-iou-20261026/"}],
        },
    },
    {
        "config_dir": ROOT / "configs/experiments/cd-iou-20261026/examples",
        "output": PUBLIC_DATA / "cd-iou-20261026.json",
        "samples_dir": ROOT / "experiments/cd-iou-20261026/samples",
        "manifest_path": "data/cd-iou-20261026.json",
        "catalog_path": "experiments/cd-iou-20261026/",
        "expected_baselines": (["first-e0001-i0002", "third-e0003-i0000", "fourth-e0002-i0001"],),
        "catalog": {
            "eyebrow": "DexYCB · 2026-10-26 evaluation",
            "title": "CD-H / IoU checkpoint comparison",
            "description": "30 sequences · 20 validation + 10 test · three refinement checkpoints",
            "metricSet": "cd-iou", "sampleRoot": "experiments/cd-iou-20261026/samples",
            "relatedCatalogs": [{"label": "← Input / refined / SPIDER", "url": ""}],
        },
    },
)


def sample_html(sample_id: str, label: str, manifest_path: str, catalog_path: str) -> str:
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
  <body data-sample-id="{escaped_id}" data-manifest="{manifest_path}" data-catalog="{catalog_path}">
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
'''


def catalog_html(manifest_path: str) -> str:
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="HOI reconstruction experiment catalog" />
    <title>HL Experiments</title>
  </head>
  <body data-manifest="{manifest_path}">
    <div id="app"></div>
    <script type="module" src="/src/catalog.js"></script>
  </body>
</html>
'''


def export_collection(collection: dict) -> int:
    examples, seen = [], set()
    for path in sorted(collection["config_dir"].glob("*.json")):
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
        if baseline_ids not in collection["expected_baselines"]:
            raise ValueError(f"{path}: unexpected baselines {baseline_ids}")
        seen.add(payload["id"])
        examples.append(payload)
        page = collection["samples_dir"] / payload["id"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(sample_html(
            payload["id"], payload["label"], collection["manifest_path"], collection["catalog_path"],
        ), encoding="utf-8")
    if not examples:
        raise ValueError(f"no example configs found below {collection['config_dir']}")
    for page in collection["samples_dir"].glob("*/index.html"):
        if page.parent.name not in seen:
            shutil.rmtree(page.parent)
    collection["output"].parent.mkdir(parents=True, exist_ok=True)
    collection["output"].write_text(json.dumps({
        "schemaVersion": 2, "catalog": collection["catalog"], "examples": examples,
    }, indent=2) + "\n", encoding="utf-8")
    return len(examples)


def main() -> None:
    for collection in COLLECTIONS:
        count = export_collection(collection)
        if collection["catalog_path"]:
            catalog = ROOT / collection["catalog_path"] / "index.html"
            catalog.parent.mkdir(parents=True, exist_ok=True)
            catalog.write_text(catalog_html(collection["manifest_path"]), encoding="utf-8")
        print(f"Exported {count} example(s) to {collection['output'].relative_to(ROOT)}")


if __name__ == "__main__":
    main()
