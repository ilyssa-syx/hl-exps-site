import "./style.css";
import { Preview2D } from "./preview-2d.js";
import { SceneViewer } from "./scene-viewer.js";
import { loadReconstruction } from "./reconstruction-data.js";

const base = import.meta.env.BASE_URL;
const response = await fetch(`${base}data/manifest.json`);
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();
const selectedId = document.body.dataset.sampleId;
const example = manifest.examples.find((item) => item.id === selectedId);
if (!example) throw new Error(`Unknown sample page: ${selectedId}`);
const rgb = example.views.overlay2d.rgb;
const rgbUrl = rgb?.url ? `${base}${rgb.url}` : null;
const spider = example.views.spider;
const reconstructionPath = example.views.overlay2d.reconstruction ?? example.views.scene3d.reconstruction;
const reconstruction = reconstructionPath
  ? loadReconstruction(`${base}${reconstructionPath}`)
  : Promise.reject(new Error("No reconstruction asset is configured"));

const formatMetric = (value, suffix = "") => value == null ? "—" : `${Number(value).toFixed(3)}${suffix}`;
const spiderArtifact = (title, artifact) => `
  <div class="spider-artifact">
    <div class="artifact-title"><span>${title}</span><small class="artifact-state ${artifact?.status ?? "missing"}">${artifact?.status ?? "missing"}</small></div>
    ${artifact?.video
      ? `<video class="spider-video" src="${base}${artifact.video}" controls muted playsinline preload="metadata"></video>`
      : `<div class="artifact-empty"><strong>No rendered video</strong><p>${artifact?.detail ?? "This artifact was not exported."}</p></div>`}
  </div>
`;
const exampleLinks = manifest.examples.map((item) => `
  <a class="example-link ${item.id === example.id ? "active" : ""}" href="${base}samples/${encodeURIComponent(item.id)}/">
    <span>${item.label}</span><small>${item.objectName ?? "unknown object"}</small>
  </a>
`).join("");

document.querySelector("#app").innerHTML = `
  <aside class="sidebar">
    <a class="brand" href="${base}">
      <span class="brand-mark">HL</span>
      <span><strong>Experiments</strong><small>reconstruction → retargeting</small></span>
    </a>
    <div class="sidebar-label">Examples · ${manifest.examples.length}</div>
    <nav>${exampleLinks}</nav>
    <a class="repo-link" href="https://github.com/ilyssa-syx/hl-exps-site">GitHub repository ↗</a>
  </aside>
  <main>
    <header class="topbar">
      <div>
        <div class="eyebrow">${example.dataset ?? "dataset"} / ${example.split ?? "split"}</div>
        <h1>${example.label}</h1>
        <p>${example.description ?? "Sequence-level experiment inspection."}</p>
      </div>
      <div class="meta">
        <span><small>object</small>${example.objectName ?? "—"}</span>
        <span><small>frames</small>${example.frameCount}</span>
        <span><small>fps</small>${example.fps}</span>
      </div>
    </header>

    <section class="workspace">
      <div class="tabs" role="tablist" aria-label="Visualization type">
        <button class="tab active" data-tab="overlay" role="tab">2D overlay</button>
        <button class="tab" data-tab="scene" role="tab">3D reconstruction</button>
        <button class="tab" data-tab="spider" role="tab">SPIDER retargeting</button>
      </div>

      <div class="panel active" data-panel="overlay">
        <div class="stage single overlay-stage">
          ${rgbUrl ? `<video id="input-rgb" src="${rgbUrl}" preload="auto" muted playsinline></video>` : `<div class="missing-rgb">Input RGB is not published for this sample.</div>`}
          <canvas id="overlay-canvas"></canvas>
          <span class="stage-tag">INPUT RGB + EXPORTED CAMERA-SPACE MESH</span>
        </div>
        <div class="layer-row">
          ${example.views.overlay2d.layers.map((layer) => `<span><i style="--layer:${layer.color}"></i>${layer.label}</span>`).join("")}
        </div>
      </div>

      <div class="panel" data-panel="scene" hidden>
        <div class="stage single"><canvas id="scene-canvas"></canvas><span class="stage-tag">EXPORTED HAND + OBJECT GEOMETRY</span></div>
        <div class="layer-row">
          ${example.views.scene3d.layers.map((layer) => `<span><i style="--layer:${layer.color}"></i>${layer.label}</span>`).join("")}
        </div>
      </div>

      <div class="panel" data-panel="spider" hidden>
        <div class="spider-head">
          <div><span class="status ${spider.status}">${spider.status}</span><strong>${spider.robot} · ${spider.embodiment}</strong></div>
          <div class="metrics">
            <span><small>ADD-AUC10</small>${formatMetric(spider.metrics.addAuc10)}</span>
            <span><small>position error</small>${formatMetric(spider.metrics.positionErrorMeters, " m")}</span>
            <span><small>rotation error</small>${formatMetric(spider.metrics.rotationErrorRadians, " rad")}</span>
          </div>
        </div>
        <div class="spider-media">
          ${spiderArtifact("Kinematic / IK", spider.ik)}
          ${spiderArtifact("MJWP / physics", spider.physics)}
        </div>
        ${spider.status === "failed" ? `<p class="failure-note">This is an evaluated SPIDER failure, not a missing visualization. Failed physics runs score zero ADD-AUC10.</p>` : ""}
      </div>

      <div class="transport">
        <button id="play" aria-label="Play sequence">▶</button>
        <span id="frame">000 / ${String(example.frameCount - 1).padStart(3, "0")}</span>
        <input id="timeline" type="range" min="0" max="${example.frameCount - 1}" value="0" aria-label="Sequence frame" />
        <span id="time">0.00 s</span>
      </div>
    </section>
  </main>
`;

const viewers = [
  new Preview2D(document.querySelector("#overlay-canvas"), document.querySelector("#input-rgb"), reconstruction),
  new SceneViewer(document.querySelector("#scene-canvas"), reconstruction),
];
const tabs = [...document.querySelectorAll(".tab")];
const panels = [...document.querySelectorAll(".panel")];
tabs.forEach((tab) => tab.addEventListener("click", () => {
  tabs.forEach((item) => item.classList.toggle("active", item === tab));
  panels.forEach((panel) => {
    const active = panel.dataset.panel === tab.dataset.tab;
    panel.hidden = !active;
    panel.classList.toggle("active", active);
  });
  requestAnimationFrame(() => viewers.forEach((viewer) => viewer.render?.()));
}));

const timeline = document.querySelector("#timeline");
const inputRgb = document.querySelector("#input-rgb");
const frameLabel = document.querySelector("#frame");
const timeLabel = document.querySelector("#time");
const play = document.querySelector("#play");
let playing = false;
let lastTick = 0;

function setFrame(frame, seekVideo = true) {
  const safeFrame = Math.max(0, Math.min(example.frameCount - 1, Math.round(frame)));
  timeline.value = safeFrame;
  const progress = safeFrame / Math.max(1, example.frameCount - 1);
  viewers.forEach((viewer) => viewer.setProgress(progress));
  frameLabel.textContent = `${String(safeFrame).padStart(3, "0")} / ${String(example.frameCount - 1).padStart(3, "0")}`;
  timeLabel.textContent = `${(safeFrame / example.fps).toFixed(2)} s`;
  if (seekVideo && inputRgb && Number.isFinite(inputRgb.duration)) {
    const target = Math.min(inputRgb.duration, safeFrame / example.fps);
    if (Math.abs(inputRgb.currentTime - target) > 1 / example.fps) inputRgb.currentTime = target;
  }
}

timeline.addEventListener("input", () => setFrame(Number(timeline.value)));
play.addEventListener("click", () => {
  playing = !playing;
  play.textContent = playing ? "❚❚" : "▶";
  lastTick = performance.now();
  if (inputRgb) {
    if (playing && inputRgb.ended) inputRgb.currentTime = 0;
    if (playing) inputRgb.play().catch(() => {});
    else inputRgb.pause();
  }
});

function animate(now) {
  if (playing) {
    if (inputRgb && !inputRgb.paused) {
      const videoFrame = Math.min(example.frameCount - 1, Math.floor(inputRgb.currentTime * example.fps));
      setFrame(videoFrame, false);
      if (inputRgb.ended || videoFrame >= example.frameCount - 1) {
        playing = false;
        inputRgb.pause();
        play.textContent = "▶";
      }
    } else {
      const elapsed = (now - lastTick) / 1000;
      if (elapsed >= 1 / example.fps) {
        const next = (Number(timeline.value) + Math.max(1, Math.floor(elapsed * example.fps))) % example.frameCount;
        setFrame(next);
        lastTick = now;
      }
    }
  }
  requestAnimationFrame(animate);
}

setFrame(0);
requestAnimationFrame(animate);
