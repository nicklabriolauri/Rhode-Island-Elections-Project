/* Pure scoring functions shared by the website and regression tests. */
export const CATEGORIES = [
  ['local_rule', 'Local rules and ordinances'],
  ['fiscal', 'Fiscal measures'],
  ['approval', 'Property / administrative approvals'],
  ['advocacy', 'Requests for state action'],
  ['symbolic', 'Symbolic display policy'],
  ['recognition', 'Recognition and commemoration']
];
export const PRESETS = {
  core: {label:'Local policy activity',weights:{local_rule:1,fiscal:1,approval:0,advocacy:0,symbolic:0,recognition:0},cosponsor:0.25,joint:'split',includeCarryover:true},
  initiators: {label:'Sponsors only',weights:{local_rule:1,fiscal:1,approval:0,advocacy:0,symbolic:0,recognition:0},cosponsor:0,joint:'split',includeCarryover:true},
  broader: {label:'Include advocacy',weights:{local_rule:1,fiscal:1,approval:0,advocacy:0.5,symbolic:0,recognition:0},cosponsor:0.25,joint:'split',includeCarryover:true}
};
export function validateConfig(config) {
  if (!config || !['split','full'].includes(config.joint) || typeof config.includeCarryover!=='boolean') throw new Error('Invalid credit settings');
  for (const value of [...CATEGORIES.map(([k])=>config.weights?.[k]), config.cosponsor]) {
    if (typeof value!=='number' || !Number.isFinite(value) || value<0 || value>5) throw new Error('Enter weights between 0 and 5');
  }
}
export function score(data, config) {
  validateConfig(config);
  const members=new Set(data.members.map(m=>m.id));
  const ids=new Set();
  for (const p of data.proposals) {
    if (ids.has(p.id)) throw new Error('Duplicate measure: '+p.id);
    ids.add(p.id);
    if (!CATEGORIES.some(([k])=>k===p.function)) throw new Error('Unclassified measure: '+p.id);
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
      const categoryWeight=config.weights[p.function];
      const included=config.includeCarryover||!p.carryover;
      contributions.push({proposal:p,role,roleCredit,categoryWeight,included,points:included?roleCredit*categoryWeight:0});
    }
    return {...m,contributions,raw:contributions.reduce((s,c)=>s+c.points,0),observed:contributions.length};
  });
  const mean=rows.length?rows.reduce((s,r)=>s+r.raw,0)/rows.length:0;
  return rows.map(r=>({...r,index:mean>0?100*r.raw/mean:null}));
}
export function competitionRanks(rows) {
  return rows.map(r=>r.index===null?null:1+rows.filter(o=>o.raw-r.raw>1e-10).length);
}
