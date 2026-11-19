/* Official vote snapshot + separately attributed race calls. Shared by search and profiles. */
(() => {
  'use strict';
  if (window.RIEPResults2026) return;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');
  let snapshot, roster;
  const style = document.createElement('link');
  style.rel = 'stylesheet'; style.href = '/election-results-2026.css?v=20261119'; document.head.append(style);
  const ready = Promise.all(['/data/general_results_2026.json','/data/candidate_results_2026.json'].map(async url => {
    const response = await fetch(url, {cache:'no-store'});
    if (!response.ok) throw Error('2026 election results are temporarily unavailable.');
    return response.json();
  })).then(([results, index]) => { snapshot = results; roster = index.candidates; });
  // Keep the rest of each page usable if results cannot load.
  ready.catch(() => {});
  function record(candidate) {
    if (!roster) return null;
    const slug = typeof candidate === 'string' ? candidate.split('/').pop().replace(/\.html(?:\?.*)?$/, '') : candidate.slug || (candidate.profile || candidate.profile_url || '').split('/').pop().replace(/\.html$/, '');
    if (slug) { const exact = roster.find(c => c.slug === slug); if (exact) return exact; }
    if (typeof candidate === 'string') return null;
    return roster.find(c => c.chamber === candidate.chamber && Number(c.district) === Number(candidate.district ?? candidate.district_number) && normalize(c.name) === normalize(candidate.name)) || null;
  }
  const race = (chamber, district) => snapshot?.races.find(r => r.chamber === chamber && r.district === Number(district));
  const href = r => `/general-results.html?chamber=${r.chamber}&district=${r.district}`;
  function outcome(c, r) {
    if (!c.source_id) return 'Not on general-election ballot';
    const official = r.candidates.find(x => x.source_id === c.source_id);
    const leader = official?.name === r.leader_name;
    if (r.status === 'winner') return leader ? (r.call_source ? 'Won · DDHQ call' : 'Won') : 'Not elected';
    if (r.is_unopposed && leader) return 'Unopposed · elected';
    if (r.status === 'tied') return 'Result unresolved';
    return leader ? 'Leading · unofficial' : 'Trailing · unofficial';
  }
  function badge(candidate, link = true) {
    const c = record(candidate); if (!c) return '';
    const r = race(c.chamber, c.district); if (!r) return '';
    const official = r.candidates.find(x => x.source_id === c.source_id);
    const label = `2026: ${outcome(c,r)}${official ? ` · ${official.pct === null ? '—' : official.pct.toFixed(1)+'%'}` : ''}`;
    const cls = official?.name === r.leader_name ? ' elected' : '';
    return link ? `<a class="riep-result-badge${cls}" href="${href(r)}">${esc(label)} →</a>` : `<span class="riep-result-badge${cls}">${esc(label)}</span>`;
  }
  function section(candidate) {
    const c = record(candidate); if (!c) return '';
    const r = race(c.chamber, c.district); if (!r) return '';
    const sourceDate = new Date(snapshot.source_as_of).toLocaleString('en-US', {timeZone:'America/New_York',month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
    return `<section class="riep-election-result" id="election-results-2026" aria-labelledby="result2026Heading"><h2 id="result2026Heading">2026 general election</h2>${badge(c,false)}<div class="riep-results-scroll"><table><thead><tr><th scope="col">Candidate</th><th scope="col">Votes</th><th scope="col">Share</th></tr></thead><tbody>${r.candidates.map(x => `<tr${x.source_id === c.source_id ? ' class="selected-candidate"' : ''}><th scope="row">${esc(x.name)}${x.is_write_in ? '' : ` (${esc(x.party)})`}${x.name === r.leader_name && (r.status === 'winner' || r.is_unopposed) ? ' · Winner' : ''}</th><td>${x.votes.toLocaleString('en-US')}</td><td>${x.pct === null ? '—' : x.pct.toFixed(1)+'%'}</td></tr>`).join('')}</tbody></table></div><p class="riep-result-note">${snapshot.is_official ? 'Certified' : 'Unofficial'} vote totals as of ${esc(sourceDate)}. Shares include write-ins.${r.call_source ? ` Winner called by <a href="${esc(r.call_source_url)}" target="_blank" rel="noopener noreferrer">Decision Desk HQ</a>; a call is not certification.` : r.is_unopposed ? ' One named ballot candidate; write-ins are included.' : ''} Election outcomes do not indicate that a new term has begun.</p><p><a href="${href(r)}">View this district’s 2026 results and map →</a> · <a href="${esc(r.source_url)}" target="_blank" rel="noopener noreferrer">State election returns ↗</a></p></section>`;
  }
  function district(chamber,district) {
    const r = race(chamber,district); if (!r) return '';
    return `<p class="riep-district-result"><a href="${href(r)}"><strong>2026: ${esc(r.leader_name || 'No leader')}</strong> · ${r.status === 'winner' ? 'Won · DDHQ call' : r.is_unopposed ? 'Unopposed · elected' : 'Leading · unofficial'} →</a></p>`;
  }
  window.RIEPResults2026 = {ready,record,race,badge,section,district};
  ready.then(() => {
    if (/^\/candidates\/[^/]+\.html$/.test(location.pathname)) {
      const html = section(location.pathname); if (!html || document.getElementById('election-results-2026')) return;
      const target = document.getElementById('elections');
      if (target) target.querySelectorAll('p').forEach(p => {
        p.innerHTML = p.innerHTML.replace(' The 2026 general election has not occurred.', ' See the 2026 general-election results above.');
      });
      if (target) target.insertAdjacentHTML('beforebegin',html);
      else (document.querySelector('main .stack') || document.querySelector('main'))?.insertAdjacentHTML('afterbegin',html);
    }
    document.querySelectorAll('a.profile-card').forEach(card => {
      card.insertAdjacentHTML('beforeend',badge(card.getAttribute('href'),false));
    });
  }).catch(() => {});
})();
