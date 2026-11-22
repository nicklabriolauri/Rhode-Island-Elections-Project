(() => {
  'use strict';
  const dialog = document.getElementById('localMapChooser');
  let opener;
  if (dialog && typeof dialog.showModal === 'function') {
    document.addEventListener('click', event => {
      const trigger = event.target.closest('#homeCtaRow a.maps, [data-open-map-chooser]');
      if (!trigger) return;
      event.preventDefault(); opener = trigger; dialog.showModal();
    });
    dialog.querySelector('[data-close-map-chooser]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) {
      const r=dialog.getBoundingClientRect();
      if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom) dialog.close();
    }});
    dialog.addEventListener('close', () => { if (opener?.isConnected) opener.focus(); });
  }
  const strip = document.getElementById('riepUpdates');
  if (!strip) return;
  const items = [
    {text:'Cranston: nine council profiles, campaign information and 2026 results',url:'/cranston-map.html?colors=returns'},
    {text:'New: council attendance percentages and individually recorded votes',url:'/cranston-records.html'},
    {text:'Explore local wards: Cranston coverage and the Providence map pilot',url:'#local-coverage'},
    {text:'Updated: color-coded Womxn Project ratings on municipal profiles',url:'/candidates/sara-jane-haupt.html#ratings'}
  ];
  let index=0, paused=window.matchMedia('(prefers-reduced-motion: reduce)').matches, hovering=false, focused=false;
  const link=strip.querySelector('[data-update-link]'), pause=strip.querySelector('[data-update-pause]');
  const announce=strip.querySelector('[data-update-status]');
  function show(delta,manual=false) {
    index=(index+delta+items.length)%items.length;
    link.textContent=items[index].text;link.href=items[index].url;
    link.classList.remove('riep-updated');void link.offsetWidth;link.classList.add('riep-updated');
    if(manual) announce.textContent=`Update ${index+1} of ${items.length}: ${items[index].text}`;
  }
  function sync(){pause.textContent=paused?'Play':'Pause';pause.setAttribute('aria-label',paused?'Play rotating updates':'Pause rotating updates');pause.setAttribute('aria-pressed',String(paused));}
  strip.querySelector('[data-update-prev]').addEventListener('click',()=>show(-1,true));
  strip.querySelector('[data-update-next]').addEventListener('click',()=>show(1,true));
  pause.addEventListener('click',()=>{paused=!paused;sync();});
  strip.addEventListener('mouseenter',()=>hovering=true);strip.addEventListener('mouseleave',()=>hovering=false);
  strip.addEventListener('focusin',()=>focused=true);strip.addEventListener('focusout',e=>focused=strip.contains(e.relatedTarget));
  setInterval(()=>{if(!paused&&!hovering&&!focused&&!document.hidden)show(1);},8000);
  sync();
})();
