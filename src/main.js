import "./style.css";
import { Preview2D } from "./preview-2d.js";
import { SceneViewer } from "./scene-viewer.js";
import { loadReconstruction } from "./reconstruction-data.js";

const base = import.meta.env.BASE_URL;
const assetBase = import.meta.env.VITE_ASSET_BASE_URL || base;
const versionedAsset = (path) => `${base}${path}?v=${encodeURIComponent(__BUILD_ID__)}`;
const experimentAsset = (path) => `${assetBase}${path}?v=${encodeURIComponent(__BUILD_ID__)}`;
const response = await fetch(versionedAsset("data/manifest.json"), { cache: "no-store" });
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();
const selectedId = document.body.dataset.sampleId;
const example = manifest.examples.find((item) => item.id === selectedId);
if (!example) throw new Error(`Unknown sample page: ${selectedId}`);

const requestedBaseline = new URLSearchParams(location.search).get("baseline");
const baseline = example.baselines.find((item) => item.id === requestedBaseline) ?? example.baselines[0];
const views = baseline.views;
const rgbUrl = experimentAsset(views.overlay2d.rgb.url);
const reconstruction = loadReconstruction(experimentAsset(views.overlay2d.reconstruction));
const spider = views.spider;
const exampleIndex = manifest.examples.findIndex((item) => item.id === example.id);
const neighbor = (offset) => manifest.examples[(exampleIndex + offset + manifest.examples.length) % manifest.examples.length];
const sampleHref = (sample) => `${base}samples/${encodeURIComponent(sample.id)}/?baseline=${encodeURIComponent(baseline.id)}`;
const formatMetric = (value, suffix = "") => value == null ? "—" : `${Number(value).toFixed(3)}${suffix}`;

const baselineLinks = example.baselines.map((item) => `
  <a class="baseline-link ${item.id === baseline.id ? "active" : ""}" href="?baseline=${encodeURIComponent(item.id)}">
    <span>${item.label}</span><small>${item.views.spider ? "2D · 3D · SPIDER" : "2D · 3D"}</small>
  </a>
`).join("");

document.querySelector("#app").innerHTML = `
  <aside class="sidebar">
    <a class="brand" href="${base}"><span class="brand-mark">HL</span><span><strong>Experiments</strong><small>reconstruction → retargeting</small></span></a>
    <div class="sidebar-label">Baselines</div>
    <nav>${baselineLinks}</nav>
    <a class="repo-link" href="https://github.com/ilyssa-syx/hl-exps-site">GitHub repository ↗</a>
  </aside>
  <main>
    <div class="sample-nav"><a href="${base}">← all samples</a><span><a href="${sampleHref(neighbor(-1))}">← previous</a><a href="${sampleHref(neighbor(1))}">next →</a></span></div>
    <header class="topbar">
      <div><div class="eyebrow">${example.dataset} / ${example.split} / ${baseline.label}</div><h1>${example.label}</h1><p>${example.description}</p></div>
      <div class="meta"><span><small>object</small>${example.objectName}</span><span><small>frames</small>${example.frameCount}</span><span><small>fps</small>${example.fps}</span></div>
    </header>
    <section class="workspace">
      <div class="tabs" role="tablist" aria-label="Visualization type">
        <button class="tab active" data-tab="overlay" role="tab">2D overlay</button>
        <button class="tab" data-tab="scene" role="tab">3D reconstruction</button>
        ${spider ? `<button class="tab" data-tab="spider" role="tab">SPIDER</button>` : ""}
      </div>
      <div class="panel active" data-panel="overlay">
        <div class="stage single overlay-stage"><video id="input-rgb" src="${rgbUrl}" preload="auto" muted playsinline></video><canvas id="overlay-canvas"></canvas><span class="stage-tag">INPUT RGB + ${baseline.label.toUpperCase()}</span></div>
        <div class="layer-row"><span><i style="--layer:#8c96a8"></i>input RGB</span><span><i style="--layer:#62e0c5"></i>hand mesh</span><span><i style="--layer:#ff9d66"></i>object mesh</span></div>
      </div>
      <div class="panel" data-panel="scene" hidden>
        <div class="stage single"><canvas id="scene-canvas"></canvas><span class="stage-tag">${baseline.label.toUpperCase()} · CAMERA-SPACE GEOMETRY</span></div>
        <div class="layer-row"><span><i style="--layer:#62e0c5"></i>hand mesh</span><span><i style="--layer:#ff9d66"></i>object mesh</span></div>
      </div>
      ${spider ? `
        <div class="panel" data-panel="spider" hidden>
          <div class="spider-head"><div><span class="status evaluated">evaluated</span><strong>${spider.robot} · ${spider.embodiment}</strong></div>
            <div class="metrics"><span><small>ADD-AUC10</small>${formatMetric(spider.metrics.addAuc10)}</span><span><small>position error</small>${formatMetric(spider.metrics.positionErrorMeters, " m")}</span><span><small>rotation error</small>${formatMetric(spider.metrics.rotationErrorRadians, " rad")}</span></div>
          </div>
          <div class="spider-artifact spider-success"><video class="spider-video" src="${experimentAsset(spider.video)}" controls muted playsinline preload="metadata"></video></div>
        </div>` : ""}
      <div class="transport"><button id="play" aria-label="Play sequence">▶</button><span id="frame">000 / ${String(example.frameCount - 1).padStart(3, "0")}</span><input id="timeline" type="range" min="0" max="${example.frameCount - 1}" value="0" aria-label="Sequence frame" /><span id="time">0.00 s</span></div>
    </section>
  </main>
`;

const viewers = [new Preview2D(document.querySelector("#overlay-canvas"), document.querySelector("#input-rgb"), reconstruction), new SceneViewer(document.querySelector("#scene-canvas"), reconstruction)];
const tabs = [...document.querySelectorAll(".tab")];
const panels = [...document.querySelectorAll(".panel")];
tabs.forEach((tab) => tab.addEventListener("click", () => {
  tabs.forEach((item) => item.classList.toggle("active", item === tab));
  panels.forEach((panel) => { const active = panel.dataset.panel === tab.dataset.tab; panel.hidden = !active; panel.classList.toggle("active", active); });
  document.querySelector(".transport").hidden = tab.dataset.tab === "spider";
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
  viewers.forEach((viewer) => viewer.setProgress(safeFrame / Math.max(1, example.frameCount - 1)));
  frameLabel.textContent = `${String(safeFrame).padStart(3, "0")} / ${String(example.frameCount - 1).padStart(3, "0")}`;
  timeLabel.textContent = `${(safeFrame / example.fps).toFixed(2)} s`;
  if (seekVideo && Number.isFinite(inputRgb.duration)) inputRgb.currentTime = Math.min(inputRgb.duration, safeFrame / example.fps);
}
timeline.addEventListener("input", () => setFrame(Number(timeline.value)));
play.addEventListener("click", () => {
  playing = !playing; play.textContent = playing ? "❚❚" : "▶"; lastTick = performance.now();
  if (playing && inputRgb.ended) inputRgb.currentTime = 0;
  if (playing) inputRgb.play().catch(() => {}); else inputRgb.pause();
});
function animate(now) {
  if (playing) {
    if (!inputRgb.paused) {
      const frame = Math.min(example.frameCount - 1, Math.floor(inputRgb.currentTime * example.fps)); setFrame(frame, false);
      if (inputRgb.ended || frame >= example.frameCount - 1) { playing = false; inputRgb.pause(); play.textContent = "▶"; }
    } else if ((now - lastTick) / 1000 >= 1 / example.fps) { setFrame((Number(timeline.value) + 1) % example.frameCount); lastTick = now; }
  }
  requestAnimationFrame(animate);
}
setFrame(0);
requestAnimationFrame(animate);
