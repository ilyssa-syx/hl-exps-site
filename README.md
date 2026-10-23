# HL Experiment Viewer

Static, sequence-level viewer for HOI reconstruction outputs and their SPIDER
retargeting results. Each example has one shareable page containing:

- calibrated 2D reconstruction overlays;
- a free-camera 3D reconstruction view;
- SPIDER kinematic and MJWP/physics views with rollout metrics;
- one shared sequence timeline.

The checked-in `schema-preview` example is deliberately procedural and is
labeled as such. It exercises the page structure without pretending to be an
experiment result.

## Development

```bash
npm install
npm run dev
```

Production build:

```bash
npm run build
```

The site is deployed from `main` by `.github/workflows/pages.yml`.

## Add an example

Add `configs/examples/<example-id>.json`, then run `npm run export`. The config
is the editable source of truth. `public/data/manifest.json` is regenerated and
must not be edited manually.

Example pages use a GitHub-Pages-safe query URL:

```text
https://ilyssa-syx.github.io/hl-exps-site/?example=<example-id>
```

Generated videos and geometry bundles belong in object storage, not Git. The
next converter pass will map the existing reconstruction outputs and SPIDER
artifacts (`trajectory_kinematic.npz`, `trajectory_mjwp.npz`, metrics JSON,
and optional IK/MJWP MP4 files) into the example schema.
