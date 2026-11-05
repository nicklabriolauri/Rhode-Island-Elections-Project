/* Dated official-source snapshot. A lead is never promoted to a race call. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const names = {DEM:'Democratic', REP:'Republican', IND:'Independent', SOC:'Socialist', LIB:'Libertarian', FAN:'For All Neighbors', UNASSIGNED:'Unassigned', OTHER:'Other'};
  const colors = {DEM:'#255c99', REP:'#b92335', IND:'#9b7416', OTHER:'#7a8491'};
  const partyClass = p => ({DEM:'dem', REP:'rep', IND:'ind'}[p] || 'other');
  const partyName = p => names[p] || p || 'No lead';
  const votes = n => Number(n).toLocaleString('en-US');
  const pct = n => n === null || n === undefined ? '—' : `${Number(n).toFixed(1)}%`;
  const chamberName = c => c === 'house' ? 'State House' : 'State Senate';
  const params = new URLSearchParams(location.search);
  let chamber = params.get('chamber') === 'senate' ? 'senate' : 'house';
  let selected = Number(params.get('district')) || null;
  let data, geometry, map, districts, request = 0;
  const raceList = () => data.races.filter(r => r.chamber === chamber);
  const statusLabel = r => r.status === 'winner' ? 'Winner' : r.status === 'tied' ? 'Tied' : r.status === 'no-votes' ? 'No votes reported' : r.is_unopposed ? 'Unopposed · leading' : 'Leading';

  function writeUrl() {
    const url = new URL(location.href);
    url.searchParams.set('chamber', chamber);
    if (selected) url.searchParams.set('district', selected); else url.searchParams.delete('district');
    history.replaceState(null, '', url.pathname + url.search + url.hash);
  }

  function renderTotals() {
    $('seatTotals').innerHTML = ['house', 'senate'].map(c => {
      const counts = data.seat_leads[c], total = c === 'house' ? 75 : 38;
      const parties = ['DEM','IND','REP', ...Object.keys(counts).filter(p => !['DEM','IND','REP'].includes(p))];
      const description = parties.map(p => `${counts[p] || 0} ${partyName(p)}`).join(', ');
      return `<article class="seat-summary"><h3>${chamberName(c)}<small>${total} seats · ${c === 'house' ? 38 : 20} for a majority</small></h3><div class="seat-counts">${parties.map(p => `<span class="${partyClass(p)}-text"><b>${counts[p] || 0}</b>${esc(p === 'UNASSIGNED' ? 'Unassigned' : partyName(p))}</span>`).join('')}</div><div class="seat-bar" role="img" aria-label="Current seat leads: ${esc(description)}">${parties.filter(p => counts[p]).map(p => `<span class="${partyClass(p)}" style="width:${100 * counts[p] / total}%"></span>`).join('')}</div></article>`;
    }).join('');
  }

  function renderTable() {
    $('tableHeading').textContent = `${chamberName(chamber)} results`;
    $('resultRows').innerHTML = raceList().map(r => r.candidates.map((c, i) => {
      const leading = r.leader_name === c.name && r.leader_party === c.party;
      return `<tr class="${i === 0 ? 'race-start ' : ''}${leading ? 'leading ' : ''}${selected === r.district ? 'selected-row' : ''}">${i === 0 ? `<td rowspan="${r.candidates.length}"><button type="button" class="district-button" data-district="${r.district}" aria-label="View ${chamberName(chamber)} District ${r.district}">${r.district}</button></td>` : ''}<td><span class="candidate-name">${esc(c.name)}</span>${c.is_write_in ? '' : `<span class="party-tag">${esc(c.party)}</span>`}</td><td class="number">${votes(c.votes)}</td><td class="number">${pct(c.pct)}</td><td class="table-status">${leading ? esc(statusLabel(r)) : r.status === 'tied' && c.votes === r.candidates[0].votes ? 'Tied' : ''}</td></tr>`;
    }).join('')).join('');
  }

  function renderDetail() {
    const r = raceList().find(r => r.district === selected);
    if (!r) {
      selected = null;
      $('districtDetail').innerHTML = '<h3>Select a district</h3><p>Choose a district on the map, in the dropdown, or in the results table to see every candidate’s votes.</p>';
      return;
    }
    const reporting = r.reporting;
    const reportingText = reporting && Number.isFinite(reporting.reportingUnits) && Number.isFinite(reporting.totalUnits) ? `${reporting.reportingUnits} of ${reporting.totalUnits} source reporting units` : 'Reporting-unit count unavailable';
    const change = r.party_change ? `<p class="party-change">Party change in current returns: ${esc(partyName(r.previous_party))} → ${esc(partyName(r.leader_party))}</p>` : '';
    $('districtDetail').innerHTML = `<p class="eyebrow">${chamberName(chamber)}</p><h3>District ${r.district}</h3><span class="race-status">${esc(statusLabel(r))}</span>${change}<div>${r.candidates.map(c => `<div class="candidate-row"><div class="candidate-line"><span><strong>${esc(c.name)}</strong><br><span class="candidate-meta">${esc(c.is_write_in ? 'Write-in' : partyName(c.party))}</span></span><span><strong>${pct(c.pct)}</strong><br>${votes(c.votes)} votes</span></div><div class="vote-bar" aria-hidden="true"><span class="${partyClass(c.party)}" style="width:${c.pct || 0}%"></span></div></div>`).join('')}</div><p class="source-count">${votes(r.total_votes)} total votes · ${esc(reportingText)}<br>Reporting units are not a ballot-count percentage.</p>${!r.is_unopposed && r.margin_votes !== null ? `<p>Lead: <strong>${votes(r.margin_votes)} votes</strong> · ${r.margin_pct.toFixed(1)} percentage points</p>` : ''}<div class="detail-links"><a href="/races/${chamber}-${r.district}.html">Race &amp; candidate profiles ↗</a><a href="${esc(r.source_url)}" target="_blank" rel="noopener">State results ↗</a></div>`;
  }

  function style(feature) {
    const r = raceList().find(r => r.district === Number(feature.properties.district_number));
    return {fillColor: colors[r?.leader_party] || colors.OTHER, fillOpacity: .78, color: Number(feature.properties.district_number) === selected ? '#111c3d' : '#fff', weight: Number(feature.properties.district_number) === selected ? 3 : 1};
  }

  function chooseDistrict(number, focusMap = true) {
    selected = number ? Number(number) : null;
    renderDetail();
    $('district').value = selected ? String(selected) : '';
    renderTable();
    if (districts) {
      districts.setStyle(style);
      if (focusMap) {
        const layer = districts.getLayers().find(l => Number(l.feature.properties.district_number) === selected);
        map.fitBounds(layer ? layer.getBounds() : districts.getBounds(), {padding:[25,25], maxZoom:13, animate:false});
      }
    }
    writeUrl();
  }

  async function renderMap() {
    const current = ++request;
    $('resultsMap').setAttribute('aria-busy','true');
    if (districts) {districts.remove(); districts = null;}
    try {
      if (!window.L) throw new Error('Map library unavailable');
      if (!map) {
        $('mapFallback').remove();
        map = L.map('resultsMap', {scrollWheelZoom:false}).setView([41.68,-71.5],9);
        map.attributionControl.addAttribution('Boundaries: RIEP / U.S. Census via U.S. Atlas');
        fetch('/data/results_map_context.geojson').then(response => {if (!response.ok) throw new Error('Context unavailable'); return response.json();}).then(context => {
          L.geoJSON(context, {interactive:false, style:{color:'#c5cdd6', weight:1, fillColor:'#dfe5ea', fillOpacity:1}}).addTo(map).bringToBack();
        }).catch(error => console.warn(error.message));
      }
      if (!geometry[chamber]) {
        const response = await fetch(`/data/${chamber}_new.geojson`);
        if (!response.ok) throw new Error('District boundaries could not be loaded');
        geometry[chamber] = await response.json();
      }
      if (current !== request) return;
      if (districts) districts.remove();
      districts = L.geoJSON(geometry[chamber], {
        style,
        onEachFeature(feature, layer) {
          const d = Number(feature.properties.district_number);
          const r = raceList().find(r => r.district === d);
          layer.bindTooltip(`<strong>${chamberName(chamber)} District ${d}</strong><br>${esc(r.leader_name || statusLabel(r))}${r.leader_party ? ` (${esc(r.leader_party)})` : ''}<br>${esc(statusLabel(r))}`);
          layer.on('click', () => chooseDistrict(d));
          layer.on('mouseover', () => layer.setStyle({weight:3}));
          layer.on('mouseout', () => layer.setStyle(style(feature)));
        }
      }).addTo(map);
      districts.eachLayer(layer => {
        const el = layer.getElement();
        if (!el) return;
        const d = Number(layer.feature.properties.district_number);
        el.setAttribute('role','button');
        el.setAttribute('tabindex','0');
        el.setAttribute('aria-label', `${chamberName(chamber)} District ${d}. ${raceList().find(r => r.district === d)?.leader_name || 'No leader'}. Select for results.`);
        el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') {e.preventDefault(); chooseDistrict(d);} });
      });
      chooseDistrict(selected);
      $('resultsMap').setAttribute('aria-busy','false');
    } catch (error) {
      if (current !== request) return;
      if (!map) $('resultsMap').textContent = 'The map could not load. All district results remain available in the dropdown and table below.';
      else {
        $('error').hidden = false;
        $('error').textContent = 'District boundaries could not load. Please use the district dropdown or results table.';
      }
      $('resultsMap').setAttribute('aria-busy','false');
      console.error(error);
    }
  }

  function setChamber(next, keepDistrict = false) {
    chamber = next;
    if (!keepDistrict) selected = null;
    document.querySelectorAll('[data-chamber]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.chamber === chamber)));
    $('district').innerHTML = '<option value="">All districts</option>' + raceList().map(r => `<option value="${r.district}">District ${r.district}</option>`).join('');
    renderDetail(); renderTable();
    $('district').value = selected ? String(selected) : '';
    writeUrl();
    renderMap();
  }

  async function init() {
    try {
      const response = await fetch('/data/general_results_2026.json', {cache:'no-cache'});
      if (!response.ok) throw new Error(`Results request returned ${response.status}`);
      data = await response.json();
      if (data.races.length !== 113) throw new Error('Results snapshot is incomplete');
      geometry = {};
      $('resultStatus').textContent = data.is_official ? 'Official results' : 'Unofficial results';
      const asOf = new Date(data.source_as_of).toLocaleString('en-US', {timeZone:'America/New_York', month:'short', day:'numeric', year:'numeric', hour:'numeric', minute:'2-digit', timeZoneName:'short'});
      $('sourceTime').textContent = `State data as of ${asOf}`;
      renderTotals();
      document.querySelectorAll('[data-chamber]').forEach(button => button.addEventListener('click', () => setChamber(button.dataset.chamber)));
      $('district').addEventListener('change', e => chooseDistrict(e.target.value));
      $('resetMap').addEventListener('click', () => chooseDistrict(null));
      $('resultRows').addEventListener('click', e => {const button = e.target.closest('[data-district]'); if (button) {chooseDistrict(button.dataset.district); $('mapHeading').scrollIntoView({block:'start'});} });
      setChamber(chamber, true);
    } catch (error) {
      $('resultStatus').textContent = 'Results unavailable';
      $('error').hidden = false;
      $('error').textContent = 'Results could not be loaded. Please reload this page or use the state source link above.';
      console.error(error);
    }
  }
  init();
})();
