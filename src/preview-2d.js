export class Preview2D {
  constructor(canvas, video, layers) {
    this.canvas = canvas;
    this.video = video;
    this.layers = new Map(layers.map((layer) => [layer.id, { ...layer, data: null, loading: null }]));
    this.visible = new Set(layers.map((layer) => layer.id));
    this.ctx = canvas.getContext("2d");
    this.progress = 0;
    this.projectionBuffers = new Map();
    this.setVisible(this.visible);
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.resizeObserver.observe(canvas);
  }

  ensureLayer(layer) {
    if (!layer.loading) {
      layer.loading = layer.load().then((data) => { layer.data = data; this.draw(); }).catch((error) => console.error(error));
    }
  }

  setVisible(ids) {
    this.visible = new Set(ids);
    for (const id of this.visible) {
      const layer = this.layers.get(id);
      if (layer) this.ensureLayer(layer);
    }
    this.draw();
  }

  setProgress(progress) { this.progress = progress; this.draw(); }

  draw() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = Math.min(devicePixelRatio, 1.5);
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (this.canvas.width !== width || this.canvas.height !== height) { this.canvas.width = width; this.canvas.height = height; }
    const ctx = this.ctx;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    const videoAspect = this.video?.videoWidth && this.video?.videoHeight ? this.video.videoWidth / this.video.videoHeight : 4 / 3;
    const stageAspect = rect.width / rect.height;
    const contentWidth = stageAspect > videoAspect ? rect.height * videoAspect : rect.width;
    const contentHeight = stageAspect > videoAspect ? rect.height : rect.width / videoAspect;
    const viewport = { left: (rect.width - contentWidth) / 2, top: (rect.height - contentHeight) / 2, width: contentWidth, height: contentHeight };

    for (const id of this.visible) {
      const layer = this.layers.get(id);
      if (!layer?.data) continue;
      const { metadata } = layer.data;
      const frame = Math.min(metadata.frameCount - 1, Math.round(this.progress * (metadata.frameCount - 1)));
      const intrinsics = metadata.intrinsics[Math.min(frame, metadata.intrinsics.length - 1)];
      if (metadata.object.valid[frame]) this.drawObject(layer, frame, intrinsics, viewport);
      if (metadata.hand.valid[frame]) this.drawHand(layer, frame, intrinsics, viewport);
    }
  }

  drawHand(layer, frame, intrinsics, viewport) {
    const { metadata, handVertices, handFaces } = layer.data;
    const offset = frame * metadata.hand.vertexCount * 3;
    this.drawMesh(layer.id, metadata, metadata.hand.vertexCount, handFaces, (index) => handVertices.subarray(offset + index * 3, offset + index * 3 + 3), intrinsics, viewport, layer.color, "hand");
  }

  drawObject(layer, frame, intrinsics, viewport) {
    const { metadata, objectVertices, objectFaces, objectPoses } = layer.data;
    const matrix = objectPoses.subarray(frame * 16, frame * 16 + 16);
    this.drawMesh(layer.id, metadata, metadata.object.vertexCount, objectFaces, (index) => {
      const offset = index * 3;
      const x = objectVertices[offset], y = objectVertices[offset + 1], z = objectVertices[offset + 2];
      return [matrix[0] * x + matrix[1] * y + matrix[2] * z + matrix[3], matrix[4] * x + matrix[5] * y + matrix[6] * z + matrix[7], matrix[8] * x + matrix[9] * y + matrix[10] * z + matrix[11]];
    }, intrinsics, viewport, layer.color, "object");
  }

  drawMesh(layerId, metadata, vertexCount, faces, vertexAt, intrinsics, viewport, color, kind) {
    const [fx, cx, fy, cy] = [intrinsics[0][0], intrinsics[0][2], intrinsics[1][1], intrinsics[1][2]];
    const key = `${layerId}:${kind}`;
    let points = this.projectionBuffers.get(key);
    if (!points || points.length !== vertexCount * 2) { points = new Float32Array(vertexCount * 2); this.projectionBuffers.set(key, points); }
    for (let index = 0; index < vertexCount; index += 1) {
      const [x, y, z] = vertexAt(index);
      points[index * 2] = viewport.left + ((fx * x / z + cx) / metadata.imageWidth) * viewport.width;
      points[index * 2 + 1] = viewport.top + ((fy * y / z + cy) / metadata.imageHeight) * viewport.height;
    }
    const faceStep = kind === "object" ? Math.max(1, Math.ceil((faces.length / 3) / 4500)) : 1;
    const ctx = this.ctx;
    ctx.beginPath();
    for (let index = 0; index < faces.length; index += 3 * faceStep) {
      const a = faces[index] * 2, b = faces[index + 1] * 2, c = faces[index + 2] * 2;
      ctx.moveTo(points[a], points[a + 1]); ctx.lineTo(points[b], points[b + 1]); ctx.lineTo(points[c], points[c + 1]); ctx.closePath();
    }
    ctx.globalAlpha = kind === "hand" ? 0.25 : 0.16;
    ctx.fillStyle = color;
    ctx.fill();
    ctx.globalAlpha = kind === "hand" ? 0.78 : 0.55;
    ctx.strokeStyle = color;
    ctx.lineWidth = kind === "hand" ? 0.7 : 0.45;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}
