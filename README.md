# HL Experiment Viewer

Static, sequence-level viewer for HOI reconstruction outputs and their SPIDER
retargeting results. The catalog contains 20 DexYCB validation samples and 10
test samples. Each sample has one shareable page containing:

- calibrated 2D reconstruction overlays;
- a free-camera 3D reconstruction view;
- per-sequence input/refined WA-MPJPE and coverage-penalized CD-H metrics;
- independently toggleable input and `refined-20261023` overlays in 2D and 3D;
- a rendered SPIDER MJWP/physics rollout and metrics when evaluation succeeds;
- one shared sequence timeline.

All samples use their real input RGB, MANO hand mesh, object mesh, and per-frame
camera-space transforms. A SPIDER tab is intentionally omitted for a baseline
when that sample's SPIDER evaluation failed.

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

## R2 assets

Production visualization assets use the `hl-exps-site` Cloudflare R2 bucket.
The S3-compatible uploader uses the local `hl-exps-r2` AWS profile with region
`auto`; credentials are never stored in this repository. The browser origin
policy is tracked in `configs/r2-cors.json`.

Export generated assets below `r2_assets/` and publish them incrementally:

```bash
python3 scripts/publish_r2.py --dry-run
python3 scripts/publish_r2.py
```

The uploader never deletes remote objects. Production and development builds
resolve experiment assets below the public base URL recorded in the two tracked
Vite environment files; credentials remain only in the local AWS profile.

## Add an example

Add `configs/examples/<example-id>.json`, then run `npm run export`. The config
is the editable source of truth. `public/data/manifest.json` is regenerated and
must not be edited manually.

Every sample is emitted as its own static HTML page:

```text
https://ilyssa-syx.github.io/hl-exps-site/samples/<sample-id>/
```

Generated videos and geometry bundles belong in object storage, not Git.
`scripts/export_reconstruction.py` converts `hand_results.npz`, the object mesh,
camera intrinsics, and object poses into browser-readable typed-array buffers.
`scripts/export_eval_run.py` regenerates the dated 30-sample release, including
browser geometry and MP4 renders of successful `trajectory_mjwp.npz` rollouts.

`baselines[].views.overlay2d.rgb` is required for real samples. It points to either a
published input RGB video or, in a future schema revision, an RGB image
sequence. Camera-space overlay geometry is rendered above that RGB layer.
