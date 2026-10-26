import "./style.css";
import { Preview2D } from "./preview-2d.js";
import { loadReconstruction } from "./reconstruction-data.js";

const base = import.meta.env.BASE_URL;
const assetBase = import.meta.env.VITE_ASSET_BASE_URL || base;
const versionedAsset = (path) => `${base}${path}?v=${encodeURIComponent(__BUILD_ID__)}`;
const experimentAsset = (path) => `${assetBase}${path}?v=${encodeURIComponent(__BUILD_ID__)}`;
const response = await fetch(versionedAsset("data/manifest.json"), { cache: "no-store" });
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();
const example = manifest.examples.find((item) => item.id === document.body.dataset.sampleId);
if (!example) throw new Error(`Unknown sample page: ${document.body.dataset.sampleId}`);

const colors = { input: "#55a7ff", "refined-20261023": "#ff6f91" };
const selected = new Set(example.baselines.map((item) => item.id));
const reconstructionCache = new Map();
const reconstructionFor = (item) => {
  if (!reconstructionCache.has(item.id)) {
    reconstructionCache.set(item.id, loadReconstruction(experimentAsset(item.views.overlay2d.reconstruction)));
  }
  return reconstructionCache.get(item.id);
};
const layers = example.baselines.map((item) => ({
  id: item.id, label: item.label, color: colors[item.id], load: () => reconstructionFor(item),
}));
const rgbUrl = experimentAsset(example.baselines[0].views.overlay2d.rgb.url);
const exampleIndex = manifest.examples.findIndex((item) => item.id === example.id);
const neighbor = (offset) => manifest.examples[(exampleIndex + offset + manifest.examples.length) % manifest.examples.length];
const sampleHref = (sample) => `${base}samples/${encodeURIComponent(sample.id)}/`;
const formatMetric = (value, suffix = "") => value == null ? "—" : `${Number(value).toFixed(3)}${suffix}`;
const formatSpiderMetric = (metrics) => metrics.spiderStatus === "evaluated" && metrics.spiderAddAuc10 != null
  ? Number(metrics.spiderAddAuc10).toFixed(3)
  : `<span class="metric-failed">${metrics.spiderStatus || "not evaluated"}</span>`;
const reconstructionMetrics = example.baselines.map((item) => {
  const metrics = item.metrics ?? {};
  return `<article class="sequence-metric" style="--baseline:${colors[item.id]}">
    <div class="metric-baseline"><i></i><strong>${item.label}</strong></div>
    <div class="metric-values">
      <span><small>WA-MPJPE ↓</small>${formatMetric(metrics.waMpjpeMeanMm, " mm")}<em>${metrics.waMpjpeEvaluatedFrames ?? "—"} evaluated frames</em></span>
      <span><small>CD-H ↓</small>${formatMetric(metrics.cdHScoredMeanCm, " cm")}<em>${metrics.cdHEvaluatedFrames ?? "—"} / ${metrics.cdHEligibleFrames ?? "—"} evaluated</em></span>
      <span><small>SPIDER ADD-AUC10 ↑</small>${formatSpiderMetric(metrics)}<em>${metrics.spiderStatus || "not evaluated"}</em></span>
    </div>
  </article>`;
}).join("");

const baselineControls = example.baselines.map((item) => `
  <button class="baseline-toggle" data-baseline="${item.id}" aria-pressed="true" style="--baseline:${colors[item.id]}">
    <i></i><span>${item.label}</span><small>${item.views.spider ? "2D · 3D · SPIDER" : "2D · 3D"}</small>
  </button>`).join("");
const layerChips = example.baselines.map((item) => `
  <button class="layer-chip" data-baseline="${item.id}" aria-pressed="true" style="--baseline:${colors[item.id]}"><i></i>${item.label}</button>`).join("");
const spiderCards = example.baselines.filter((item) => item.views.spider).map((item) => {
  const spider = item.views.spider;
  return `<article class="spider-run" data-baseline="${item.id}" style="--baseline:${colors[item.id]}">
    <div class="spider-head">
      <div><i class="baseline-dot"></i><strong>${item.label}</strong><span class="status evaluated">evaluated</span><small>${spider.robot} · ${spider.embodiment}</small></div>
      <div class="metrics"><span><small>ADD-AUC10</small>${formatMetric(spider.metrics.addAuc10)}</span><span><small>position error</small>${formatMetric(spider.metrics.positionErrorMeters, " m")}</span><span><small>rotation error</small>${formatMetric(spider.metrics.rotationErrorRadians, " rad")}</span></div>
    </div>
    <video class="spider-video" data-src="${experimentAsset(spider.video)}" controls muted playsinline preload="none"></video>
  </article>`;
}).join("");

document.querySelector("#app").innerHTML = `
  <aside class="sidebar">
    <a class="brand" href="${base}"><span class="brand-mark">HL</span><span><strong>Experiments</strong><small>reconstruction → retargeting</small></span></a>
    <div class="sidebar-label">Visible baselines</div>
    <nav class="baseline-controls">${baselineControls}</nav>
    <p class="sidebar-hint">Select either baseline or show both together.</p>
    <a class="repo-link" href="https://github.com/ilyssa-syx/hl-exps-site">GitHub repository ↗</a>
  </aside>
  <main>
    <div class="sample-nav"><a href="${base}">← all samples</a><span><a href="${sampleHref(neighbor(-1))}">← previous</a><a href="${sampleHref(neighbor(1))}">next →</a></span></div>
    <header class="topbar">
      <div><div class="eyebrow">${example.dataset} / ${example.split} / baseline comparison</div><h1>${example.label}</h1><p>${example.description}</p></div>
      <div class="meta"><span><small>object</small>${example.objectName}</span><span><small>frames</small>${example.frameCount}</span><span><small>fps</small>${example.fps}</span></div>
    </header>
    <section class="workspace">
      <div class="tabs" role="tablist" aria-label="Visualization type">
        <button class="tab active" data-tab="overlay" role="tab">2D overlay</button>
        <button class="tab" data-tab="scene" role="tab">3D reconstruction</button>
        ${spiderCards ? `<button class="tab" data-tab="spider" role="tab">SPIDER</button>` : ""}
      </div>
      <div class="panel active" data-panel="overlay">
        <div class="stage single overlay-stage"><video id="input-rgb" src="${rgbUrl}" preload="metadata" muted playsinline></video><canvas id="overlay-canvas"></canvas><span class="stage-tag">INPUT RGB + SELECTED BASELINES</span></div>
        <div class="layer-row baseline-legend">${layerChips}</div>
      </div>
      <div class="panel" data-panel="scene" hidden>
        <div class="stage single scene-stage">
          <canvas id="scene-canvas" tabindex="0" aria-label="Interactive 3D reconstruction. Drag to rotate, scroll to zoom, and right-drag to pan."></canvas>
          <span class="stage-tag">SELECTED BASELINES · CAMERA-SPACE GEOMETRY</span>
          <div class="scene-controls" aria-label="3D navigation help">
            <span><b>drag</b> rotate</span><span><b>scroll</b> zoom</span><span><b>right-drag</b> pan</span>
            <button id="reset-view" type="button">Reset view</button>
          </div>
        </div>
        <div class="layer-row baseline-legend">${layerChips}</div>
      </div>
      ${spiderCards ? `<div class="panel" data-panel="spider" hidden><div class="spider-stack">${spiderCards}</div><p class="spider-empty" hidden>No successful SPIDER rollout for the selected baselines.</p></div>` : ""}
      <div class="transport"><button id="play" aria-label="Play sequence">▶</button><span id="frame">000 / ${String(example.frameCount - 1).padStart(3, "0")}</span><input id="timeline" type="range" min="0" max="${example.frameCount - 1}" value="0" aria-label="Sequence frame" /><span id="time">0.00 s</span></div>
    </section>
    <section class="sequence-metrics" aria-labelledby="sequence-metrics-title">
      <div class="sequence-metrics-head"><div><div class="eyebrow">Sequence evaluation</div><h2 id="sequence-metrics-title">Reconstruction & retargeting metrics</h2></div><p>WA-MPJPE / CD-H ↓ · SPIDER ↑</p></div>
      <div class="sequence-metric-grid">${reconstructionMetrics}</div>
      <p class="metric-note">WA-MPJPE is the evaluated-frame wrist-aligned mean. CD-H is the coverage-penalized wrist-relative object Chamfer mean. SPIDER reports object-translation ADD-AUC10; failed rollouts remain marked as failed rather than scored as zero.</p>
    </section>
  </main>`;

const inputRgb = document.querySelector("#input-rgb");
const preview2d = new Preview2D(document.querySelector("#overlay-canvas"), inputRgb, layers);
let sceneViewer = null;
let sceneLoading = null;
let activeTab = "overlay";
let currentFrame = 0;
let playing = false;
let videoCallback = null;
let animationFrame = null;

function ensureSceneViewer() {
  if (sceneViewer) return Promise.resolve(sceneViewer);
  sceneLoading ??= import("./scene-viewer.js").then(({ SceneViewer }) => {
    sceneViewer = new SceneViewer(document.querySelector("#scene-canvas"), layers);
    sceneViewer.setVisible(selected);
    sceneViewer.setProgress(currentFrame / Math.max(1, example.frameCount - 1));
    return sceneViewer;
  });
  return sceneLoading;
}

function updateSpider() {
  const cards = [...document.querySelectorAll(".spider-run")];
  let visible = 0;
  cards.forEach((card) => {
    const show = selected.has(card.dataset.baseline);
    card.hidden = !show;
    const video = card.querySelector("video");
    if (!show) video.pause();
    if (show && activeTab === "spider" && !video.src) { video.src = video.dataset.src; video.load(); }
    if (show) visible += 1;
  });
  const empty = document.querySelector(".spider-empty");
  if (empty) empty.hidden = visible !== 0;
}

function updateBaselineControls() {
  document.querySelectorAll("[data-baseline]").forEach((control) => {
    if (control.matches("button")) control.setAttribute("aria-pressed", String(selected.has(control.dataset.baseline)));
  });
}

function toggleBaseline(id) {
  if (selected.has(id)) selected.delete(id); else selected.add(id);
  updateBaselineControls();
  preview2d.setVisible(selected);
  sceneViewer?.setVisible(selected);
  updateSpider();
  setFrame(currentFrame, false, true);
}

document.querySelectorAll(".baseline-toggle, .layer-chip").forEach((button) => button.addEventListener("click", () => toggleBaseline(button.dataset.baseline)));
document.querySelector("#reset-view").addEventListener("click", () => sceneViewer?.resetView());
const tabs = [...document.querySelectorAll(".tab")];
const panels = [...document.querySelectorAll(".panel")];
tabs.forEach((tab) => tab.addEventListener("click", () => {
  activeTab = tab.dataset.tab;
  tabs.forEach((item) => item.classList.toggle("active", item === tab));
  panels.forEach((panel) => { const active = panel.dataset.panel === activeTab; panel.hidden = !active; panel.classList.toggle("active", active); });
  document.querySelector(".transport").hidden = activeTab === "spider";
  if (activeTab === "scene") void ensureSceneViewer();
  if (activeTab === "spider") { stopPlayback(); updateSpider(); }
  else setFrame(currentFrame, false, true);
}));

const timeline = document.querySelector("#timeline");
const frameLabel = document.querySelector("#frame");
const timeLabel = document.querySelector("#time");
const play = document.querySelector("#play");
function setFrame(frame, seekVideo = true, force = false) {
  const safeFrame = Math.max(0, Math.min(example.frameCount - 1, Math.round(frame)));
  if (!force && safeFrame === currentFrame) return;
  currentFrame = safeFrame;
  timeline.value = safeFrame;
  const progress = safeFrame / Math.max(1, example.frameCount - 1);
  if (activeTab === "overlay") preview2d.setProgress(progress);
  if (activeTab === "scene") sceneViewer?.setProgress(progress);
  frameLabel.textContent = `${String(safeFrame).padStart(3, "0")} / ${String(example.frameCount - 1).padStart(3, "0")}`;
  timeLabel.textContent = `${(safeFrame / example.fps).toFixed(2)} s`;
  if (seekVideo && Number.isFinite(inputRgb.duration)) inputRgb.currentTime = Math.min(Math.max(0, inputRgb.duration - 0.001), safeFrame / example.fps);
}
function cancelFrameUpdates() {
  if (videoCallback !== null && inputRgb.cancelVideoFrameCallback) inputRgb.cancelVideoFrameCallback(videoCallback);
  if (animationFrame !== null) cancelAnimationFrame(animationFrame);
  videoCallback = null;
  animationFrame = null;
}
function scheduleFrameUpdate() {
  if (!playing || document.hidden) return;
  if (inputRgb.requestVideoFrameCallback) {
    videoCallback = inputRgb.requestVideoFrameCallback((_now, metadata) => { videoCallback = null; setFrame(Math.floor(metadata.mediaTime * example.fps), false); scheduleFrameUpdate(); });
  } else {
    animationFrame = requestAnimationFrame(() => { animationFrame = null; setFrame(Math.floor(inputRgb.currentTime * example.fps), false); scheduleFrameUpdate(); });
  }
}
function stopPlayback() { playing = false; inputRgb.pause(); play.textContent = "▶"; cancelFrameUpdates(); }
timeline.addEventListener("input", () => setFrame(Number(timeline.value)));
play.addEventListener("click", () => {
  if (playing) { stopPlayback(); return; }
  if (inputRgb.ended || currentFrame >= example.frameCount - 1) { inputRgb.currentTime = 0; setFrame(0, false, true); }
  playing = true; play.textContent = "❚❚";
  inputRgb.play().then(scheduleFrameUpdate).catch(stopPlayback);
});
inputRgb.addEventListener("ended", stopPlayback);
inputRgb.addEventListener("loadedmetadata", () => setFrame(currentFrame, true, true), { once: true });
document.addEventListener("visibilitychange", () => { if (document.hidden) stopPlayback(); });
window.addEventListener("pagehide", () => { stopPlayback(); sceneViewer?.dispose(); });
updateBaselineControls();
updateSpider();
setFrame(0, false, true);
