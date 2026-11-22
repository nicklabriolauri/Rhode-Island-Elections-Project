/* Pure scoring functions shared by the website and regression tests. */
export const CATEGORIES = [
  ['symbolic', 'Symbolic and advocacy activity'],
  ['administrative', 'Routine approvals and administrative decisions'],
  ['substantive', 'Substantive municipal policymaking']
];
export const FUNCTIONS = {
  local_rule:'Local rules and ordinances', fiscal:'Fiscal measures',
  approval:'Property / administrative approvals', advocacy:'Requests for state action',
  symbolic:'Symbolic display policy', recognition:'Recognition and commemoration'
};
export const PRESETS = {
  core: {label:'RIEP 1–2–5',weights:{symbolic:1,administrative:2,substantive:5},cosponsor:0,joint:'full',includeCarryover:true},
  compact: {label:'Alternative 1–2–3',weights:{symbolic:1,administrative:2,substantive:3},cosponsor:0,joint:'full',includeCarryover:true},
  equal: {label:'Equal weights 1–1–1',weights:{symbolic:1,administrative:1,substantive:1},cosponsor:0,joint:'full',includeCarryover:true}
};
export function validateConfig(config) {
  if (!config || !['split','full'].includes(config.joint) || typeof config.includeCarryover!=='boolean') throw new Error('Invalid credit settings');
  for (const value of [...CATEGORIES.map(([k])=>config.weights?.[k]), config.cosponsor]) {
    if (typeof value!=='number' || !Number.isFinite(value) || value<0 || value>10) throw new Error('Enter weights between 0 and 10');
  }
}
export function score(data, config) {
  validateConfig(config);
  const members=new Set(data.members.map(m=>m.id));
  const ids=new Set();
  for (const p of data.proposals) {
    if (ids.has(p.id)) throw new Error('Duplicate measure: '+p.id);
    ids.add(p.id);
    if (!CATEGORIES.some(([k])=>k===p.tier) || !FUNCTIONS[p.function]) throw new Error('Unclassified measure: '+p.id);
    const topics=[p.primary_topic,...p.secondary_topics];
    if (topics.length>3 || new Set(topics).size!==topics.length || topics.some(t=>!data.topic_vocabulary.includes(t))) throw new Error('Invalid topic tags: '+p.id);
    if (new Set(p.sponsors).size!==p.sponsors.length || new Set(p.cosponsors).size!==p.cosponsors.length) throw new Error('Duplicate person credit');
    if (p.sponsors.some(id=>p.cosponsors.includes(id))) throw new Error('Sponsor/cosponsor overlap');
    if ([...p.sponsors,...p.cosponsors].some(id=>!members.has(id))) throw new Error('Unknown council member');
  }
  const rows=data.members.map(m=>{
    const contributions=[];
    for (const p of data.proposals) {
      const role=p.sponsors.includes(m.id)?'sponsor':p.cosponsors.includes(m.id)?'cosponsor':null;
      if (!role) continue;
      const roleCredit=role==='sponsor' ? (config.joint==='split'?1/p.sponsors.length:1) : config.cosponsor;
      const categoryWeight=config.weights[p.tier];
      const included=config.includeCarryover||!p.carryover;
      contributions.push({proposal:p,role,roleCredit,categoryWeight,included,points:included?roleCredit*categoryWeight:0});
    }
    return {...m,contributions,raw:contributions.reduce((s,c)=>s+c.points,0),observed:contributions.length};
  });
  const mean=rows.length?rows.reduce((s,r)=>s+r.raw,0)/rows.length:0;
  return rows.map(r=>({...r,index:mean>0?100*r.raw/mean:null}));
}
export function matchesTopic(proposal,topic){return !topic||proposal.primary_topic===topic||proposal.secondary_topics.includes(topic);}

export function rankRows(rows) {
 const sorted=[...rows].sort((a,b)=>(b.raw-a.raw)||a.name.localeCompare(b.name));
 return sorted.map((r,i)=>({...r,rank:r.index===null?null:(i&&Math.abs(r.raw-sorted[i-1].raw)<1e-10?sorted.findIndex(x=>Math.abs(x.raw-r.raw)<1e-10)+1:i+1)}));
}
