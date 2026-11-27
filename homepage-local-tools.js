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
})();
