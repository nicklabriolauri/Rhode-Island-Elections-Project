(() => {
  const dialog = document.getElementById('aclu-votes-dialog');
  const trigger = document.getElementById('aclu-votes-open');
  if (!dialog || !trigger) return;
  trigger.addEventListener('click', () => dialog.showModal());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
})();

// Shared acknowledgment for desktop profiles and the mobile candidate view.
(() => {
  if (window.RIEPPartnershipCredit) return;
  function create() {
    const credit = document.createElement('p');
    credit.className = 'riep-partnership-credit';
    credit.style.margin = '16px 0 0';
    credit.style.fontSize = '14px';
    credit.style.lineHeight = '1.6';
    credit.append('This work is supported in partnership with the ');
    const link = document.createElement('a');
    link.textContent = 'Elections Officials Communications Tracker';
    link.href = 'https://www.junkipedia.org/dashboards_pro/public/2026-eos-communications-tracker';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.style.color = 'inherit';
    link.style.textDecoration = 'underline';
    credit.append(link, ' (Thessalia Merivaki and Mara Suttmann-Lea).');
    return credit;
  }
  window.RIEPPartnershipCredit = {create};
  if (location.pathname.startsWith('/candidates/') && !document.querySelector('.riep-partnership-credit')) {
    const footer = document.querySelector('footer .shell') || document.querySelector('footer') || document.querySelector('main');
    if (footer) footer.append(create());
  }
})();

// Share the same attributed 2026 results used in search and the mobile guide.
(() => {
  if (window.RIEPResults2026 || document.querySelector('script[src*="election-results-2026.js"]')) return;
  const script = document.createElement('script');
  script.src = '/election-results-2026.js?v=20261119';
  document.head.append(script);
})();
