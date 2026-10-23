import "./style.css";
import { Preview2D } from "./preview-2d.js";
import { SceneViewer } from "./scene-viewer.js";

const base = import.meta.env.BASE_URL;
const response = await fetch(`${base}data/manifest.json`);
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();
const params = new URLSearchParams(location.search);
const selectedId = params.get("example");
const example = manifest.examples.find((item) => item.id === selectedId) ?? manifest.examples[0];

const formatMetric = (value, suffix = "") => value == null ? "—" : `${Number(value).toFixed(3)}${suffix}`;
const exampleLinks = manifest.examples.map((item) => `
  <a class="example-link ${item.id === example.id ? "active" : ""}" href="?example=${encodeURIComponent(item.id)}">
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
        <div class="stage single"><canvas id="overlay-canvas"></canvas></div>
        <div class="layer-row">
          ${example.views.overlay2d.layers.map((layer) => `<span><i style="--layer:${layer.color}"></i>${layer.label}</span>`).join("")}
        </div>
      </div>

      <div class="panel" data-panel="scene" hidden>
        <div class="stage single"><canvas id="scene-canvas"></canvas><span class="stage-tag">FREE CAMERA · PREVIEW</span></div>
        <div class="layer-row">
          ${example.views.scene3d.layers.map((layer) => `<span><i style="--layer:${layer.color}"></i>${layer.label}</span>`).join("")}
        </div>
      </div>

      <div class="panel" data-panel="spider" hidden>
        <div class="spider-head">
          <div><span class="status ${example.views.spider.status}">${example.views.spider.status}</span><strong>${example.views.spider.robot}</strong></div>
          <div class="metrics">
            <span><small>ADD-AUC10</small>${formatMetric(example.views.spider.metrics.addAuc10)}</span>
            <span><small>position error</small>${formatMetric(example.views.spider.metrics.positionErrorMeters, " m")}</span>
            <span><small>rotation error</small>${formatMetric(example.views.spider.metrics.rotationErrorRadians, " rad")}</span>
          </div>
        </div>
        <div class="stage split">
          <div><canvas id="spider-ik-canvas"></canvas><span class="stage-tag">KINEMATIC / IK</span></div>
          <div><canvas id="spider-physics-canvas"></canvas><span class="stage-tag">MJWP / PHYSICS</span></div>
        </div>
        <p class="note">The SPIDER panels use normalized sequence time. Published examples can replace either preview with exported MP4 while keeping this shared timeline.</p>
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
  new Preview2D(document.querySelector("#overlay-canvas")),
  new SceneViewer(document.querySelector("#scene-canvas")),
  new SceneViewer(document.querySelector("#spider-ik-canvas"), "spider"),
  new SceneViewer(document.querySelector("#spider-physics-canvas"), "spider"),
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
const frameLabel = document.querySelector("#frame");
const timeLabel = document.querySelector("#time");
const play = document.querySelector("#play");
let playing = false;
let lastTick = 0;

function setFrame(frame) {
  const safeFrame = Math.max(0, Math.min(example.frameCount - 1, Math.round(frame)));
  timeline.value = safeFrame;
  const progress = safeFrame / Math.max(1, example.frameCount - 1);
  viewers.forEach((viewer, index) => viewer.setProgress(Math.min(1, progress + (index === 3 ? 0.008 : 0))));
  frameLabel.textContent = `${String(safeFrame).padStart(3, "0")} / ${String(example.frameCount - 1).padStart(3, "0")}`;
  timeLabel.textContent = `${(safeFrame / example.fps).toFixed(2)} s`;
}

timeline.addEventListener("input", () => setFrame(Number(timeline.value)));
play.addEventListener("click", () => {
  playing = !playing;
  play.textContent = playing ? "❚❚" : "▶";
  lastTick = performance.now();
});

function animate(now) {
  if (playing) {
    const elapsed = (now - lastTick) / 1000;
    if (elapsed >= 1 / example.fps) {
      const next = (Number(timeline.value) + Math.max(1, Math.floor(elapsed * example.fps))) % example.frameCount;
      setFrame(next);
      lastTick = now;
    }
  }
  requestAnimationFrame(animate);
}

setFrame(0);
requestAnimationFrame(animate);
