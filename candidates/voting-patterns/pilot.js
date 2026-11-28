(() => {
  const assets = new URL('.', document.currentScript.src);
  const explorer = new URL('index.html', assets);
  const chartUrl = new URL('senate-two-dimensional.svg', assets);
  const candidateParam = new URLSearchParams(location.search).get('candidate');
  const sourceLink = 'https://www.rilegislature.gov/journals/senatejournals/SitePages/senateJournals.aspx';
  const modelLink = 'https://github.com/nicklabriolauri/Rhode-Island-Elections-Project/tree/main/analysis/senate-two-dimensional-preview';

  async function init(root) {
    const candidate = root.dataset.candidate;
    const profile = root.dataset.compact === 'true';
    const section = root.closest('#voting-patterns');
    if (section) {
      const heading = document.createElement('h2');
      heading.textContent = 'Senate voting patterns · W-NOMINATE';
      section.replaceChildren(heading, root);
    }
    root.innerHTML = `
      <p>2025–2026 Rhode Island Senate · 358 divided roll calls through June 11, 2026</p>
      <p data-unscored hidden></p>
      <div class="vp-controls"><label>Explore a senator<select></select></label></div>
      <p>Hover near a dot for its name and scores. Click, tap, or use the menu to select a senator.</p>
      <div class="vp-plot"><div class="vp-tooltip" aria-hidden="true" hidden><strong></strong><span></span></div></div>
      <p class="vp-selected" aria-live="polite"></p>
      <dl>
        <dt><strong>Dimension 1 · Between-party alignment</strong></dt>
        <dd>The horizontal axis captures the strongest voting divide in this Senate sample. Democrats fall to the left and Republicans to the right. Coordinates indicate voting positions on a fitted scale.</dd>
        <dt><strong>Dimension 2 · Within-party divides</strong></dt>
        <dd>The vertical axis captures a secondary voting pattern. Senators with similar horizontal scores can still vote differently. Positive and negative positions indicate different patterns, and the direction depends on the model’s anchor.</dd>
      </dl>
      <details open><summary>Where Senate Democrats split</summary>
      <p>The chart shows two groups of Democrats on the left and a Republican cluster on the right. The vertical gap between the Democratic groups reflects disagreements over issues such as energy and criminal justice.</p>
      <ul>
        <li><a href="https://www.rilegislature.gov/journals/senatejournals/2025%20Senate%20Journals/06-10-2025.pdf#page=25">Nuclear power purchases, June 2025</a>: 0 of 13 higher-scoring Democrats voted yes, compared with 19 of 19 lower-scoring Democrats who voted.</li>
        <li><a href="https://www.rilegislature.gov/journals/senatejournals/2026%20Senate%20Journals/SJ%2006-09-2026.pdf#page=6">Limits on utility profits, June 2026</a>: 12 of 14 higher-scoring Democrats and 0 of 20 lower-scoring Democrats voted for the amendment.</li>
        <li><a href="https://www.rilegislature.gov/journals/senatejournals/2026%20Senate%20Journals/SJ%2006-11-2026.pdf#page=24">Use of force to resist lawful orders in prison, June 2026</a>: 1 of 14 higher-scoring Democrats and 20 of 20 lower-scoring Democrats voted for the bill.</li>
      </ul>
      <p>These are examples of votes with large gaps between Democrats above and below zero on the vertical axis. They suggest a divide between Democrats who more often challenged Senate leadership on these votes and Democrats who more often sided with it. The groups can shift by issue.</p></details>
      <details><summary>Data and methodology</summary><p>W-NOMINATE estimates voting positions from recorded yea and nay votes in 81 official Senate journals. Party affiliation provides the point colors. Jessica de la Cruz and Dawn Euer anchor the directions of the two axes. Uncertainty intervals are unavailable for this fit.</p><p><a href="${sourceLink}">Official Senate journals</a> · <a href="${modelLink}">Model inputs and R code</a></p></details>
      <p><a data-explore href="${explorer}">Open the Senate explorer</a></p>`;
    if (!profile) root.querySelector('[data-explore]').parentElement.remove();
    const response = await fetch(chartUrl);
    if (!response.ok) throw Error('Chart unavailable');
    const parsed = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
    if (parsed.documentElement.localName !== 'svg') throw Error('Chart unavailable');
    const chart = document.importNode(parsed.documentElement, true);
    const plot = root.querySelector('.vp-plot');
    const tooltip = plot.querySelector('.vp-tooltip');
    const select = root.querySelector('select');
    const readout = root.querySelector('.vp-selected');
    const points = [];
    const coords = dot => ['cx', 'cy'].map(key => Number(dot.getAttribute(key)));
    for (const dot of chart.querySelectorAll('circle')) {
      const title = dot.querySelector('title');
      const match = title?.textContent.match(/^(.+) \(([+-][\d.]+), ([+-][\d.]+)\)$/);
      if (!match) continue;
      const [, name, first, second] = match;
      const [x,y] = coords(dot);
      points.push({ name, first, second, x, y });
      title.remove();
    }
    if (!points.length) throw Error('Chart points unavailable');
    points.sort((a,b) => a.name.localeCompare(b.name));
    const byName = new Map(points.map(point => [point.name, point]));
    const initial = byName.get(profile ? candidate : candidateParam || candidate);
    const unavailable = root.querySelector('[data-unscored]');
    if (candidate && !byName.has(candidate) && profile) {
      unavailable.textContent = `No W-NOMINATE estimate is available for ${candidate} in this Senate roll-call sample. Explore the modeled senators below.`;
      unavailable.hidden = false;
    }
    select.add(new Option('Select a senator', ''));
    for (const point of points) select.add(new Option(point.name, point.name));
    chart.style.cssText = 'display:block;width:100%;height:auto;cursor:crosshair';
    chart.removeAttribute('aria-labelledby');
    chart.setAttribute('aria-label', 'Senate voting positions. Use the senator menu to explore every point.');
    const ring = document.createElementNS(chart.namespaceURI, 'circle');
    for (const [key,value] of Object.entries({r:9,fill:'none',stroke:'#14213d','stroke-width':2.5,'pointer-events':'none'})) ring.setAttribute(key,value);
    chart.append(ring);
    plot.prepend(chart);

    const shortScores = point => `Dimension 1 ${point.first} · Dimension 2 ${point.second}`;
    function highlight(point) {
      ring.setAttribute('visibility', point ? 'visible' : 'hidden');
      if (point) {
        ring.setAttribute('cx', point.x);
        ring.setAttribute('cy', point.y);
      }
    }
    function choose(point) {
      select.value = point?.name || '';
      readout.hidden = !point;
      readout.textContent = point ? `${point.name} · ${shortScores(point)}` : '';
      highlight(point);
    }
    function nearest(event) {
      const bounds = chart.getBoundingClientRect();
      let best, distance = event.pointerType === 'touch' ? 25 : 18;
      for (const point of points) {
        const gap = Math.hypot(event.clientX - bounds.left - point.x * bounds.width / 600,
          event.clientY - bounds.top - point.y * bounds.height / 425);
        if (gap < distance) { best = point; distance = gap; }
      }
      return best;
    }
    function showTooltip(point) {
      highlight(point);
      tooltip.querySelector('strong').textContent = point.name;
      tooltip.querySelector('span').textContent = shortScores(point);
      tooltip.hidden = false;
      const bounds = chart.getBoundingClientRect();
      const left = point.x * bounds.width / 600;
      const top = point.y * bounds.height / 425;
      tooltip.style.left = Math.max(0, Math.min(left + 12, bounds.width - tooltip.offsetWidth)) + 'px';
      tooltip.style.top = Math.max(0, top - tooltip.offsetHeight - 9) + 'px';
    }
    function clearTooltip() {
      tooltip.hidden = true;
      highlight(byName.get(select.value));
    }
    chart.addEventListener('pointermove', event => {
      if (event.pointerType === 'touch') return;
      const point = nearest(event);
      if (point) showTooltip(point); else clearTooltip();
    });
    chart.addEventListener('pointerleave', clearTooltip);
    chart.addEventListener('click', event => {
      const point = nearest(event);
      if (point) { choose(point); showTooltip(point); }
    });
    select.addEventListener('change', () => {
      const point = byName.get(select.value);
      choose(point);
      if (point) showTooltip(point); else clearTooltip();
    });
    choose(initial);
  }

  document.querySelectorAll('[data-voting-widget]').forEach(root => init(root).catch(error => {
    const plot = root.querySelector('.vp-plot');
    if (plot) {
      const link = document.createElement('a');
      link.href = chartUrl;
      link.textContent = 'Open the Senate voting chart';
      plot.replaceChildren(link);
    }
    root.querySelector('.vp-controls')?.remove();
    console.error(error);
  }));
})();
