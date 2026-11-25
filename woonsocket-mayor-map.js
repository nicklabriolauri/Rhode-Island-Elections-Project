(() => {
  "use strict";
  const candidates = {
    gendron: { name: "Daniel Gendron", color: "#16766c", shades: ["#c8e8e1", "#88c8bd", "#489f92", "#16766c", "#0b4e49"] },
    beauchamp: { name: "Christopher Beauchamp", color: "#93501c", shades: ["#f5dfc1", "#edbc83", "#d5934d", "#af6a2b", "#783c13"] },
  };
  const citywide = { name: "Citywide tally", gendron: 4530, beauchamp: 3302, writeIns: 115 };
  const mode = document.getElementById("map-mode");
  const precinct = document.getElementById("precinct-select");
  const container = document.getElementById("municipal-map");
  const tally = document.getElementById("tally-detail");
  const legend = document.getElementById("map-legend");
  const numbers = new Intl.NumberFormat("en-US");
  const total = r => r.gendron + r.beauchamp + r.writeIns;
  const share = (r, key) => r[key] / total(r) * 100;
  const margin = r => share(r, "gendron") - share(r, "beauchamp");
  const marginBand = value => value < 5 ? 0 : value < 10 ? 1 : value < 15 ? 2 : value < 20 ? 3 : 4;
  const shareBand = value => value < 40 ? 0 : value < 45 ? 1 : value < 50 ? 2 : value < 55 ? 3 : 4;
  let map, layers, bounds;
  const records = new Map();
  const rows = [...document.querySelectorAll("#results tbody tr")];
  rows.forEach(row => {
    const [name, ...counts] = [...row.cells].slice(0, 4).map(cell => cell.textContent);
    const [gendron, beauchamp, writeIns] = counts.map(value => Number(value.replaceAll(",", "")));
    records.set(row.id.slice(-4), { name, gendron, beauchamp, writeIns });
  });

  function drawTally(focusKey) {
    const result = records.get(precinct.value) || citywide;
    const heading = document.createElement("h2");
    heading.textContent = result.name;
    const count = document.createElement("p");
    count.textContent = numbers.format(total(result)) + " votes";
    tally.replaceChildren(heading, count);
    for (const [key, candidate] of Object.entries(candidates)) {
      const line = document.createElement("div");
      line.className = "tally-line";
      line.style.setProperty("--candidate", candidate.color);
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("aria-pressed", String(mode.value === key));
      button.title = "Map " + candidate.name + "’s vote share";
      const name = document.createElement("strong");
      name.className = "tally-choice";
      name.textContent = candidate.name + (result === citywide && key === "gendron" ? " · Winner" : "");
      const value = document.createElement("span");
      value.textContent = numbers.format(result[key]) + " · " + share(result, key).toFixed(2) + "%";
      button.append(name, value);
      button.addEventListener("click", () => {
        mode.value = mode.value === key ? "margin" : key;
        refresh(key);
      });
      const bar = document.createElement("div");
      bar.className = "result-bar";
      bar.setAttribute("aria-hidden", "true");
      const fill = document.createElement("span");
      fill.style.setProperty("--share", share(result, key) + "%");
      bar.append(fill);
      line.append(button, bar);
      tally.append(line);
      if (key === focusKey) button.focus();
    }
    const other = document.createElement("p");
    other.textContent = "Write-ins " + numbers.format(result.writeIns) + " · " + share(result, "writeIns").toFixed(2) + "%";
    const lead = document.createElement("p");
    lead.textContent = "Gendron + " + margin(result).toFixed(2) + " percentage points";
    tally.append(other, lead);
  }

  function style(feature) {
    const r = feature.properties;
    const selected = precinct.value === r.code;
    const modeKey = mode.value;
    const lead = margin(r);
    const palette = candidates[modeKey] || candidates[lead >= 0 ? "gendron" : "beauchamp"];
    const band = modeKey === "margin" ? marginBand(Math.abs(lead)) : shareBand(share(r, modeKey));
    return { color: selected ? "#182b4d" : "#fff", weight: selected ? 3 : 1.3, fillColor: palette.shades[band], fillOpacity: selected ? .94 : .74 };
  }
  function drawLegend() {
    const isMargin = mode.value === "margin";
    const groups = isMargin ? Object.values(candidates) : [candidates[mode.value]];
    const bins = isMargin ? ["<5", "5–<10", "10–<15", "15–<20", "20+"] : ["<40", "40–<45", "45–<50", "50–<55", "55+"];
    legend.replaceChildren();
    for (const candidate of groups) {
      const group = document.createElement("span");
      group.append(candidate.name + (isMargin ? " lead (pp) " : " share (%) "));
      bins.forEach((label, index) => {
        const swatch = document.createElement("i");
        swatch.style.backgroundColor = candidate.shades[index];
        swatch.setAttribute("aria-hidden", "true");
        const item = document.createElement("span");
        item.append(swatch, label);
        group.append(item);
      });
      legend.append(group);
    }
  }
  function refresh(focusKey) {
    if (layers) layers.setStyle(style);
    drawLegend();
    drawTally(focusKey);
  }
  mode.addEventListener("change", () => refresh());
  precinct.addEventListener("change", () => {
    refresh();
    if (!map) return;
    if (!precinct.value) map.fitBounds(bounds.pad(.18));
    else layers.eachLayer(layer => {
      if (layer.feature.properties.code === precinct.value) map.fitBounds(layer.getBounds().pad(.3), { maxZoom: 15 });
    });
  });
  const hash = location.hash.match(/^#precinct-(\d{4})$/);
  if (hash && records.has(hash[1])) precinct.value = hash[1];
  refresh();
  (async () => {
    const response = await fetch("/data/woonsocket/mayoral-precincts.json");
    if (!response.ok || !window.L) throw new Error("Map unavailable");
    const geo = await response.json();
    container.replaceChildren();
    map = L.map(container, { scrollWheelZoom: false, maxZoom: 18 });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    layers = L.geoJSON(geo, {
      style,
      onEachFeature(feature, layer) {
        const r = feature.properties;
        const label = document.createElement("span");
        label.textContent = r.name + " · Gendron +" + margin(r).toFixed(1) + " pp";
        layer.bindTooltip(label, { sticky: true });
        layer.on("click", () => { precinct.value = r.code; refresh(); });
      },
    }).addTo(map);
    bounds = layers.getBounds();
    map.fitBounds(bounds.pad(.18));
  })().catch(() => {
    container.textContent = "The map could not load. Use the precinct selector or results table.";
  });
})();
