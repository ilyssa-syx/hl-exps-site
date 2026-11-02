# HL Experiment Viewer

Static, sequence-level viewer for HOI reconstruction outputs. The catalog contains
all 20 test sequences from `dexycb_hl_v3_100_20_20`. Each sample compares the
dataset's scaled `input/final` reconstruction, displayed simply as `input`, with
the CD-IoU fourth-run checkpoint at epoch 5 / iteration 4. Each sample has one
shareable page containing:

- calibrated 2D reconstruction overlays;
- a free-camera 3D reconstruction view;
- independently toggleable `input` and `cd-iou-fourth-run-20261029` overlays
  in 2D and 3D;
- one shared sequence timeline.

All samples use their real input RGB, MANO hand mesh, object mesh, and per-frame
camera-space transforms.

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

`baselines[].views.overlay2d.rgb` is required for real samples. It points to either a
published input RGB video or, in a future schema revision, an RGB image
sequence. Camera-space overlay geometry is rendered above that RGB layer.
