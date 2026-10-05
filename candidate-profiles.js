(() => {
  const cards = [...document.querySelectorAll('.profile-card')];
  const search = document.getElementById('profile-search');
  const chamber = document.getElementById('profile-chamber');
  const party = document.getElementById('profile-party');
  function update() {
    const terms = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    let count = 0;
    cards.forEach(card => {
      const match = terms.every(term => card.dataset.search.includes(term)) &&
        (!chamber.value || card.dataset.chamber === chamber.value) &&
        (!party.value || card.dataset.party === party.value);
      card.hidden = !match;
      if (match) count++;
    });
    document.getElementById('profile-count').textContent = `Showing ${count} of ${cards.length} profiles`;
    document.getElementById('profile-empty').hidden = count !== 0;
  }
  search.addEventListener('input', update);
  chamber.addEventListener('change', update);
  party.addEventListener('change', update);
  search.closest('form').addEventListener('reset', () => { setTimeout(update, 0); });
})();
