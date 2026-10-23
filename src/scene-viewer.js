import * as THREE from "three";

export class SceneViewer {
  constructor(canvas, reconstruction = null) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.01, 50);
    this.camera.position.set(2.8, 2.1, 4.3);
    this.camera.lookAt(0, 0.25, 0);

    this.scene.add(new THREE.HemisphereLight(0xbad7ff, 0x162032, 2.1));
    const key = new THREE.DirectionalLight(0xffffff, 3.4);
    key.position.set(3, 5, 4);
    this.scene.add(key);

    this.grid = new THREE.GridHelper(7, 14, 0x33445d, 0x202c3c);
    this.grid.position.y = -0.72;
    this.scene.add(this.grid);
    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.grid.visible = false;
    reconstruction?.then((data) => this.buildReconstruction(data)).catch((error) => console.error(error));

    this.resizeObserver = new ResizeObserver(() => this.render());
    this.resizeObserver.observe(canvas);
    this.setProgress(0);
  }

  material(color, metalness = 0.1) {
    return new THREE.MeshStandardMaterial({ color, roughness: 0.42, metalness });
  }

  buildReconstruction(data) {
    this.actual = data;
    const handGeometry = new THREE.BufferGeometry();
    handGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(data.metadata.hand.vertexCount * 3), 3));
    handGeometry.setIndex(new THREE.BufferAttribute(data.handFaces, 1));
    this.hand = new THREE.Mesh(
      handGeometry,
      new THREE.MeshStandardMaterial({ color: 0x62e0c5, roughness: 0.48, metalness: 0.08, side: THREE.DoubleSide }),
    );
    this.root.add(this.hand);

    const objectPositions = new Float32Array(data.objectVertices);
    const objectGeometry = new THREE.BufferGeometry();
    objectGeometry.setAttribute("position", new THREE.BufferAttribute(objectPositions, 3));
    objectGeometry.setIndex(new THREE.BufferAttribute(data.objectFaces, 1));
    objectGeometry.computeVertexNormals();
    this.object = new THREE.Mesh(objectGeometry, this.material(0xff9d66, 0.12));
    this.object.matrixAutoUpdate = false;
    this.root.add(this.object);
    this.setProgress(this.progress ?? 0);
    this.fitCamera();
  }

  setProgress(progress) {
    this.progress = progress;
    if (!this.actual) return;
    const { metadata, handVertices, objectPoses } = this.actual;
    const frame = Math.min(metadata.frameCount - 1, Math.round(progress * (metadata.frameCount - 1)));
    const positions = this.hand.geometry.attributes.position.array;
    const offset = frame * metadata.hand.vertexCount * 3;
    for (let index = 0; index < positions.length; index += 3) {
      positions[index] = handVertices[offset + index];
      positions[index + 1] = -handVertices[offset + index + 1];
      positions[index + 2] = -handVertices[offset + index + 2];
    }
    this.hand.visible = metadata.hand.valid[frame];
    this.hand.geometry.attributes.position.needsUpdate = true;
    this.hand.geometry.computeVertexNormals();

    const pose = objectPoses.subarray(frame * 16, frame * 16 + 16);
    const cameraFromObject = new THREE.Matrix4().set(...pose);
    const webglFromCamera = new THREE.Matrix4().set(
      1, 0, 0, 0,
      0, -1, 0, 0,
      0, 0, -1, 0,
      0, 0, 0, 1,
    );
    this.object.matrix.copy(webglFromCamera.multiply(cameraFromObject));
    this.object.visible = metadata.object.valid[frame];
    this.render();
  }

  fitCamera() {
    this.root.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(this.root);
    if (bounds.isEmpty()) return;
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const radius = Math.max(size.x, size.y, size.z, 0.1);
    this.camera.position.copy(center).add(new THREE.Vector3(radius * 1.5, radius * 1.1, radius * 2.4));
    this.camera.near = Math.max(radius / 100, 0.001);
    this.camera.far = radius * 20;
    this.camera.lookAt(center);
    this.camera.updateProjectionMatrix();
    this.render();
  }

  render() {
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    this.renderer.setSize(rect.width, rect.height, false);
    this.camera.aspect = rect.width / rect.height;
    this.camera.updateProjectionMatrix();
    this.renderer.render(this.scene, this.camera);
  }
}
