# HL Experiment Viewer

Static, sequence-level viewer for HOI reconstruction outputs. The catalog contains
all 20 test sequences from `dexycb_hl_v3_100_20_20`, a balanced 20-sequence
OakInk SP0 test sample, and all 13 sequences from `HO3D_v3-TEST`. Each sample compares the
dataset's scaled `input/final` reconstruction, displayed simply as `input`, with
Exp 4 and Exp 7. DexYCB additionally includes the latest accepted Exp 8
checkpoint (`run-20261106`, epoch 11 / iteration 1). The 20 DexYCB test pages
also include **5 examples overfit**, optimized on five DexYCB train sequences
and evaluated on the full held-out test split at query 154, plus **exp11**
(`linear-batch-3`, 30 completed iterations; accepted epoch 0 / iteration 28), and
**exp13** (`linear-bs3 batch-v1`, first-30 validation incumbent at epoch 0 /
iteration 24), and **5 examples overfitting reconstruction** (stitched query
154). Each sample has one shareable page
containing:

- calibrated 2D reconstruction overlays;
- a free-camera 3D reconstruction view;
- per-sequence evaluation-v12 metric tables for every baseline;
- independently toggleable experiment overlays in 2D and 3D;
- one shared sequence timeline.

All samples use their real input RGB, MANO hand mesh, object mesh, and per-frame
camera-space transforms.

The 20 OakInk pages compare their shared `input` reconstruction with **exp8**,
**5 examples overfit**, **exp11**, and **exp13**, using the same sequence timeline
and the OakInk evaluator's per-sequence metrics. The 11 sequences with textured
ground-truth meshes additionally show **5 examples overfitting reconstruction**
and are grouped as **GT-texture 11 test** in the catalog.

The catalog also has a dedicated **5 examples train overfit** section for the
five fixed DexYCB training sequences from `run-20261113-five-case-from-zero`,
alongside the textured reconstruction result from the stitched query 154 run.
Those pages compare `input`, refinement query/iteration 150, and the textured
reconstruction result.

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

The main catalog presents DexYCB, OakInk, and `HO3D_v3-TEST` sections with
the same card and per-sample comparison format.

HO3D sequence pages contain full-sequence metrics and links to independently
loadable five-second visualization pages. Segment pages keep the shared 2D/3D
baseline controls while loading only that segment's RGB and reconstruction data.

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
