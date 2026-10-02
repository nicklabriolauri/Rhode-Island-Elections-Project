(() => {
  const dialog = document.getElementById('aclu-votes-dialog');
  const trigger = document.getElementById('aclu-votes-open');
  if (!dialog || !trigger) return;
  trigger.addEventListener('click', () => dialog.showModal());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
})();
