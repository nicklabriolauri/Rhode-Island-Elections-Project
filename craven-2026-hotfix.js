(() => {
  const clean = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const isCravenJrText = s => {
    const t = clean(s);
    return t.includes('robert') && t.includes('craven') && (t.includes(' jr') || t.includes('junior'));
  };

  function removeCravenMisattribution(root=document) {
    if (!root.querySelectorAll) return;

    // Homepage/search card: remove the father's incumbency and 2024 result from Jr.
    root.querySelectorAll('.hero-search-match').forEach(card => {
      if (!isCravenJrText(card.querySelector('.hero-search-match-name')?.textContent)) return;
      card.querySelectorAll('.riep-search-status').forEach(n => {
        if (/incumbent/i.test(n.textContent || '')) n.remove();
      });
      [...card.querySelectorAll('*')].forEach(n => {
        const txt = (n.textContent || '').trim();
        if (/^INCUMBENT$/i.test(txt)) n.remove();
      });
      card.querySelectorAll('.hero-search-result-card').forEach(n => {
        if (/2024 candidate performance|won in 2024|6,606|95\.2%/i.test(n.textContent || '')) n.remove();
      });
    });

    // Races & Candidates page: locate the current District 32 candidate panel by Jr.'s name.
    const nameNodes = [...root.querySelectorAll('h1,h2,h3,h4,.candidate-name,[data-candidate-name]')]
      .filter(n => isCravenJrText(n.textContent));
    nameNodes.forEach(nameNode => {
      let box = nameNode.closest('.candidate-card,.candidate-panel,.candidate-detail,.candidate-profile,article');
      if (!box) box = nameNode.parentElement;
      if (!box) return;

      // Remove any incumbent badge attached to Jr.
      [...box.querySelectorAll('*')].forEach(n => {
        if (/^INCUMBENT$/i.test((n.textContent || '').trim())) n.remove();
      });

      // Remove the entire inherited legislative-record block, regardless of its CSS class.
      [...box.querySelectorAll('*')].forEach(n => {
        const txt = (n.textContent || '').trim();
        if (/^RECORD IN OFFICE\s*[:·]?\s*2025.?2026 GENERAL ASSEMBLY/i.test(txt) || /^RECORD IN OFFICE$/i.test(txt)) {
          let section = n;
          while (section.parentElement && section.parentElement !== box && !/^(SECTION|ARTICLE)$/i.test(section.tagName)) section = section.parentElement;
          if (section !== box) section.remove();
        }
      });
    });
  }

  function dedupeEndorsements(root=document) {
    if (!root.querySelectorAll) return;
    // Endorsement pills/links are grouped under a section headed ENDORSEMENTS. Deduplicate by visible organization name.
    [...root.querySelectorAll('h2,h3,h4,h5,.section-label,.eyebrow')].forEach(h => {
      if (!/^ENDORSEMENTS$/i.test((h.textContent || '').trim())) return;
      const section = h.parentElement;
      if (!section) return;
      const seen = new Set();
      [...section.querySelectorAll('a,button,.endorsement,.endorsement-pill,.tag,.pill')].forEach(el => {
        const key = clean(el.textContent);
        if (!key || key === 'endorsements') return;
        if (seen.has(key)) el.remove(); else seen.add(key);
      });
    });
  }

  function apply(){ removeCravenMisattribution(document); dedupeEndorsements(document); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply); else apply();
  [100,300,700,1400,2500].forEach(ms => setTimeout(apply, ms));
  document.addEventListener('input', () => setTimeout(apply, 50), true);
  document.addEventListener('click', () => setTimeout(apply, 100), true);
})();
