const VERTEX_SHADER = `
attribute vec3 aPosition;
uniform mat4 uCameraFromModel;
uniform vec4 uIntrinsics;
uniform vec2 uImageSize;

void main() {
  vec4 point = uCameraFromModel * vec4(aPosition, 1.0);
  if (point.z <= 0.0001) {
    gl_Position = vec4(2.0, 2.0, 1.0, 1.0);
    return;
  }
  vec2 pixel = vec2(
    uIntrinsics.x * point.x / point.z + uIntrinsics.z,
    uIntrinsics.y * point.y / point.z + uIntrinsics.w
  );
  vec2 projected = vec2(pixel.x / uImageSize.x * 2.0 - 1.0, 1.0 - pixel.y / uImageSize.y * 2.0);
  float depth = clamp(point.z / 10.0, 0.0, 1.0) * 2.0 - 1.0;
  gl_Position = vec4(projected, depth, 1.0);
}`;

const FRAGMENT_SHADER = `
precision mediump float;
uniform vec4 uColor;

void main() {
  gl_FragColor = uColor;
}`;

const IDENTITY = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);

function compileShader(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`Could not compile 2D overlay shader: ${message}`);
  }
  return shader;
}

function createProgram(gl) {
  const vertex = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
  const fragment = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
  const program = gl.createProgram();
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const message = gl.getProgramInfoLog(program);
    gl.deleteProgram(program);
    throw new Error(`Could not link 2D overlay shader: ${message}`);
  }
  return program;
}

function rgb(color) {
  const value = Number.parseInt(color.replace("#", ""), 16);
  return [(value >> 16 & 255) / 255, (value >> 8 & 255) / 255, (value & 255) / 255];
}

function edgeIndices(faces) {
  const edges = new Uint16Array(faces.length * 2);
  for (let source = 0, target = 0; source < faces.length; source += 3, target += 6) {
    const a = faces[source], b = faces[source + 1], c = faces[source + 2];
    edges[target] = a; edges[target + 1] = b;
    edges[target + 2] = b; edges[target + 3] = c;
    edges[target + 4] = c; edges[target + 5] = a;
  }
  return edges;
}

export class Preview2D {
  constructor(canvas, video, layers) {
    this.canvas = canvas;
    this.video = video;
    this.layers = new Map(layers.map((layer) => [layer.id, {
      ...layer, data: null, loading: null, hand: null, object: null,
      colorRgb: rgb(layer.color), pose: new Float32Array(16),
    }]));
    this.visible = new Set(layers.map((layer) => layer.id));
    this.progress = 0;
    this.gl = canvas.getContext("webgl", { alpha: true, antialias: true, premultipliedAlpha: true });
    if (!this.gl) throw new Error("WebGL is required for the 2D overlay viewer");
    this.program = createProgram(this.gl);
    this.locations = {
      position: this.gl.getAttribLocation(this.program, "aPosition"),
      model: this.gl.getUniformLocation(this.program, "uCameraFromModel"),
      intrinsics: this.gl.getUniformLocation(this.program, "uIntrinsics"),
      imageSize: this.gl.getUniformLocation(this.program, "uImageSize"),
      color: this.gl.getUniformLocation(this.program, "uColor"),
    };
    this.gl.enable(this.gl.BLEND);
    this.gl.blendFuncSeparate(this.gl.SRC_ALPHA, this.gl.ONE_MINUS_SRC_ALPHA, this.gl.ONE, this.gl.ONE_MINUS_SRC_ALPHA);
    this.gl.enable(this.gl.DEPTH_TEST);
    this.gl.depthFunc(this.gl.LESS);
    this.gl.clearColor(0, 0, 0, 0);
    this.gl.clearDepth(1);
    this.setVisible(this.visible);
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.resizeObserver.observe(canvas);
  }

  createMesh(vertices, faces, dynamic = false) {
    const gl = this.gl;
    const vertexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, dynamic ? gl.DYNAMIC_DRAW : gl.STATIC_DRAW);
    const triangleBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, triangleBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, faces, gl.STATIC_DRAW);
    const edges = edgeIndices(faces);
    const edgeBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, edgeBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, edges, gl.STATIC_DRAW);
    return { vertexBuffer, triangleBuffer, triangleCount: faces.length, edgeBuffer, edgeCount: edges.length, frame: -1 };
  }

  buildLayer(layer, data) {
    if (this.disposed) return;
    layer.data = data;
    const handSize = data.metadata.hand.vertexCount * 3;
    layer.hand = this.createMesh(data.handVertices.subarray(0, handSize), data.handFaces, true);
    layer.object = this.createMesh(data.objectVertices, data.objectFaces);
    this.draw();
  }

  ensureLayer(layer) {
    if (!layer.loading) {
      layer.loading = layer.load().then((data) => this.buildLayer(layer, data)).catch((error) => console.error(error));
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

  setObjectPose(target, source) {
    target[0] = source[0]; target[1] = source[4]; target[2] = source[8]; target[3] = 0;
    target[4] = source[1]; target[5] = source[5]; target[6] = source[9]; target[7] = 0;
    target[8] = source[2]; target[9] = source[6]; target[10] = source[10]; target[11] = 0;
    target[12] = source[3]; target[13] = source[7]; target[14] = source[11]; target[15] = 1;
  }

  drawMesh(mesh, model, color, fillAlpha, lineAlpha) {
    const gl = this.gl;
    gl.clear(gl.DEPTH_BUFFER_BIT);
    gl.bindBuffer(gl.ARRAY_BUFFER, mesh.vertexBuffer);
    gl.vertexAttribPointer(this.locations.position, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(this.locations.position);
    gl.uniformMatrix4fv(this.locations.model, false, model);
    gl.uniform4f(this.locations.color, color[0], color[1], color[2], fillAlpha);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.triangleBuffer);
    gl.drawElements(gl.TRIANGLES, mesh.triangleCount, gl.UNSIGNED_SHORT, 0);
    gl.disable(gl.DEPTH_TEST);
    gl.uniform4f(this.locations.color, color[0], color[1], color[2], lineAlpha);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.edgeBuffer);
    gl.drawElements(gl.LINES, mesh.edgeCount, gl.UNSIGNED_SHORT, 0);
    gl.enable(gl.DEPTH_TEST);
  }

  draw() {
    if (this.disposed || this.gl.isContextLost()) return;
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dpr = Math.min(devicePixelRatio, 1.5);
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (this.canvas.width !== width || this.canvas.height !== height) { this.canvas.width = width; this.canvas.height = height; }
    const gl = this.gl;
    gl.viewport(0, 0, width, height);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const videoAspect = this.video?.videoWidth && this.video?.videoHeight ? this.video.videoWidth / this.video.videoHeight : 4 / 3;
    const stageAspect = rect.width / rect.height;
    const contentWidth = stageAspect > videoAspect ? rect.height * videoAspect : rect.width;
    const contentHeight = stageAspect > videoAspect ? rect.height : rect.width / videoAspect;
    const left = (rect.width - contentWidth) / 2;
    const top = (rect.height - contentHeight) / 2;
    gl.viewport(Math.round(left * dpr), Math.round((rect.height - top - contentHeight) * dpr), Math.round(contentWidth * dpr), Math.round(contentHeight * dpr));
    gl.useProgram(this.program);

    for (const id of this.visible) {
      const layer = this.layers.get(id);
      if (!layer?.data || !layer.hand || !layer.object) continue;
      const { metadata, handVertices, objectPoses } = layer.data;
      const frame = Math.min(metadata.frameCount - 1, Math.round(this.progress * (metadata.frameCount - 1)));
      const intrinsics = metadata.intrinsics[Math.min(frame, metadata.intrinsics.length - 1)];
      gl.uniform4f(this.locations.intrinsics, intrinsics[0][0], intrinsics[1][1], intrinsics[0][2], intrinsics[1][2]);
      gl.uniform2f(this.locations.imageSize, metadata.imageWidth, metadata.imageHeight);

      if (metadata.object.valid[frame]) {
        this.setObjectPose(layer.pose, objectPoses.subarray(frame * 16, frame * 16 + 16));
        this.drawMesh(layer.object, layer.pose, layer.colorRgb, 0.16, 0.55);
      }
      if (metadata.hand.valid[frame]) {
        if (layer.hand.frame !== frame) {
          const offset = frame * metadata.hand.vertexCount * 3;
          const vertices = handVertices.subarray(offset, offset + metadata.hand.vertexCount * 3);
          gl.bindBuffer(gl.ARRAY_BUFFER, layer.hand.vertexBuffer);
          gl.bufferSubData(gl.ARRAY_BUFFER, 0, vertices);
          layer.hand.frame = frame;
        }
        this.drawMesh(layer.hand, IDENTITY, layer.colorRgb, 0.25, 0.78);
      }
    }
  }

  disposeMesh(mesh) {
    if (!mesh) return;
    this.gl.deleteBuffer(mesh.vertexBuffer);
    this.gl.deleteBuffer(mesh.triangleBuffer);
    this.gl.deleteBuffer(mesh.edgeBuffer);
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.resizeObserver.disconnect();
    for (const layer of this.layers.values()) {
      this.disposeMesh(layer.hand);
      this.disposeMesh(layer.object);
    }
    this.gl.deleteProgram(this.program);
  }
}
