import "./style.css";

const base = import.meta.env.BASE_URL;
const manifestPath = document.body.dataset.manifest || "data/manifest.json";
const response = await fetch(`${base}${manifestPath}?v=${encodeURIComponent(__BUILD_ID__)}`, { cache: "no-store" });
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();
const catalog = manifest.catalog || {};
const card = (sample, index) => {
  const [subject, sequence, camera] = sample.label.split(" / ");
  return `<a class="sample-card" href="${base}${catalog.sampleRoot || "samples"}/${encodeURIComponent(sample.id)}/">
    <div class="card-number">${String(index + 1).padStart(2, "0")}</div>
    <div class="eyebrow">${sample.dataset} / ${sample.split} / ${subject}</div>
    <h2>${sequence}</h2><p class="camera-id">camera ${camera}</p>
    <div class="sample-meta"><span>${sample.objectName}</span><span>${sample.frameCount} frames</span><span>${sample.baselines.length} baselines</span></div>
  </a>`;
};

const testExamples = manifest.examples.filter((sample) => sample.split === "test");
const sections = `<section class="catalog-section"><div class="section-title"><h2>dexycb-test</h2><span>${testExamples.length} samples</span></div><div class="sample-grid">${testExamples.map(card).join("")}</div></section>`;
const related = (catalog.relatedCatalogs || []).map((item) =>
  `<a class="catalog-link" href="${base}${item.url}">${item.label}</a>`
).join("");

document.querySelector("#app").innerHTML = `<main class="catalog">
  <header class="catalog-head"><div class="brand-mark">HL</div><div><div class="eyebrow">${catalog.eyebrow || "DexYCB evaluation"}</div><h1>${catalog.title || "Experiment samples"}</h1><p>${catalog.description || ""}</p><nav class="catalog-links">${related}</nav></div></header>
  ${sections}
</main>`;
