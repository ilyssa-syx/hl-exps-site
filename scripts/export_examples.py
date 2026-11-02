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
METRIC_KEYS = {
    "addAligned",
    "objectAmodalIou",
    "handAmodalIou",
    "cdH",
    "objRel",
    "wristTranslation",
    "wristRotation",
}
OPTIONAL_METRIC_KEYS = {"wristRotation"}
COLLECTIONS = (
    {
        "config_groups": (
            {
                "config_dir": ROOT / "configs/examples",
                "expected_baselines": ([
                    "input",
                    "cd-iou-fourth-run-20261029",
                    "successful-differentiable-first-run-20261102",
                ],),
            },
            {
                "config_dir": ROOT / "configs/HO3D_v3-TEST/examples",
                "expected_baselines": ([
                    "input",
                    "cd-iou-fourth-run-20261029",
                    "successful-differentiable-first-run",
                ],),
            },
        ),
        "output": PUBLIC_DATA / "manifest.json",
        "samples_dir": ROOT / "samples",
        "manifest_path": "data/manifest.json",
        "catalog_path": "",
        "catalog": {
            "eyebrow": "DexYCB + HO3D v3 · input vs. two refined runs",
            "title": "Experiment samples",
            "description": "33 test sequences · input, CD-IoU fourth run, and differentiable first run · per-sequence 2D/3D comparison",
            "sampleRoot": "samples",
            "sections": [
                {"dataset": "DexYCB", "title": "dexycb-test"},
                {"dataset": "HO3D v3", "title": "HO3D_v3-TEST"},
            ],
            "relatedCatalogs": [],
        },
    },
)


def sample_html(
    sample_id: str, label: str, manifest_path: str, catalog_path: str,
    segment_id: str | None = None,
) -> str:
    escaped_id = sample_id.replace("&", "&amp;").replace('"', "&quot;")
    escaped_label = label.replace("&", "&amp;").replace("<", "&lt;")
    segment_attr = f' data-segment-id="{segment_id}"' if segment_id else ""
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="HOI reconstruction sample {escaped_label}" />
    <title>{escaped_label} · HL Experiments</title>
  </head>
  <body data-sample-id="{escaped_id}"{segment_attr} data-manifest="{manifest_path}" data-catalog="{catalog_path}">
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
'''


def sequence_html(sample_id: str, label: str, manifest_path: str, catalog_path: str) -> str:
    escaped_id = sample_id.replace("&", "&amp;").replace('"', "&quot;")
    escaped_label = label.replace("&", "&amp;").replace("<", "&lt;")
    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="HOI reconstruction sequence {escaped_label}" />
    <title>{escaped_label} · HL Experiments</title>
  </head>
  <body data-sample-id="{escaped_id}" data-manifest="{manifest_path}" data-catalog="{catalog_path}">
    <div id="app"></div>
    <script type="module" src="/src/sequence.js"></script>
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
    for group in collection["config_groups"]:
        paths = sorted(group["config_dir"].glob("*.json"))
        if not paths:
            raise ValueError(f"no example configs found below {group['config_dir']}")
        for path in paths:
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
            if baseline_ids not in group["expected_baselines"]:
                raise ValueError(f"{path}: unexpected baselines {baseline_ids}")
            for baseline in payload["baselines"]:
                metrics = baseline.get("metrics")
                metric_keys = set(metrics) if isinstance(metrics, dict) else set()
                if (
                    not isinstance(metrics, dict)
                    or not METRIC_KEYS - OPTIONAL_METRIC_KEYS <= metric_keys
                    or metric_keys - METRIC_KEYS
                ):
                    raise ValueError(
                        f"{path}: {baseline.get('id')} has invalid per-sequence metrics"
                    )
            seen.add(payload["id"])
            examples.append(payload)
            page = collection["samples_dir"] / payload["id"] / "index.html"
            page.parent.mkdir(parents=True, exist_ok=True)
            if payload.get("segments"):
                page.write_text(sequence_html(
                    payload["id"], payload["label"], collection["manifest_path"], collection["catalog_path"],
                ), encoding="utf-8")
                segments_dir = page.parent / "segments"
                segment_ids = set()
                for segment in payload["segments"]:
                    segment_id = segment.get("id")
                    if not isinstance(segment_id, str) or not SAFE_ID.fullmatch(segment_id):
                        raise ValueError(f"{path}: segment id is not URL-safe")
                    if segment_id in segment_ids:
                        raise ValueError(f"{path}: duplicate segment {segment_id!r}")
                    segment_ids.add(segment_id)
                    segment_page = segments_dir / segment_id / "index.html"
                    segment_page.parent.mkdir(parents=True, exist_ok=True)
                    segment_page.write_text(sample_html(
                        payload["id"], f"{payload['label']} · {segment['label']}",
                        collection["manifest_path"], collection["catalog_path"], segment_id,
                    ), encoding="utf-8")
                for segment_page in segments_dir.glob("*/index.html"):
                    if segment_page.parent.name not in segment_ids:
                        shutil.rmtree(segment_page.parent)
            else:
                page.write_text(sample_html(
                    payload["id"], payload["label"], collection["manifest_path"], collection["catalog_path"],
                ), encoding="utf-8")
    if not examples:
        raise ValueError("no example configs found")
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
