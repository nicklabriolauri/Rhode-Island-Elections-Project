(async () => {
  const panels = document.querySelectorAll('[data-historical-name]');
  const table = document.getElementById('comparison-body');
  if (!panels.length && !table) return;
  const escape = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  try {
    const response = await fetch('../data/legislative_comparison_2023_2024.json');
    if (!response.ok) throw Error('Historical dataset unavailable');
    const data = await response.json();
    for (const panel of panels) {
      const surname = panel.dataset.historicalName.split(' ').pop().toLowerCase();
      const r = data.records.find(r => r.chamber==='senate' && r.name.split(',')[0].toLowerCase()===surname);
      const target = panel.querySelector('.historical-result');
      if (!r) { target.textContent='Not applicable: no 2023–2024 service record for this candidate. This is not a zero score.'; continue; }
      const group=data.chambers[r.chamber];
      target.innerHTML=`<div class="record-grid"><div class="metric"><b>${r.riep_index.toFixed(2)}</b><span>RIEP index · #${r.riep_rank} of ${group.n}</span></div><div class="metric"><b>${r.cel_sles.toFixed(2)}</b><span>CEL SLES · #${r.cel_rank} of ${group.n}</span></div></div><p>Same session, same historical chamber roster. Ranks compare all ${group.n} Senate legislator records, not party-only rankings.</p><details class="profile-fold"><summary>Historical calculation</summary><div class="fold-content"><p>${group.n} ÷ 3 × (${r.introduced} ÷ ${group.totals.introduced} + ${r.passed_chamber} ÷ ${group.totals.passed_chamber} + ${r.became_law} ÷ ${group.totals.became_law}) = ${r.riep_index.toFixed(6)}.</p><p>${escape(data.bill_scope)}</p><p>${escape(data.limitations)}</p></div></details>`;
    }
    if (!table) return;
    const chamber=document.getElementById('comparison-chamber'), search=document.getElementById('comparison-search');
    function render() {
      const rows=data.records.filter(r=>r.chamber===chamber.value), group=data.chambers[chamber.value];
      document.getElementById('comparison-summary').textContent=`${group.n} historical ${chamber.value==='senate'?'Senate':'House'} records · Pearson r = ${group.pearson_r.toFixed(3)} · Spearman ρ = ${group.spearman_rho.toFixed(3)} · Mean absolute rank difference = ${group.mean_absolute_rank_difference.toFixed(2)} places. Stronger correlation means similar ordering, not identical scores or independent validation.`;
      const query=search.value.trim().toLowerCase();
      const matches=r=>r.name.toLowerCase().includes(query);
      const filtered=rows.filter(matches).sort((a,b)=>a.riep_rank-b.riep_rank);
      document.getElementById('comparison-search-status').textContent=query ? `${filtered.length} matching ${filtered.length===1?'legislator':'legislators'}. Matching points are highlighted in gold; other points are faded.` : 'Search a name to highlight it on the chart and filter the table.';
      table.innerHTML=filtered.map(r=>`<tr><th scope="row">${escape(r.name)}</th><td>${r.district}</td><td>${r.party}</td><td>${r.introduced}</td><td>${r.passed_chamber}</td><td>${r.became_law}</td><td>${r.riep_index.toFixed(3)}</td><td>${r.cel_sles.toFixed(3)}</td><td>${r.riep_rank}</td><td>${r.cel_rank}</td><td>${r.rank_difference>0?'+':''}${r.rank_difference}</td></tr>`).join('')||'<tr><td colspan="11">No matching legislators.</td></tr>';
      const max=Math.ceil(Math.max(...rows.map(r=>Math.max(r.riep_index,r.cel_sles)))),scale=340/max;
      document.getElementById('comparison-chart').innerHTML=`<svg class="comparison-chart" viewBox="0 0 500 440" role="img" aria-label="RIEP versus CEL scores for all ${group.n} ${chamber.value} records. Detailed values follow in the table."><path d="M70 30V370H410" fill="none" stroke="#77899c"/><path d="M70 370L410 30" stroke="#b48420" stroke-dasharray="5 5"/><text x="175" y="420">RIEP index (0–${max})</text><text x="10" y="18">CEL SLES (0–${max})</text>${[...rows].sort((a,b)=>Number(matches(a))-Number(matches(b))).map(r=>{const selected=query && matches(r), x=70+r.riep_index*scale, y=370-r.cel_sles*scale; return `<circle cx="${x}" cy="${y}" r="${selected?7:4}" fill="${selected?'#d99b16':'#1c527c'}" opacity="${query&&!selected?0.16:1}" stroke="${selected?'#704b00':'none'}" stroke-width="1.5"><title>${escape(r.name)}: RIEP ${r.riep_index.toFixed(3)}, CEL ${r.cel_sles.toFixed(3)}</title></circle>${selected?`<text x="${x>290?x-12:x+12}" y="${y-12}" text-anchor="${x>290?'end':'start'}" font-size="11" font-weight="700" fill="#704b00" stroke="#fff" stroke-width="3" paint-order="stroke">${escape(r.name)}</text>`:''}`;}).join('')}<text x="65" y="392">0</text><text x="403" y="392">${max}</text><text x="45" y="35">${max}</text></svg>`;
    }
    chamber.addEventListener('change',render);search.addEventListener('input',render);render();
  } catch(error) {
    panels.forEach(p=>p.querySelector('.historical-result').textContent='Historical comparison unavailable. Please try again later.');
    if(table)document.getElementById('comparison-summary').textContent='Historical comparison unavailable. No scores can be displayed.';
  }
})();
