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
    const visibleLayerCount = Math.max(1, [...this.visible].filter((id) => this.layers.get(id)?.data).length);
    const dprLimit = visibleLayerCount >= 4 ? 1 : visibleLayerCount >= 2 ? 1.25 : 1.5;
    const dpr = Math.min(devicePixelRatio, dprLimit);
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
    this.drawMesh(layer.id, metadata, metadata.hand.vertexCount, handFaces, handVertices, offset, null, intrinsics, viewport, layer.color, "hand");
  }

  drawObject(layer, frame, intrinsics, viewport) {
    const { metadata, objectVertices, objectFaces, objectPoses } = layer.data;
    const matrix = objectPoses.subarray(frame * 16, frame * 16 + 16);
    this.drawMesh(layer.id, metadata, metadata.object.vertexCount, objectFaces, objectVertices, 0, matrix, intrinsics, viewport, layer.color, "object");
  }

  drawMesh(layerId, metadata, vertexCount, faces, vertices, vertexOffset, matrix, intrinsics, viewport, color, kind) {
    const [fx, cx, fy, cy] = [intrinsics[0][0], intrinsics[0][2], intrinsics[1][1], intrinsics[1][2]];
    const key = `${layerId}:${kind}`;
    let points = this.projectionBuffers.get(key);
    if (!points || points.length !== vertexCount * 2) { points = new Float32Array(vertexCount * 2); this.projectionBuffers.set(key, points); }
    for (let index = 0; index < vertexCount; index += 1) {
      const offset = vertexOffset + index * 3;
      const sourceX = vertices[offset], sourceY = vertices[offset + 1], sourceZ = vertices[offset + 2];
      const x = matrix ? matrix[0] * sourceX + matrix[1] * sourceY + matrix[2] * sourceZ + matrix[3] : sourceX;
      const y = matrix ? matrix[4] * sourceX + matrix[5] * sourceY + matrix[6] * sourceZ + matrix[7] : sourceY;
      const z = matrix ? matrix[8] * sourceX + matrix[9] * sourceY + matrix[10] * sourceZ + matrix[11] : sourceZ;
      points[index * 2] = viewport.left + ((fx * x / z + cx) / metadata.imageWidth) * viewport.width;
      points[index * 2 + 1] = viewport.top + ((fy * y / z + cy) / metadata.imageHeight) * viewport.height;
    }
    const visibleLayerCount = Math.max(1, this.visible.size);
    const layerBudget = Math.max(900, Math.floor(7000 / visibleLayerCount));
    const faceBudget = kind === "hand"
      ? Math.max(320, Math.floor(layerBudget * 0.3))
      : Math.min(4500, Math.max(580, Math.floor(layerBudget * 0.7)));
    const faceStep = Math.max(1, Math.ceil((faces.length / 3) / faceBudget));
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
