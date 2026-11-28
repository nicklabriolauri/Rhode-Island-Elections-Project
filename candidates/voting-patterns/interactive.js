async function enableVotingPlot(figure) {
  const fallback = figure.querySelector('[data-plot-fallback]');
  const controls = figure.querySelector('[data-plot-controls]');
  const select = controls.querySelector('select');
  const scores = controls.querySelector('output');
  const source = new URL(fallback.href);
  if (source.origin !== location.origin) return;

  const response = await fetch(source);
  if (!response.ok) return;
  const parsed = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
  if (parsed.documentElement.localName !== 'svg') return;

  const chart = document.importNode(parsed.documentElement, true);
  const points = Array.from(chart.querySelectorAll('circle:has(> title)'), dot => {
    const label = dot.querySelector('title').textContent;
    const match = label.match(/^(.+) \(([+-][\d.]+), ([+-][\d.]+)\)$/);
    if (!match) return null;
    const [, name, first, second] = match;
    return { dot, name, first, second };
  }).filter(Boolean).sort((a, b) => a.name.localeCompare(b.name));
  if (!points.length) return;

  chart.style.cssText = 'display:block;width:100%;height:auto';
  chart.removeAttribute('aria-labelledby');
  chart.setAttribute('aria-label', 'Legislative voting positions. Use the member menu to explore every point.');
  const ring = document.createElementNS(chart.namespaceURI, 'circle');
  ring.setAttribute('r', '9');
  ring.setAttribute('fill', 'none');
  ring.setAttribute('stroke', '#13264a');
  ring.setAttribute('stroke-width', '2');
  ring.setAttribute('pointer-events', 'none');
  chart.append(ring);

  function show(point) {
    for (const coord of ['cx', 'cy']) ring.setAttribute(coord, point.dot.getAttribute(coord));
    scores.textContent = `${point.name} · Dimension 1 ${point.first} · Dimension 2 ${point.second}`;
  }

  for (const point of points) {
    select.add(new Option(point.name, point.name));
    point.dot.style.cursor = 'pointer';
    point.dot.addEventListener('pointerenter', event => {
      if (event.pointerType === 'mouse') show(point);
    });
    point.dot.addEventListener('click', () => {
      select.value = point.name;
      show(point);
    });
  }
  const selected = () => points.find(point => point.name === select.value);
  select.value = points.some(point => point.name === figure.dataset.votingPlot)
    ? figure.dataset.votingPlot : points[0].name;
  select.addEventListener('change', () => show(selected()));
  chart.addEventListener('pointerleave', () => show(selected()));
  show(selected());
  fallback.replaceWith(chart);
  controls.hidden = false;
}

document.querySelectorAll('[data-voting-plot]').forEach(figure => {
  enableVotingPlot(figure).catch(error => console.warn('Interactive voting chart unavailable:', error));
});
