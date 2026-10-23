# HL Experiment Viewer

Static, sequence-level viewer for HOI reconstruction outputs and their SPIDER
retargeting results. Each example has one shareable page containing:

- calibrated 2D reconstruction overlays;
- a free-camera 3D reconstruction view;
- SPIDER kinematic and MJWP/physics views with rollout metrics;
- one shared sequence timeline.

The checked-in DexYCB sample uses its real input RGB, Dyn-HaMR/MANO hand mesh,
FoundationPose++ object mesh, and per-frame camera-space transforms. Its Sharpa
IK completed, while MJWP failed the initial-state sanity check; the page reports
that failure instead of substituting a synthetic robot visualization.

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
The SPIDER converter will similarly map `trajectory_kinematic.npz`,
`trajectory_mjwp.npz`, metrics JSON, and optional IK/MJWP MP4 files into the
example schema.
The repository includes one small RGB clip only so the checked-in sample page
exercises the real video-backed overlay path before object-storage publishing
is configured.

`views.overlay2d.rgb` is required for real samples. It points to either a
published input RGB video or, in a future schema revision, an RGB image
sequence. Camera-space overlay geometry is rendered above that RGB layer.
