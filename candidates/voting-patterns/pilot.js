(() => {
  const house = document.currentScript.dataset.chamber === 'house';
  const chamber = house ? 'House' : 'Senate';
  const member = house ? 'representative' : 'senator';
  const assets = new URL(house ? '../house-voting-patterns/' : '.', document.currentScript.src);
  const explorer = new URL('index.html', assets);
  const chartUrl = new URL(house ? 'two-dimensional.svg?v=rollout' : 'senate-two-dimensional.svg?v=groups', assets);
  const candidateParam = new URLSearchParams(location.search).get('candidate');
  const sourceLink = house ? 'https://www.rilegislature.gov/journals/housejournals/SitePages/HouseJournals.aspx' : 'https://www.rilegislature.gov/journals/senatejournals/SitePages/senateJournals.aspx';
  const modelLink = 'https://github.com/nicklabriolauri/Rhode-Island-Elections-Project/tree/main/analysis/' + (house ? 'house-voting-patterns' : 'senate-two-dimensional-preview');

  async function init(root) {
    const candidate = root.dataset.candidate;
    const profile = root.dataset.compact === 'true';
    const section = root.closest('#voting-patterns');
    if (section) {
      const heading = document.createElement('h2');
      heading.textContent = chamber + ' voting patterns · W-NOMINATE';
      section.replaceChildren(heading, root);
    }
    root.innerHTML = `
      <p>2025–2026 Rhode Island ${chamber} · ${house ? 450 : 358} divided roll calls through June 11, 2026</p>
      <p data-unscored hidden></p>
      <div class="vp-controls"><label>Explore a ${member}<select></select></label></div>
      <p>Hover near a dot for its name and scores. Click, tap, or use the menu to select a ${member}.</p>
      <div class="vp-plot"><div class="vp-tooltip" aria-hidden="true" hidden><strong></strong><span></span></div></div>
      <p class="vp-selected" aria-live="polite"></p>
      ${house && !profile ? '<p><a data-member-profile hidden>Open selected representative’s profile</a></p>' : ""}
      <dl>
        <dt><strong>Dimension 1 · Between-party alignment</strong></dt>
        <dd>The horizontal axis captures the strongest voting divide in this ${chamber} sample. Democrats generally fall to the left and Republicans generally fall to the right. Coordinates indicate voting positions on a fitted scale.</dd>
        <dt><strong>Dimension 2 · Within-party divides</strong></dt>
        <dd>The vertical axis captures a secondary voting pattern. Senators with similar horizontal scores can still vote differently. Positive and negative positions indicate different patterns, and the direction depends on the model’s anchor.</dd>
      </dl>
      ${house ? `<p>Light outlines mark Republicans and Democrats above and below zero on Dimension 2. The groups differ sharply on some votes, but both Democratic groups agreed with Christopher Blazejewski on about 96% of votes they cast in common in this sample, averaging across members and excluding Blazejewski and Joseph Shekarchi. The group labels describe chart positions.</p>
      <details><summary>Where House Democrats split</summary><ul>
      <li><a href="https://www.rilegislature.gov/journals/housejournals/2025%20House%20Journals/06-20-2025.pdf#page=31">Self-storage bill amendment</a>: 17 of 18 higher-scoring Democrats and 6 of 35 lower-scoring Democrats voted yes.</li>
      <li><a href="https://www.rilegislature.gov/journals/housejournals/2025%20House%20Journals/04-24-2025.pdf#page=6">Aggressive driving bill</a>: 6 of 19 higher-scoring Democrats and 31 of 32 lower-scoring Democrats voted yes.</li>
      </ul></details>` : `<details open><summary>Where Senate Democrats split</summary>
      <p>The shaded outlines label the two Democratic clusters by their relationship to Senate leadership on the example votes below. These are descriptive labels for these voting patterns. Leonidas Raptakis sits apart from the two visible Democratic clusters and is counted with the lower-scoring Democrats in the vote totals.</p>
      <ul>
        <li><a href="https://www.rilegislature.gov/journals/senatejournals/2025%20Senate%20Journals/06-10-2025.pdf#page=25">Nuclear power purchases, June 2025</a>: 0 of 13 higher-scoring Democrats voted yes, compared with 19 of 19 lower-scoring Democrats who voted.</li>
        <li><a href="https://www.rilegislature.gov/journals/senatejournals/2026%20Senate%20Journals/SJ%2006-09-2026.pdf#page=6">Limits on utility profits, June 2026</a>: 12 of 14 higher-scoring Democrats and 0 of 20 lower-scoring Democrats voted for the amendment.</li>
        <li><a href="https://www.rilegislature.gov/journals/senatejournals/2026%20Senate%20Journals/SJ%2006-11-2026.pdf#page=24">Use of force to resist lawful orders in prison, June 2026</a>: 1 of 14 higher-scoring Democrats and 20 of 20 lower-scoring Democrats voted for the bill.</li>
      </ul>
      <p>These are examples of votes with large gaps between Democrats above and below zero on the vertical axis. They suggest a divide between Democrats who more often challenged Senate leadership on these votes and Democrats who more often sided with it. The groups can shift by issue.</p></details>`}
      <details><summary>Data and methodology</summary><p>W-NOMINATE estimates voting positions from recorded yea and nay votes in ${house ? 91 : 81} official ${chamber} journals. Party affiliation provides the point colors. ${house ? "Michael Chippendale and Kathleen Fogarty" : "Jessica de la Cruz and Dawn Euer"} anchor the directions of the two axes. Uncertainty intervals are unavailable for this fit.</p><p><a href="${sourceLink}">Official ${chamber} journals</a> · <a href="${modelLink}">Model inputs and R code</a></p></details>
      <p><a data-explore href="${explorer}">Open the ${chamber} explorer</a></p>`;
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
      unavailable.textContent = `No W-NOMINATE estimate is available for ${candidate} in this ${chamber} roll-call sample. Explore the modeled members below.`;
      unavailable.hidden = false;
    }
    select.add(new Option(`Select a ${member}`, ''));
    for (const point of points) select.add(new Option(point.name, point.name));
    chart.style.cssText = 'display:block;width:100%;height:auto;cursor:crosshair';
    chart.removeAttribute('aria-labelledby');
    chart.setAttribute('aria-label', `${chamber} voting positions. Use the member menu to explore every point.`);
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
      if (house && !profile) {
        const link = root.querySelector('[data-member-profile]');
        link.hidden = !point;
        if (point) {
          const slug = point.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
          link.href = new URL('../' + slug + '.html#voting-patterns', assets);
        }
      }
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
      link.textContent = `Open the ${chamber} voting chart`;
      plot.replaceChildren(link);
    }
    root.querySelector('.vp-controls')?.remove();
    console.error(error);
  }));
})();
