import "./style.css";

const base = import.meta.env.BASE_URL;
const response = await fetch(`${base}data/manifest.json?v=${encodeURIComponent(__BUILD_ID__)}`, { cache: "no-store" });
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();
const palette = ["#55a7ff", "#ff6f91", "#62e0c5", "#f6c85f"];
const baselineColor = (baseline, index) => baseline.color || palette[index % palette.length];
const formatMetric = (value, suffix) => value == null ? "—" : `${Number(value).toFixed(3)} ${suffix}`;

const card = (sample, index) => {
  const [subject, sequence, camera] = sample.label.split(" / ");
  const metrics = sample.baselines.map((baseline, baselineIndex) => `
    <div class="card-metric-row" style="--baseline:${baselineColor(baseline, baselineIndex)}">
      <strong><i></i>${baseline.label}</strong>
      <span>${formatMetric(baseline.metrics?.cdHScoredMeanCm, "cm")}</span>
      <span>${formatMetric(baseline.metrics?.objectAmodalScoredMeanIou, "")}</span>
      <span>${formatMetric(baseline.metrics?.handAmodalScoredMeanIou, "")}</span>
    </div>`).join("");
  return `
  <a class="sample-card" href="${base}samples/${encodeURIComponent(sample.id)}/">
    <div class="card-number">${String(index + 1).padStart(2, "0")}</div>
    <div class="eyebrow">${sample.dataset} / ${sample.split} / ${subject}</div>
    <h2>${sequence}</h2>
    <p class="camera-id">camera ${camera}</p>
    <div class="sample-meta"><span>${sample.objectName}</span><span>${sample.frameCount} frames</span><span>${sample.baselines.length} checkpoints</span></div>
    <div class="card-metrics">
      <div class="card-metric-head"><span></span><span>CD-H ↓</span><span>OBJ IoU ↑</span><span>HAND IoU ↑</span></div>
      ${metrics}
    </div>
  </a>`;
};

const sections = ["val", "test"].map((split) => {
  const examples = manifest.examples.filter((sample) => sample.split === split);
  return `<section class="catalog-section"><div class="section-title"><h2>${split}</h2><span>${examples.length} samples</span></div><div class="sample-grid">${examples.map(card).join("")}</div></section>`;
}).join("");

document.querySelector("#app").innerHTML = `
  <main class="catalog">
    <header class="catalog-head"><div class="brand-mark">HL</div><div><div class="eyebrow">DexYCB · 2026-10-26 evaluation</div><h1>Experiment samples</h1><p>30 sequences · 20 validation + 10 test · three CD-H/IoU checkpoints</p></div></header>
    ${sections}
  </main>`;
