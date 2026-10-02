/* Same equal-weight three-stage calculation used for Edwards; Senate peers only. */
(async function () {
  const scoreNode = document.getElementById('riep-progress-score');
  const rankNode = document.getElementById('riep-progress-rank');
  const stages = ['prime_sponsored', 'passed_chamber', 'became_law'];
  try {
    const response = await fetch('../data/incumbent_records_2026.json');
    if (!response.ok) throw new Error('Dataset unavailable');
    const data = await response.json();
    const peers = data.records.filter(r => String(r.chamber).toLowerCase() === 'senate');
    const districts = new Set(peers.map(r => Number(r.district_number)));
    const valid = peers.length === 38 && districts.size === 38 &&
      peers.every(r => Number.isInteger(Number(r.district_number)) && Number(r.district_number) >= 1 && Number(r.district_number) <= 38 &&
        stages.every(k => Number.isInteger(r.legislation?.[k]) && r.legislation[k] >= 0));
    if (!valid) throw new Error('Incomplete Senate comparison');
    const totals = stages.map(k => peers.reduce((sum, r) => sum + r.legislation[k], 0));
    if (totals.some(t => t === 0)) throw new Error('Missing stage totals');
    const calculate = r => peers.length / stages.length * stages.reduce((sum, k, i) => sum + r.legislation[k] / totals[i], 0);
    const burke = peers.find(r => Number(r.district_number) === 9 && /\bburke\b/i.test(r.candidate_name));
    if (!burke) throw new Error('Burke record missing');
    const score = calculate(burke);
    const rank = 1 + peers.filter(r => calculate(r) > score).length;
    scoreNode.textContent = score.toFixed(2);
    rankNode.textContent = `#${rank} of ${peers.length} Senate district records`;
    const labels = ['Lead-sponsored', 'Passed Senate', 'Became law'];
    const metrics = document.getElementById('riep-progress-metrics');
    stages.forEach((k, i) => {
      const cell = document.createElement('div');
      const count = document.createElement('strong');
      count.textContent = burke.legislation[k];
      const label = document.createElement('span');
      label.textContent = labels[i];
      cell.append(count, label);
      metrics.append(cell);
    });
    document.getElementById('riep-progress-formula').textContent =
      `38 ÷ 3 × (${stages.map((k, i) => `${burke.legislation[k]} ÷ ${totals[i]}`).join(' + ')}) = ${score.toFixed(6)} (displayed as ${score.toFixed(2)}).`;
    document.getElementById('riep-progress-date').textContent = `Dataset updated: ${data.updated_at || 'not specified'}. Counts reflect this dataset, not a live legislative feed.`;
  } catch (error) {
    scoreNode.textContent = 'Unavailable';
    rankNode.textContent = 'Calculation withheld until all 38 Senate records are available and valid.';
  }
})();
