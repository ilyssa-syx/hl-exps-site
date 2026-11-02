import "./style.css";

const base = import.meta.env.BASE_URL;
const manifestPath = document.body.dataset.manifest || "data/manifest.json";
const response = await fetch(`${base}${manifestPath}?v=${encodeURIComponent(__BUILD_ID__)}`, { cache: "no-store" });
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();
const catalog = manifest.catalog || {};
const example = manifest.examples.find((item) => item.id === document.body.dataset.sampleId);
if (!example?.segments) throw new Error(`Unknown segmented sequence: ${document.body.dataset.sampleId}`);

const colors = Object.fromEntries(example.baselines.map((item) => [item.id, item.color]));
const metricColumns = [
  { label: "ADD-S", unit: "cm", direction: "min", value: (m) => m.addAligned.mean },
  { label: "Object amodal IoU", unit: "", direction: "max", value: (m) => m.objectAmodalIou.mean, digits: 4 },
  { label: "Hand amodal IoU", unit: "", direction: "max", value: (m) => m.handAmodalIou.mean, digits: 4 },
  { label: "Hand scored IoU", unit: "", direction: "max", value: (m) => m.handAmodalIou.scoredMean, digits: 4 },
  { label: "CD-H", unit: "cm", direction: "min", value: (m) => m.cdH.mean },
  { label: "CD-H scored", unit: "cm", direction: "min", value: (m) => m.cdH.scoredMean },
  { label: "Obj-rel", unit: "cm", direction: "min", value: (m) => m.objRel.mean },
  { label: "Wrist trans.", unit: "mm", direction: "min", value: (m) => m.wristTranslation.mean },
  { label: "Wrist rot.", unit: "deg", direction: "min", value: (m) => m.wristRotation.mean },
].filter((metric) => example.baselines.every((item) => {
  try { return Number.isFinite(metric.value(item.metrics)); } catch { return false; }
}));
const metricBest = metricColumns.map((metric) => {
  const values = example.baselines.map((item) => metric.value(item.metrics));
  return metric.direction === "max" ? Math.max(...values) : Math.min(...values);
});
const metricTable = `<div class="metric-scroll"><table class="metric-table">
  <thead><tr><th>Baseline</th>${metricColumns.map((metric) => `<th>${metric.label}<small>${metric.direction === "max" ? "↑" : "↓"}${metric.unit ? ` · ${metric.unit}` : ""}</small></th>`).join("")}</tr></thead>
  <tbody>${example.baselines.map((item) => `<tr style="--baseline:${colors[item.id]}"><th><i></i>${item.label}</th>${metricColumns.map((metric, index) => {
    const value = metric.value(item.metrics);
    return `<td class="${value === metricBest[index] ? "best" : ""}">${value.toFixed(metric.digits ?? 3)}</td>`;
  }).join("")}</tr>`).join("")}</tbody>
</table></div><p class="metric-note">${example.metricNote || "Per-sequence evaluation means."}</p>`;

const sampleRoot = catalog.sampleRoot || "samples";
const sequenceRoot = `${base}${sampleRoot}/${encodeURIComponent(example.id)}/`;
const segmentCards = example.segments.map((segment, index) => `
  <a class="sample-card segment-card" href="${sequenceRoot}segments/${encodeURIComponent(segment.id)}/">
    <div class="card-number">${String(index + 1).padStart(2, "0")}</div>
    <div class="eyebrow">frames ${segment.startFrame}–${segment.endFrame - 1}</div>
    <h2>${segment.label}</h2>
    <p>Open this five-second 2D/3D comparison.</p>
    <div class="sample-meta"><span>${segment.frameCount} frames</span><span>${example.baselines.length} baselines</span></div>
  </a>`).join("");

document.querySelector("#app").innerHTML = `<main class="catalog sequence-overview">
  <div class="sample-nav"><a href="${base}${document.body.dataset.catalog || ""}">← all samples</a></div>
  <header class="catalog-head"><div class="brand-mark">HL</div><div>
    <div class="eyebrow">${example.dataset} / ${example.split} / sequence overview</div>
    <h1>${example.label}</h1><p>${example.description}</p>
    <div class="sample-meta"><span>${example.objectName}</span><span>${example.frameCount} frames</span><span>${example.segments.length} segments</span></div>
  </div></header>
  <section class="metrics-inline sequence-metrics">
    <div class="metrics-heading"><div><div class="eyebrow">${example.metricLabel || "Evaluation"}</div><h2>Per-sequence metrics</h2></div><p>Mean performance across the full sequence.</p></div>
    ${metricTable}
  </section>
  <section class="catalog-section"><div class="section-title"><h2>5-second segments</h2><span>${example.segments.length} segments</span></div><div class="sample-grid">${segmentCards}</div></section>
</main>`;
