#!/usr/bin/env python3
"""Render an existing successful SPIDER MJWP trajectory to an H.264 video."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--camera", default="front")
    parser.add_argument("--fps", type=int, default=15)
    args = parser.parse_args()

    trial = args.trial_dir.resolve()
    model = mujoco.MjModel.from_xml_path(str(trial.parent / "scene.xml"))
    data = mujoco.MjData(model)
    qpos = np.load(trial / "trajectory_mjwp.npz", allow_pickle=False)["qpos"].reshape(-1, model.nq)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        args.ffmpeg, "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", "640x480", "-framerate", str(args.fps), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(args.output),
    ]
    renderer = mujoco.Renderer(model, height=480, width=640)
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        assert process.stdin is not None
        for pose in qpos:
            data.qpos[:] = pose
            mujoco.mj_forward(model, data)
            renderer.update_scene(data, camera=args.camera)
            process.stdin.write(renderer.render().tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("ffmpeg failed while encoding SPIDER video")
    renderer.close()
    print(f"Rendered {len(qpos)} frames to {args.output}")


if __name__ == "__main__":
    main()
