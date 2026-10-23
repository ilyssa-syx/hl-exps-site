import * as THREE from "three";

const TAU = Math.PI * 2;

export class SceneViewer {
  constructor(canvas, mode = "reconstruction") {
    this.canvas = canvas;
    this.mode = mode;
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

    const grid = new THREE.GridHelper(7, 14, 0x33445d, 0x202c3c);
    grid.position.y = -0.72;
    this.scene.add(grid);
    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.mode === "spider" ? this.buildRobot() : this.buildReconstruction();

    this.resizeObserver = new ResizeObserver(() => this.render());
    this.resizeObserver.observe(canvas);
    this.setProgress(0);
  }

  material(color, metalness = 0.1) {
    return new THREE.MeshStandardMaterial({ color, roughness: 0.42, metalness });
  }

  buildReconstruction() {
    this.object = new THREE.Mesh(
      new THREE.BoxGeometry(0.9, 0.9, 0.9, 2, 2, 2),
      this.material(0xff9d66),
    );
    this.object.position.set(0.45, 0.15, 0);
    this.root.add(this.object);
    this.joints = [];
    const jointGeometry = new THREE.SphereGeometry(0.07, 18, 12);
    const jointMaterial = this.material(0x62e0c5, 0.22);
    for (let finger = 0; finger < 5; finger += 1) {
      for (let joint = 0; joint < 4; joint += 1) {
        const mesh = new THREE.Mesh(jointGeometry, jointMaterial);
        mesh.userData = { finger, joint };
        this.joints.push(mesh);
        this.root.add(mesh);
      }
    }
  }

  buildRobot() {
    this.object = new THREE.Mesh(
      new THREE.CylinderGeometry(0.42, 0.42, 0.76, 24),
      this.material(0xff9d66),
    );
    this.object.position.set(0.5, -0.1, 0);
    this.root.add(this.object);
    this.robotLinks = [];
    const palm = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.18, 0.72), this.material(0xd8deea, 0.7));
    palm.position.set(-0.45, -0.1, 0);
    this.root.add(palm);
    for (let finger = 0; finger < 4; finger += 1) {
      for (let joint = 0; joint < 3; joint += 1) {
        const link = new THREE.Mesh(
          new THREE.CapsuleGeometry(0.075, 0.25, 6, 12),
          this.material(finger === 0 ? 0x62e0c5 : 0xb8c4d8, 0.6),
        );
        link.userData = { finger, joint };
        this.robotLinks.push(link);
        this.root.add(link);
      }
    }
  }

  setProgress(progress) {
    const t = progress * TAU;
    this.object.rotation.set(t * 0.12, t * 0.2, Math.sin(t) * 0.18);
    this.object.position.y = 0.05 + Math.sin(t) * (this.mode === "spider" ? 0.08 : 0.16);
    if (this.mode === "reconstruction") {
      for (const joint of this.joints) {
        const { finger, joint: depth } = joint.userData;
        joint.position.set(
          -0.95 + depth * 0.34,
          -0.45 + finger * 0.2 + Math.sin(t + finger * 0.5 + depth) * 0.05,
          (finger - 2) * 0.14 + depth * 0.04,
        );
      }
    } else {
      for (const link of this.robotLinks) {
        const { finger, joint } = link.userData;
        const angle = 0.25 + Math.sin(t + finger * 0.4) * 0.28;
        link.rotation.z = Math.PI / 2 + angle;
        link.position.set(-0.08 + joint * 0.29, 0.03 + finger * 0.12 + joint * 0.1, (finger - 1.5) * 0.18);
      }
    }
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
