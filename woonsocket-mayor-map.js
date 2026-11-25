(() => {
  const select = document.getElementById("precinct-select");
  const detail = document.getElementById("precinct-detail");
  const links = [...document.querySelectorAll(".precinct-map a")];

  function show(code) {
    const row = document.getElementById("precinct-" + code);
    if (!row) return;
    const [name, gendron, beauchamp, writeIns, margin] = [...row.cells].map(cell => cell.textContent);
    const heading = document.createElement("h3");
    heading.textContent = name;
    const result = document.createElement("p");
    result.textContent = `Gendron ${gendron} · Beauchamp ${beauchamp} · Write-ins ${writeIns}`;
    const lead = document.createElement("p");
    lead.textContent = `Gendron lead: ${margin}`;
    detail.replaceChildren(heading, result, lead);
  }

  function choose(code) {
    select.value = code;
    for (const link of links) {
      if (link.getAttribute("href") === "#precinct-" + code) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    }
    if (code) show(code);
    else detail.textContent = "Choose a precinct on the map or from the list.";
  }

  for (const link of links) {
    const code = link.getAttribute("href").slice("#precinct-".length);
    link.addEventListener("click", event => {
      event.preventDefault();
      choose(code);
    });
    link.addEventListener("pointerenter", () => { if (!select.value) show(code); });
    link.addEventListener("focus", () => { if (!select.value) show(code); });
  }
  select.addEventListener("change", () => choose(select.value));
  const initial = location.hash.match(/^#precinct-(\d{4})$/);
  if (initial && document.getElementById("precinct-" + initial[1])) choose(initial[1]);
})();
