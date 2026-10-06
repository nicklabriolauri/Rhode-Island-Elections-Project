const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const html = fs.readFileSync('candidate-profiles.html', 'utf8');
const cards = [...html.matchAll(/<a class="profile-card" href="([^"]+)" data-search="([^"]+)" data-chamber="([^"]+)" data-party="([^"]+)"/g)].map(m => {
  assert(fs.existsSync(m[1]), m[1]);
  return {dataset: {search:m[2], chamber:m[3], party:m[4]}, hidden:false};
});
assert.equal(cards.length,63);
const fields = {};
['profile-search','profile-chamber','profile-party','profile-count','profile-empty'].forEach(id => fields[id]={value:'',addEventListener(event,cb){this[event]=cb;}});
const form={addEventListener(event,cb){this[event]=cb;}};
fields['profile-search'].closest=()=>form;
vm.runInNewContext(fs.readFileSync('candidate-profiles.js','utf8'),{document:{querySelectorAll:()=>cards,getElementById:id=>fields[id]},setTimeout:cb=>cb()});
const visible=()=>cards.filter(c=>!c.hidden).length;
fields['profile-search'].value='Victoria Gu';fields['profile-search'].input();assert.equal(visible(),1);
fields['profile-search'].value='';fields['profile-chamber'].value='house';fields['profile-chamber'].change();assert.equal(visible(),22);
fields['profile-party'].value='REP';fields['profile-party'].change();assert.equal(visible(),3);
fields['profile-search'].value='no such person';fields['profile-search'].input();assert.equal(visible(),0);assert.equal(fields['profile-empty'].hidden,false);
for(const id of ['profile-search','profile-chamber','profile-party'])fields[id].value='';form.reset();assert.equal(visible(),63);
assert.equal((html.match(/<span>Incumbent<\/span>/g)||[]).length,54); // 38 Senate and 16 House incumbents.
console.log('PASS: 63 existing profile destinations, search, chamber/party filters, empty state and reset');
