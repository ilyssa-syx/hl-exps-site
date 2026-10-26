import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export class SceneViewer {
  constructor(canvas, layers) {
    this.canvas = canvas;
    this.layers = new Map(layers.map((layer) => [layer.id, { ...layer, data: null, loading: null, group: null }]));
    this.visible = new Set(layers.map((layer) => layer.id));
    this.progress = 0;
    this.currentFrame = -1;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.01, 50);
    this.camera.position.set(2.8, 2.1, 4.3);
    this.camera.lookAt(0, 0.25, 0);
    this.defaultViewDirection = this.camera.position.clone().sub(new THREE.Vector3(0, 0.25, 0)).normalize();
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.target.set(0, 0.25, 0);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.screenSpacePanning = true;
    this.controls.zoomToCursor = true;
    this.controls.update();
    this.controls.addEventListener("start", () => {
      this.interacting = true;
      this.settleFrames = 0;
      this.scheduleControlUpdate();
    });
    this.controls.addEventListener("change", () => this.render());
    this.controls.addEventListener("end", () => {
      this.interacting = false;
      this.settleFrames = 36;
      this.scheduleControlUpdate();
    });
    this.scene.add(new THREE.HemisphereLight(0xbad7ff, 0x162032, 2.1));
    const key = new THREE.DirectionalLight(0xffffff, 3.4);
    key.position.set(3, 5, 4);
    this.scene.add(key);
    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.resizeObserver = new ResizeObserver(() => this.render());
    this.resizeObserver.observe(canvas);
  }

  scheduleControlUpdate() {
    if (this.controlFrame !== undefined) return;
    this.controlFrame = requestAnimationFrame(() => {
      this.controlFrame = undefined;
      this.controls.update();
      if (this.interacting || this.settleFrames-- > 0) this.scheduleControlUpdate();
    });
  }

  material(color, opacity) {
    return new THREE.MeshStandardMaterial({ color, roughness: 0.42, metalness: 0.08, side: THREE.DoubleSide, transparent: true, opacity, depthWrite: opacity > 0.7 });
  }

  ensureLayer(layer) {
    if (!layer.loading) layer.loading = layer.load().then((data) => this.buildLayer(layer, data)).catch((error) => console.error(error));
  }

  buildLayer(layer, data) {
    layer.data = data;
    layer.group = new THREE.Group();
    const handGeometry = new THREE.BufferGeometry();
    handGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(data.metadata.hand.vertexCount * 3), 3));
    handGeometry.setIndex(new THREE.BufferAttribute(data.handFaces, 1));
    layer.hand = new THREE.Mesh(handGeometry, this.material(layer.color, 0.76));
    layer.group.add(layer.hand);
    const objectGeometry = new THREE.BufferGeometry();
    objectGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(data.objectVertices), 3));
    objectGeometry.setIndex(new THREE.BufferAttribute(data.objectFaces, 1));
    objectGeometry.computeVertexNormals();
    layer.object = new THREE.Mesh(objectGeometry, this.material(layer.color, 0.48));
    layer.object.matrixAutoUpdate = false;
    layer.group.add(layer.object);
    layer.group.visible = this.visible.has(layer.id);
    this.root.add(layer.group);
    this.updateLayer(layer, this.frameFor(data.metadata));
    this.fitCamera();
  }

  frameFor(metadata) { return Math.min(metadata.frameCount - 1, Math.round(this.progress * (metadata.frameCount - 1))); }

  updateLayer(layer, frame) {
    const { metadata, handVertices, objectPoses } = layer.data;
    const positions = layer.hand.geometry.attributes.position.array;
    const offset = frame * metadata.hand.vertexCount * 3;
    for (let index = 0; index < positions.length; index += 3) {
      positions[index] = handVertices[offset + index];
      positions[index + 1] = -handVertices[offset + index + 1];
      positions[index + 2] = -handVertices[offset + index + 2];
    }
    layer.hand.visible = metadata.hand.valid[frame];
    layer.hand.geometry.attributes.position.needsUpdate = true;
    layer.hand.geometry.computeVertexNormals();
    const pose = objectPoses.subarray(frame * 16, frame * 16 + 16);
    const cameraFromObject = new THREE.Matrix4().set(...pose);
    const webglFromCamera = new THREE.Matrix4().set(1, 0, 0, 0, 0, -1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1);
    layer.object.matrix.copy(webglFromCamera.multiply(cameraFromObject));
    layer.object.visible = metadata.object.valid[frame];
  }

  setVisible(ids) {
    this.visible = new Set(ids);
    for (const layer of this.layers.values()) {
      if (this.visible.has(layer.id)) this.ensureLayer(layer);
      if (layer.group) layer.group.visible = this.visible.has(layer.id);
    }
    this.fitCamera();
  }

  setProgress(progress) {
    this.progress = progress;
    const representative = [...this.layers.values()].find((layer) => layer.data);
    const frame = representative ? this.frameFor(representative.data.metadata) : -1;
    if (frame === this.currentFrame) return;
    this.currentFrame = frame;
    for (const layer of this.layers.values()) if (layer.data) this.updateLayer(layer, this.frameFor(layer.data.metadata));
    this.render();
  }

  fitCamera() {
    if (!this.root) return;
    this.root.updateMatrixWorld(true);
    const bounds = new THREE.Box3();
    for (const layer of this.layers.values()) {
      if (this.visible.has(layer.id) && layer.group) bounds.expandByObject(layer.group);
    }
    if (bounds.isEmpty()) { this.render(); return; }
    const center = bounds.getCenter(new THREE.Vector3());
    const sphere = bounds.getBoundingSphere(new THREE.Sphere());
    const radius = Math.max(sphere.radius, 0.05);
    const direction = this.camera.position.clone().sub(this.controls.target);
    if (direction.lengthSq() < 1e-8) direction.copy(this.defaultViewDirection);
    direction.normalize();
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width && rect.height) this.camera.aspect = rect.width / rect.height;
    const verticalFov = THREE.MathUtils.degToRad(this.camera.fov);
    const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * Math.max(this.camera.aspect, 0.1));
    const limitingFov = Math.min(verticalFov, horizontalFov);
    const distance = radius / Math.sin(limitingFov / 2) * 1.15;
    this.controls.target.copy(center);
    this.camera.position.copy(center).addScaledVector(direction, distance);
    this.controls.minDistance = Math.max(radius * 0.15, 0.01);
    this.controls.maxDistance = radius * 20;
    this.camera.near = Math.max(distance - radius * 2, radius / 100, 0.001);
    this.camera.far = distance + radius * 20;
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.render();
  }

  resetView() {
    const distance = this.camera.position.distanceTo(this.controls.target);
    this.camera.position.copy(this.controls.target).addScaledVector(this.defaultViewDirection, distance);
    this.camera.up.set(0, 1, 0);
    this.controls.update();
    this.fitCamera();
  }

  render() {
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    this.renderer.setSize(rect.width, rect.height, false);
    this.camera.aspect = rect.width / rect.height;
    this.camera.updateProjectionMatrix();
    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    this.resizeObserver.disconnect();
    if (this.controlFrame !== undefined) cancelAnimationFrame(this.controlFrame);
    this.controls.dispose();
    for (const layer of this.layers.values()) {
      layer.hand?.geometry.dispose(); layer.hand?.material.dispose();
      layer.object?.geometry.dispose(); layer.object?.material.dispose();
    }
    this.renderer.dispose();
  }
}
