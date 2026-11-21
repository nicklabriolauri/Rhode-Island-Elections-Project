const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const api=require('../local-representation.js');
const registry=JSON.parse(fs.readFileSync('data/local_representatives.json','utf8'));
api.setRegistryForTests(registry);
const precincts=JSON.parse(fs.readFileSync('data/cranston/precincts.geojson','utf8')).features;
for(const f of precincts){const p=f.properties;assert.equal(api.wardFor('Cranston',p.precinct),p.ward);const profiles=api.profilesFor('Cranston',p.precinct);assert.equal(profiles.length,p.ward===2?1:0);if(p.ward===2)assert.equal(profiles[0].name,'Sara Jane Haupt');}
assert.equal(api.profilesFor('Providence','0724').length,0);assert.equal(api.profilesFor('Cranston','9999').length,0);assert.equal(api.profilesFor('Cranston','2-1').length,0);assert.equal(api.profilesFor('Cranston',724).length,1);
const html=fs.readFileSync('index.html','utf8');
function extract(name){const start=html.indexOf(`    function ${name}(`);assert(start>=0);const end=html.indexOf('\n    function ',start+5);return html.slice(start,end);}
const el={};const ctx={window:{RIEPLocalRepresentation:api},document:{getElementById:()=>el},escapeHtml:s=>String(s),URLSearchParams,encodeURIComponent,buildDistrictResultCard:()=>'',buildAddressCandidateGroup:(c,d)=>`<section>${c} district ${d}</section>`};vm.createContext(ctx);vm.runInContext(extract('renderAddressSearchResult'),ctx);
for(const f of precincts){const p=f.properties;ctx.renderAddressSearchResult('public test',{address:'public test'},{municipality:'Cranston',precinct_code:p.precinct,house_district:p.house,senate_district:p.senate});assert(el.innerHTML.includes(`house district ${p.house}`));assert(el.innerHTML.includes(`senate district ${p.senate}`));assert.equal(el.innerHTML.includes('/candidates/sara-jane-haupt.html'),p.ward===2);}
ctx.renderAddressSearchResult('',{}, {municipality:'Providence',precinct_code:'0724',house_district:1,senate_district:1});assert(!el.innerHTML.includes('Sara Jane Haupt'));
const p=registry.profiles[0];for(const k of ['general','primary']){assert.equal(p[k].candidates.reduce((n,c)=>n+c.votes,0),p[k].total_votes);assert(Math.abs(p[k].candidates.reduce((n,c)=>n+c.share,0)-100)<1e-9);}assert.equal(p.primary.candidates[0].votes,877);assert.equal(p.general.candidates[0].votes,2978);
for(const file of ['index.html','ballot.html']){const text=fs.readFileSync(file,'utf8');for(const m of text.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g))if(m[1].trim()&&!m[0].includes('application/ld+json'))new vm.Script(m[1],{filename:file});}
const page=fs.readFileSync('candidates/sara-jane-haupt.html','utf8');assert(page.includes('January 4, 2027'));assert(page.includes('No votes or attendance from that term exist yet'));assert(!page.includes('W-NOMINATE'));assert(fs.readFileSync('sitemap.xml','utf8').includes('/candidates/sara-jane-haupt.html'));
console.log('PASS: all 27 precinct assignments, Ward 2-only profile lookup, all state districts preserved, wrong-city/invalid-code exclusion, exact election arithmetic, inline script syntax and indexed profile.');
