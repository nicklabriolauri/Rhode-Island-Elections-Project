import {CATEGORIES,FUNCTIONS,PRESETS,score,validateConfig,matchesTopic} from './activity-index-model.mjs?v=20261122-tiers125';

const data=JSON.parse(document.getElementById('pilot-data').textContent);
const $=id=>document.getElementById(id);
const text=(tag,value,className)=>{const el=document.createElement(tag);el.textContent=value;if(className)el.className=className;return el;};
const number=(n,digits=2)=>n===null?'Not defined':n.toLocaleString('en-US',{maximumFractionDigits:digits});
let currentConfig, currentRows;

function configFromInputs(){
  const weights=Object.fromEntries(CATEGORIES.map(([k])=>{
    const input=$('weight-'+k);
    return [k,input.value.trim()===''?NaN:Number(input.value)];
  }));
  return {weights,cosponsor:$('cosponsor-credit').value.trim()===''?NaN:Number($('cosponsor-credit').value),joint:$('joint-credit').value,includeCarryover:$('include-carryover').checked};
}
function applyPreset(key){
  const c=PRESETS[key];
  for(const [k] of CATEGORIES)$('weight-'+k).value=c.weights[k];
  $('cosponsor-credit').value=c.cosponsor;$('joint-credit').value=c.joint;$('include-carryover').checked=c.includeCarryover;$('preset').value=key;
  update();
}
function renderResults(rows){
  $('results').replaceChildren();
  for(const row of rows){
    const tr=document.createElement('tr');tr.append(text('th',row.name));tr.firstChild.scope='row';
    for(const value of [row.office_2026,row.observed,number(row.raw,3)])tr.append(text('td',value));
    tr.append(text('td',row.index===null?'Not defined':number(row.index,1),'index-value'));
    const cell=document.createElement('td');const b=text('button','Inspect');b.type='button';b.className='quiet';b.setAttribute('aria-label','Inspect contributions for '+row.name);
    b.addEventListener('click',()=>{$('audit-member').value=row.id;renderAudit();$('audit').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});});
    cell.append(b);tr.append(cell);$('results').append(tr);
  }
}
function renderAudit(){
  $('audit-items').replaceChildren();if(!currentRows)return;
  const row=currentRows.find(r=>r.id===$('audit-member').value);
  const topic=$('audit-topic').value;
  const visible=row.contributions.filter(c=>matchesTopic(c.proposal,topic));
  $('audit-total').textContent=`${row.name}: ${number(row.raw,3)} weighted activity units across ${row.observed} identified items in either role. Showing ${visible.length} item${visible.length===1?'':'s'}${topic?' tagged '+topic:''}. Topic filtering does not change the overall score.`;
  $('topic-breakdown').replaceChildren();
  for(const t of data.topic_vocabulary){
    const items=row.contributions.filter(c=>c.proposal.primary_topic===t);
    if(!items.length)continue;
    const tr=document.createElement('tr');const th=text('th',t);th.scope='row';tr.append(th,text('td',items.length),text('td',number(items.reduce((s,c)=>s+c.points,0),3)));$('topic-breakdown').append(tr);
  }
  if(!visible.length)$('audit-items').append(text('p','No identified contributions match this topic. This does not establish that the member did no work on it.'));
  for(const c of visible){
    const p=c.proposal;const card=document.createElement('details');card.className='contribution';
    const summary=document.createElement('summary');const titleBox=document.createElement('span');titleBox.append(text('span',p.title));
    const previewTags=document.createElement('span');previewTags.className='topic-tags';previewTags.append(text('span',p.primary_topic,'topic-tag'));
    for(const topic of p.secondary_topics)previewTags.append(text('span',topic,'topic-tag secondary'));titleBox.append(previewTags);
    summary.append(titleBox,text('strong',number(c.points,3)+' points'));card.append(summary);
    const body=document.createElement('div');
    body.append(text('p',CATEGORIES.find(([key])=>key===p.tier)[1]+' · '+FUNCTIONS[p.function]+' · '+(c.role==='sponsor'?'Named / joint sponsor':'Explicit cosponsor'),'item-type'));
    const tags=document.createElement('div');tags.className='topic-tags';tags.append(text('span',p.primary_topic+' · primary','topic-tag'));
    for(const tag of p.secondary_topics)tags.append(text('span',tag,'topic-tag secondary'));body.append(tags);
    const roleText=c.role==='sponsor' && currentConfig.joint==='split'?`1 / ${p.sponsors.length} named council sponsor${p.sponsors.length===1?'':'s'}`:number(c.roleCredit,3);
    body.append(text('p',c.included?`Category weight ${number(c.categoryWeight)} × role credit (${roleText}) = ${number(c.points,4)} points.`:'Excluded by the earlier-year item setting.'));
    if(p.carryover)body.append(text('p','Earlier-year item considered in 2026; not a new 2026 introduction.','source'));
    body.append(text('p',p.coding_reason,'source'),text('p',p.classification_note,'source'));
    for(const o of p.observations){
      const record=document.createElement('div');record.className='source-record';record.append(text('strong',o.date),text('p',o.action),text('p','Recorded attribution: '+o.attribution));
      const a=text('a','Read source minutes'+(o.source_page?', p. '+o.source_page:''));a.href=o.source_url+(o.source_page?'#page='+o.source_page:'');record.append(a);body.append(record);
    }
    for(const o of p.cosponsor_evidence||[]){
      const block=document.createElement('div');block.className='source-record';block.append(text('strong',o.date+' · Additional cosponsor evidence'),text('p',o.context),text('p',o.excerpt));
      const a=text('a','Read cosponsor source');a.href=o.source_url+(o.source_page?'#page='+o.source_page:'');block.append(a);body.append(block);
    }
    card.append(body);$('audit-items').append(card);
  }
}
function update(){
  try{
    const config=configFromInputs();validateConfig(config);const rows=score(data,config);currentConfig=config;currentRows=rows;
    $('input-error').hidden=true;$('export').disabled=false;renderResults(rows);renderAudit();
    const total=rows.reduce((s,r)=>s+r.raw,0);
    $('result-status').textContent=total===0?'All weighted activity is zero. The mean is zero, so the normalized index is not defined.':`Nine 2026 council members · ${data.proposals.length} identified measures · Mean weighted activity: ${number(total/rows.length,3)} · Index mean: 100. All attribution coverage is partial.`;
  }catch(error){
    currentRows=null;$('input-error').textContent=error.message;$('input-error').hidden=false;$('export').disabled=true;$('results').replaceChildren();$('audit-items').replaceChildren();$('topic-breakdown').replaceChildren();$('audit-total').textContent='';$('result-status').textContent='Results are unavailable until the input error is corrected.';
  }
}
for(const m of data.members){const option=text('option',m.name);option.value=m.id;$('audit-member').append(option);}
for(const t of data.topic_vocabulary){const option=text('option',t);option.value=t;$('audit-topic').append(option);}
const scenarios=Object.values(PRESETS).map(p=>score(data,p));
for(let i=0;i<data.members.length;i++){
  const tr=document.createElement('tr');const name=text('th',data.members[i].name);name.scope='row';tr.append(name);
  for(const rows of scenarios)tr.append(text('td',number(rows[i].index,1)));
  $('sensitivity').append(tr);
}
$('coverage-counts').textContent=`${data.proposals.length} identified measures across ${data.meeting_count} available meeting records`;
$('preset').addEventListener('change',()=>{if(PRESETS[$('preset').value])applyPreset($('preset').value);});
$('controls').addEventListener('submit',event=>event.preventDefault());
$('controls').addEventListener('input',()=>{$('preset').value='custom';update();});
$('controls').addEventListener('change',()=>{$('preset').value='custom';update();});
$('reset').addEventListener('click',()=>applyPreset('core'));
$('audit-member').addEventListener('change',renderAudit);
$('audit-topic').addEventListener('change',renderAudit);
$('export').addEventListener('click',()=>{
  if(!currentRows)return;
  const fields=['Member','2026 office','Observed items','Weighted activity','Activity index (mean 100)','Joint credit','Cosponsor credit','Include earlier-year items',...CATEGORIES.map(([,label])=>label+' weight'),'Snapshot version','Source SHA256'];
  const rows=currentRows.map(r=>[r.name,r.office_2026,r.observed,r.raw,r.index??'',currentConfig.joint,currentConfig.cosponsor,currentConfig.includeCarryover,...CATEGORIES.map(([k])=>currentConfig.weights[k]),data.version,data.source_sha256]);
  const csv=[fields,...rows].map(row=>row.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n');
  const href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=href;a.download='Cranston_Activity_Index_Test.csv';a.click();setTimeout(()=>URL.revokeObjectURL(href),1000);
});
applyPreset('core');
