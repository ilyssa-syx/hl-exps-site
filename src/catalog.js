import "./style.css";

const base = import.meta.env.BASE_URL;
const response = await fetch(`${base}data/manifest.json`);
if (!response.ok) throw new Error(`Could not load manifest: ${response.status}`);
const manifest = await response.json();

const cards = manifest.examples.map((sample) => `
  <a class="sample-card" href="${base}samples/${encodeURIComponent(sample.id)}/">
    <div class="eyebrow">${sample.dataset ?? "dataset"} / ${sample.split ?? "split"}</div>
    <h2>${sample.label}</h2>
    <p>${sample.description ?? "Sequence-level experiment sample."}</p>
    <div class="sample-meta">
      <span>${sample.objectName ?? "unknown object"}</span>
      <span>${sample.frameCount} frames</span>
      <span>${sample.fps} fps</span>
    </div>
  </a>
`).join("");

document.querySelector("#app").innerHTML = `
  <main class="catalog">
    <header class="catalog-head">
      <div class="brand-mark">HL</div>
      <div>
        <div class="eyebrow">HOI reconstruction → SPIDER retargeting</div>
        <h1>Experiment samples</h1>
        <p>Each sample opens on its own static page with 2D, 3D, and retargeting views.</p>
      </div>
    </header>
    <section class="sample-grid">${cards}</section>
  </main>
`;
