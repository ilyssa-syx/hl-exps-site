const TAU = Math.PI * 2;

export class Preview2D {
  constructor(canvas, video = null) {
    this.canvas = canvas;
    this.video = video;
    this.ctx = canvas.getContext("2d");
    this.progress = 0;
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

    const t = this.progress * TAU;
    const ox = left + contentWidth * (0.58 + Math.sin(t) * 0.045);
    const oy = top + contentHeight * (0.52 + Math.cos(t * 0.7) * 0.035);
    ctx.save();
    ctx.translate(ox, oy);
    ctx.rotate(Math.sin(t) * 0.25);
    ctx.fillStyle = "rgba(255,157,102,.16)";
    ctx.strokeStyle = "#ff9d66";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.roundRect(-55, -42, 110, 84, 14);
    ctx.fill(); ctx.stroke();
    ctx.restore();

    const wrist = [left + contentWidth * 0.37, top + contentHeight * 0.72];
    ctx.strokeStyle = "#62e0c5";
    ctx.fillStyle = "#62e0c5";
    ctx.lineWidth = 2;
    for (let finger = 0; finger < 5; finger += 1) {
      let [x, y] = wrist;
      ctx.beginPath(); ctx.moveTo(x, y);
      for (let joint = 1; joint <= 4; joint += 1) {
        x += 22 + finger * 1.5;
        y -= 20 + finger * 5 + Math.sin(t + finger * 0.6 + joint) * 3;
        ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.fill();
    }
    ctx.beginPath(); ctx.arc(wrist[0], wrist[1], 7, 0, TAU); ctx.fill();

    ctx.fillStyle = "rgba(255,255,255,.56)";
    ctx.font = "500 12px ui-monospace, SFMono-Regular, monospace";
    ctx.fillText("PROCEDURAL OVERLAY PREVIEW · INPUT RGB IS REAL", left + 18, top + 28);
  }
}
