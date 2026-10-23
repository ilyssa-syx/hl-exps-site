export class Preview2D {
  constructor(canvas, video = null, reconstruction = null) {
    this.canvas = canvas;
    this.video = video;
    this.ctx = canvas.getContext("2d");
    this.progress = 0;
    this.data = null;
    reconstruction?.then((data) => {
      this.data = data;
      this.draw();
    }).catch((error) => console.error(error));
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.resizeObserver.observe(canvas);
  }

  setProgress(progress) {
    this.progress = progress;
    this.draw();
  }

  draw() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio, 2);
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    const ctx = this.ctx;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    const videoAspect = this.video?.videoWidth && this.video?.videoHeight
      ? this.video.videoWidth / this.video.videoHeight
      : 4 / 3;
    const stageAspect = w / h;
    const contentWidth = stageAspect > videoAspect ? h * videoAspect : w;
    const contentHeight = stageAspect > videoAspect ? h : w / videoAspect;
    const left = (w - contentWidth) / 2;
    const top = (h - contentHeight) / 2;

    if (!this.data) return;
    const { metadata } = this.data;
    const frame = Math.min(metadata.frameCount - 1, Math.round(this.progress * (metadata.frameCount - 1)));
    const intrinsics = metadata.intrinsics[Math.min(frame, metadata.intrinsics.length - 1)];
    const viewport = { left, top, width: contentWidth, height: contentHeight };
    if (metadata.object.valid[frame]) this.drawObject(frame, intrinsics, viewport);
    if (metadata.hand.valid[frame]) this.drawHand(frame, intrinsics, viewport);
  }

  drawHand(frame, intrinsics, viewport) {
    const { metadata, handVertices, handFaces } = this.data;
    const offset = frame * metadata.hand.vertexCount * 3;
    this.drawMesh(
      metadata.hand.vertexCount,
      handFaces,
      (index) => handVertices.subarray(offset + index * 3, offset + index * 3 + 3),
      intrinsics,
      viewport,
      "#62e0c5",
    );
  }

  drawObject(frame, intrinsics, viewport) {
    const { metadata, objectVertices, objectFaces, objectPoses } = this.data;
    const matrix = objectPoses.subarray(frame * 16, frame * 16 + 16);
    this.drawMesh(
      metadata.object.vertexCount,
      objectFaces,
      (index) => {
        const offset = index * 3;
        const x = objectVertices[offset], y = objectVertices[offset + 1], z = objectVertices[offset + 2];
        return [
          matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3],
          matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7],
          matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11],
        ];
      },
      intrinsics,
      viewport,
      "#ff9d66",
    );
  }

  drawMesh(vertexCount, faces, vertexAt, intrinsics, viewport, color) {
    const [fx, , cx, , fy, cy] = [intrinsics[0][0], 0, intrinsics[0][2], 0, intrinsics[1][1], intrinsics[1][2]];
    const points = new Float32Array(vertexCount * 2);
    for (let index = 0; index < vertexCount; index += 1) {
      const [x, y, z] = vertexAt(index);
      points[index * 2] = viewport.left + ((fx * x / z + cx) / this.data.metadata.imageWidth) * viewport.width;
      points[index * 2 + 1] = viewport.top + ((fy * y / z + cy) / this.data.metadata.imageHeight) * viewport.height;
    }
    const ctx = this.ctx;
    ctx.beginPath();
    for (let index = 0; index < faces.length; index += 3) {
      const a = faces[index] * 2, b = faces[index + 1] * 2, c = faces[index + 2] * 2;
      ctx.moveTo(points[a], points[a + 1]);
      ctx.lineTo(points[b], points[b + 1]);
      ctx.lineTo(points[c], points[c + 1]);
      ctx.closePath();
    }
    ctx.globalAlpha = 0.34;
    ctx.fillStyle = color;
    ctx.fill();
    ctx.globalAlpha = 0.42;
    ctx.strokeStyle = color;
    ctx.lineWidth = 0.45;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}
