import "./style.css";

const base = import.meta.env.BASE_URL;
const manifestPath = document.body.dataset.manifest || "data/manifest.json";
const response = await fetch(`${base}${manifestPath}?v=${encodeURIComponent(__BUILD_ID__)}`, { cache: "no-store" });
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();
const catalog = manifest.catalog || {};
const palette = ["#55a7ff", "#ff6f91", "#62e0c5", "#f6c85f"];
const baselineColor = (baseline, index) => baseline.color || palette[index % palette.length];
const formatMetric = (value, suffix = "") => value == null ? "—" : `${Number(value).toFixed(3)}${suffix}`;
const formatSpiderMetric = (metrics) => metrics?.spiderStatus === "evaluated" && metrics.spiderAddAuc10 != null
  ? Number(metrics.spiderAddAuc10).toFixed(3)
  : `<span class="metric-failed">${metrics?.spiderStatus || "—"}</span>`;
const cdIou = catalog.metricSet === "cd-iou";

const metricRow = (baseline, baselineIndex) => {
  const metrics = baseline.metrics || {};
  const values = cdIou
    ? `<span>${formatMetric(metrics.cdHScoredMeanCm, " cm")}</span>
       <span>${formatMetric(metrics.objectAmodalScoredMeanIou)}</span>
       <span>${formatMetric(metrics.handAmodalScoredMeanIou)}</span>`
    : `<span>${formatMetric(metrics.waMpjpeMeanMm, " mm")}</span>
       <span>${formatMetric(metrics.cdHScoredMeanCm, " cm")}</span>
       <span>${formatSpiderMetric(metrics)}</span>`;
  return `<div class="card-metric-row" style="--baseline:${baselineColor(baseline, baselineIndex)}">
    <strong><i></i>${baseline.label}</strong>${values}
  </div>`;
};

const card = (sample, index) => {
  const [subject, sequence, camera] = sample.label.split(" / ");
  const metrics = sample.baselines.map(metricRow).join("");
  const headings = cdIou
    ? "<span></span><span>CD-H ↓</span><span>OBJ IoU ↑</span><span>HAND IoU ↑</span>"
    : "<span></span><span>WA-MPJPE ↓</span><span>CD-H ↓</span><span>SPIDER ↑</span>";
  return `<a class="sample-card" href="${base}${catalog.sampleRoot || "samples"}/${encodeURIComponent(sample.id)}/">
    <div class="card-number">${String(index + 1).padStart(2, "0")}</div>
    <div class="eyebrow">${sample.dataset} / ${sample.split} / ${subject}</div>
    <h2>${sequence}</h2><p class="camera-id">camera ${camera}</p>
    <div class="sample-meta"><span>${sample.objectName}</span><span>${sample.frameCount} frames</span><span>${sample.baselines.length} baselines</span></div>
    <div class="card-metrics"><div class="card-metric-head">${headings}</div>${metrics}</div>
  </a>`;
};

const sections = ["val", "test"].map((split) => {
  const examples = manifest.examples.filter((sample) => sample.split === split);
  return `<section class="catalog-section"><div class="section-title"><h2>${split}</h2><span>${examples.length} samples</span></div><div class="sample-grid">${examples.map(card).join("")}</div></section>`;
}).join("");
const related = (catalog.relatedCatalogs || []).map((item) =>
  `<a class="catalog-link" href="${base}${item.url}">${item.label}</a>`
).join("");

document.querySelector("#app").innerHTML = `<main class="catalog">
  <header class="catalog-head"><div class="brand-mark">HL</div><div><div class="eyebrow">${catalog.eyebrow || "DexYCB evaluation"}</div><h1>${catalog.title || "Experiment samples"}</h1><p>${catalog.description || ""}</p><nav class="catalog-links">${related}</nav></div></header>
  ${sections}
</main>`;
