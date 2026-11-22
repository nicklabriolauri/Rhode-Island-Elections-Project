/* Progressive enhancement: every measure and source is in the static HTML. */
(() => {
  const member = document.getElementById('sponsorship-member');
  const role = document.getElementById('sponsorship-role');
  const category = document.getElementById('sponsorship-category');
  if (!member || !role || !category) return;
  const items = Array.from(document.querySelectorAll('#sponsorship-results > article'));
  const initial = new URLSearchParams(window.location.search).get('member');
  if (Array.from(member.options).some(option => option.value === initial)) member.value = initial;
  function update() {
    let count = 0;
    for (const item of items) {
      const sponsors = item.dataset.sponsors.split(' ');
      const cosponsors = item.dataset.cosponsors.split(' ');
      const people = role.value === 'sponsors' ? sponsors : role.value === 'cosponsors' ? cosponsors : sponsors.concat(cosponsors);
      const visible = (!member.value || people.includes(member.value)) && (!category.value || item.dataset.category === category.value);
      item.hidden = !visible;
      if (visible) count++;
    }
    document.getElementById('sponsorship-count').textContent = `${count} identified measure${count === 1 ? '' : 's'} match these filters`;
  }
  for (const control of [member, role, category]) control.addEventListener('change', update);
  document.getElementById('sponsorship-filters').hidden = false;
  update();
})();
