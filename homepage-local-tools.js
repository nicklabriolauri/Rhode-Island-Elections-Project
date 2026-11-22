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
  const track=strip.querySelector('.riep-ticker-track');
  const group=strip.querySelector('.riep-ticker-group');
  const pause=strip.querySelector('[data-update-pause]');
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  let paused=reduced.matches;
  const copy=group.cloneNode(true);
  copy.setAttribute('aria-hidden','true');
  copy.querySelectorAll('a').forEach(a=>a.setAttribute('tabindex','-1'));
  track.appendChild(copy);
  function sync(){
    strip.classList.toggle('is-paused',paused);
    pause.textContent=paused?'Play':'Pause';
    pause.setAttribute('aria-label',paused?'Play scrolling updates':'Pause scrolling updates');
    pause.setAttribute('aria-pressed',String(paused));
  }
  pause.addEventListener('click',()=>{paused=!paused;sync();});
  reduced.addEventListener('change',event=>{paused=event.matches;sync();});
  strip.classList.add('ticker-ready');
  sync();
})();

