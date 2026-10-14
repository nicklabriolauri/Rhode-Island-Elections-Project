/* Full mobile profiles use the published candidate page as their source. */
(() => {
'use strict';
const cache = new Map();
function safeURL(value, base) {
  try {
    const url = new URL(value, base);
    return ['http:', 'https:', 'mailto:', 'tel:'].includes(url.protocol) ? url.href : null;
  } catch (_) { return null; }
}
function clean(root, base) {
  root.querySelectorAll('script,style,link,meta,object,embed,form,input,button').forEach(el => el.remove());
  root.querySelectorAll('iframe').forEach(el => {
    const href = safeURL(el.getAttribute('src'), base);
    const link = document.createElement('a');
    link.textContent = 'Open ' + (el.getAttribute('title') || 'source document') + ' ↗';
    if (href) link.href = href;
    el.replaceWith(link);
  });
  for (const el of [root, ...root.querySelectorAll('*')]) {
    for (const attr of [...el.attributes]) {
      if (/^on/i.test(attr.name) || ['style','srcdoc'].includes(attr.name)) el.removeAttribute(attr.name);
    }
    for (const attr of ['href', 'src']) {
      if (!el.hasAttribute(attr)) continue;
      const value = el.getAttribute(attr);
      // Keep local section anchors within the mobile profile.
      const href = attr === 'href' && value.startsWith('#') ? value : safeURL(value, base);
      if (href) el.setAttribute(attr, href); else el.removeAttribute(attr);
    }
    if (el.tagName === 'A' && el.getAttribute('target') === '_blank') el.setAttribute('rel','noopener noreferrer');
    if (el.tagName === 'IMG') el.setAttribute('loading','lazy');
  }
  root.querySelectorAll('table').forEach(table => {
    if (!table.parentElement.classList.contains('table-scroll')) {
      const wrap = document.createElement('div'); wrap.className = 'table-scroll';
      table.replaceWith(wrap); wrap.append(table);
    }
  });
}
function sections(html, c) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const main = doc.querySelector('main');
  if (!main) throw Error('Profile sections are unavailable.');
  // ACLU vote records normally open in a desktop dialog. Make them an inline foldout.
  doc.querySelectorAll('dialog').forEach(dialog => {
    const details = doc.createElement('details');
    details.className = 'mobile-vote-record';
    const summary = doc.createElement('summary');
    summary.textContent = 'Read the individual scorecard votes';
    details.append(summary);
    for (const child of [...dialog.children]) details.append(child.cloneNode(true));
    const scorecards = dialog.closest('section') || main.querySelector('#ratings, #scorecards') || main.querySelector('.scorecard-grid')?.closest('section');
    if (scorecards) scorecards.append(details);
    dialog.remove();
  });
  const base = new URL(c.profile, location.origin).href;
  return [...main.querySelectorAll('section')].filter(el =>
    !el.parentElement.closest('section') && el.querySelector('h2') && el.id !== 'finance' && !el.hidden
  ).map((el, i) => {
    const title = el.querySelector('h2').textContent.trim();
    const id = el.id || 'profile-section-' + i;
    el.querySelector('h2').remove();
    clean(el, base);
    return {id, title, html:el.innerHTML, open:['about','priorities'].includes(id)};
  });
}
async function load(c, target) {
  if (!c.profile) return;
  try {
    let html = cache.get(c.profile);
    if (!html) {
      const response = await fetch(c.profile);
      if (!response.ok) throw Error('Profile could not load.');
      html = await response.text(); cache.set(c.profile, html);
    }
    if (!target.isConnected) return;
    const rows = sections(html, c);
    const fragment = document.createDocumentFragment();
    const tools = document.createElement('div'); tools.className = 'profile-tools';
    const note = document.createElement('p'); note.className = 'note';
    note.textContent = 'The same published information as the full profile. Tap a section to read it.';
    const expand = document.createElement('button'); expand.className = 'secondary';
    expand.type = 'button'; expand.textContent = rows.every(row => row.open) ? 'Collapse all sections' : 'Expand all sections';
    tools.append(note, expand); fragment.append(tools);
    for (const row of rows) {
      const fold = document.createElement('details'); fold.className = 'profile-section';
      fold.id = row.id; fold.open = row.open;
      const summary = document.createElement('summary'); summary.textContent = row.title;
      const content = document.createElement('div'); content.className = 'profile-content'; content.innerHTML = row.html;
      fold.append(summary, content); fragment.append(fold);
    }
    target.replaceChildren(fragment);
    expand.addEventListener('click', () => {
      const folds = [...target.querySelectorAll(':scope > details')];
      const opening = folds.some(f => !f.open);
      folds.forEach(f => f.open = opening);
      expand.textContent = opening ? 'Collapse all sections' : 'Expand all sections';
    });
    // Only the site's two vetted voting widgets execute; source-page scripts never do.
    if (target.querySelector('[data-voting-widget]')) {
      const script = document.createElement('script');
      script.src = c.chamber === 'house' ? '/candidates/house-voting-patterns/pilot.js?v=20261014-mobile' : '/candidates/voting-patterns/pilot.js?v=20261014-mobile';
      script.onload = script.onerror = () => script.remove();
      document.head.append(script);
    }
  } catch (_) {
    if (!target.isConnected) return;
    const notice = document.createElement('p'); notice.className = 'notice';
    notice.textContent = 'The remaining profile sections could not load. You can retry or open the full profile above.';
    const retry = document.createElement('button'); retry.className = 'secondary'; retry.textContent = 'Retry loading profile';
    retry.onclick = () => { notice.remove(); retry.remove(); load(c,target); };
    target.prepend(notice,retry);
  }
}
window.RIEPMobileProfile = {load};
})();
