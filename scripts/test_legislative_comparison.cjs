const fs=require('fs'),vm=require('vm'),assert=require('assert');
const data=JSON.parse(fs.readFileSync('data/legislative_comparison_2023_2024.json'));
async function run(fail=false){
const panels=['John Burke','Frank A Ciccone','Lori Urso'].map(name=>({dataset:{historicalName:name},node:{},querySelector(){return this.node}}));
const nodes={};for(const id of ['comparison-body','comparison-summary','comparison-chart'])nodes[id]={};
nodes['comparison-chamber']={value:'senate',addEventListener(t,f){this.change=f}};nodes['comparison-search']={value:'',addEventListener(t,f){this.input=f}};
const document={querySelectorAll:()=>panels,getElementById:id=>nodes[id]};
await vm.runInNewContext(fs.readFileSync('candidates/historical-comparison.js','utf8'),{document,fetch:async()=>({ok:!fail,json:async()=>data})});
if(fail){assert.match(nodes['comparison-summary'].textContent,/unavailable/);return;}
assert.match(panels[0].node.innerHTML,/0.69/);assert.match(panels[1].node.innerHTML,/1.49/);assert.match(panels[2].node.textContent,/Not applicable/);
assert.equal((nodes['comparison-body'].innerHTML.match(/<tr>/g)||[]).length,39);
nodes['comparison-search'].value='burke';nodes['comparison-search'].input();assert.equal((nodes['comparison-body'].innerHTML.match(/<tr>/g)||[]).length,1);
nodes['comparison-search'].value='';nodes['comparison-chamber'].value='house';nodes['comparison-chamber'].change();assert.equal((nodes['comparison-body'].innerHTML.match(/<tr>/g)||[]).length,75);
}
(async()=>{await run();await run(true);console.log('PASS: profile scores, Urso eligibility, 39/75 table rows, filtering, chamber selection, fetch failure')})().catch(e=>{console.error(e);process.exit(1)});
