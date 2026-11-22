/* Full council records only. Never infer a member vote from attendance or sponsorship. */
(() => {
  'use strict';
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const byId = id => document.getElementById(id);
  const source = (r, text='Official minutes') => `<a href="${esc(r.source_url)}${r.source_page ? '#page='+r.source_page : ''}" target="_blank" rel="noopener">${esc(text)}${r.source_page ? ', p. '+r.source_page : ''}</a>`;
  const table = (headers, rows, caption='') => `<div class="table-scroll"><table>${caption ? `<caption>${esc(caption)}</caption>` : ''}<thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  const tally = m => m.review_status==='Needs review' ? 'Source conflict — needs review' : m.yes == null ? (m.result==='Unanimous' ? 'Unanimous' : 'See source') : m.yes+'–'+m.no;
  let data, page=0;const size=15;
  function votes() {
    const q=byId('query').value.trim().toLowerCase(),member=byId('member').value,kind=byId('kind').value;
    const rows=data.motions.filter(m=>(!member || m.votes[member]) && (!kind || m.kind===kind) && (!q || (m.title+' '+m.action+' '+m.resolution_ids.join(' ')).toLowerCase().includes(q)));
    const pages=Math.max(1,Math.ceil(rows.length/size));page=Math.min(page,pages-1);
    byId('vote-count').textContent=`${rows.length} recorded motions`;
    byId('page').textContent=`Page ${page+1} of ${pages}`;byId('previous').disabled=page===0;byId('next').disabled=page===pages-1;
    const items=rows.slice(page*size,(page+1)*size).map(m=>{
      const list=Object.entries(m.votes).map(([id,v])=>`${data.members.find(x=>x.id===id)?.name || id}: ${v}`).join('; ');
      return `<tr id="${esc(m.id)}"><td>${esc(m.date)}<span class="record-meta">${esc(m.minutes_status || '')}</span></td><td><span class="record-title">${esc(m.title)}</span><span class="record-meta">${esc(m.action)}</span>${m.resolution_ids.length ? `<span class="record-meta">Resolution ${esc(m.resolution_ids.join(', '))}</span>` : ''}<details><summary>Read the recorded motion and votes</summary><p>${esc(list)}</p><p class="record-excerpt">${esc(m.source_excerpt)}</p></details></td><td>${member ? `<span class="${m.votes[member]==='Yes'?'vote-yes':m.votes[member]==='No'?'vote-no':''}">${esc(m.votes[member])}</span><br>` : ''}${esc(tally(m))}${m.abstain ? ', '+m.abstain+' abstaining' : ''}<span class="record-meta">${esc(m.result)}${Object.keys(m.votes).length ? '' : ' · individual votes not assigned'}</span></td><td>${source(m)}</td></tr>`;
    });
    byId('vote-results').innerHTML=items.length ? table(['Meeting','Measure and motion',member?'Member vote / tally':'Tally','Source'],items) : '<p class="empty">No matching named votes in the imported records.</p>';
    const url=new URL(location.href);member?url.searchParams.set('member',member):url.searchParams.delete('member');history.replaceState(null,'',url);
  }
  function resolutions(){
    const q=byId('resolution-query').value.trim().toLowerCase();const list=data.resolutions.filter(r=>(r.number+' '+r.title).toLowerCase().includes(q));
    byId('resolution-results').innerHTML=table(['Resolution','Adopted','Title and document','Vote link'],list.map(r=>`<tr><th scope="row">${esc(r.number)}</th><td>${esc(r.adopted_date)}</td><td><a href="${esc(r.original_path || r.source_url)}" target="_blank" rel="noopener">${esc(r.title)}</a>${r.original_path ? `<span class="record-meta"><a href="${esc(r.source_url)}">Original city source</a></span>`:''}</td><td>${r.motion_ids?.length ? r.motion_ids.map(id=>{const m=data.motions.find(x=>x.id===id);return m ? `<a href="${esc(m.source_url)}${m.source_page?'#page='+m.source_page:''}">${esc(tally(m))} · ${esc(m.date)}</a>`:'Vote needs review';}).join('<br>') : 'Match needs review'}</td></tr>`),`${list.length} resolutions listed in the published ClerkBase index`);
  }
  function attendance(){
    byId('attendance-results').innerHTML=table(['Member','2026 office','Present at opening','Late arrival','Absent','Unresolved'],data.members.map(m=>{const a=data.attendance.filter(a=>a.member_id===m.id),p=a.filter(a=>a.status==='Present').length,n=a.filter(a=>a.status==='Absent').length,u=a.filter(a=>a.status==='Not recorded').length,l=a.filter(a=>a.status==='Late arrival').length;return `<tr><th scope="row">${esc(m.name)}</th><td>${esc(m.office_2026)}</td><td>${p} of ${p+n+l} documented meetings</td><td>${l}</td><td>${n}</td><td>${u}</td></tr>`;}));
  }
  function coverage(){
    const good=data.motions.filter(m=>Object.keys(m.votes).length).length;
    byId('coverage').textContent=`${data.resolutions.length} indexed resolutions · ${data.meetings.length} meeting records · ${good} reconciled named motions. Retrieved ${new Date(data.retrieved_at).toLocaleDateString('en-US',{timeZone:'America/New_York'})}. Coverage is limited to the published records listed below.`;
    byId('coverage-results').innerHTML=`<p>${esc(data.scope)}</p><p>${data.review_queue.length} entries need further review or source matching. Unresolved roll calls are excluded from individual voting histories. Draft minutes remain labeled as drafts.</p>`;
    const inventory=data.meeting_inventory?.length ? table(['Date / time','Minutes availability','Official meeting record'],data.meeting_inventory.map(m=>`<tr><td>${esc(m.meeting || m.date)}</td><td>${esc(m.minutes_status || 'No minutes linked')}</td><td><a href="${esc(m.source_url || 'https://opengov.sos.ri.gov/OpenMeetingsPublic/OpenMeetingDashboard?EntityID=715')}">State filing</a></td></tr>`)) : '';
    byId('review-results').innerHTML=inventory+table(['Record','Review needed','Source'],data.review_queue.map(r=>`<tr><td>${esc(r.type)}</td><td>${esc(r.reason)}</td><td>${source(r,'Source')}</td></tr>`));
  }
  fetch('/data/cranston/records-2026/records.json').then(r=>{if(!r.ok)throw Error('Records unavailable');return r.json();}).then(d=>{
    data=d;const select=byId('member');select.innerHTML+=[...d.members].sort((a,b)=>a.name.localeCompare(b.name)).map(m=>`<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');
    const member=new URLSearchParams(location.search).get('member');if(d.members.some(m=>m.id===member))select.value=member;
    ['query','member','kind'].forEach(id=>byId(id).addEventListener(id==='query'?'input':'change',()=>{page=0;votes();}));byId('previous').addEventListener('click',()=>{page--;votes();});byId('next').addEventListener('click',()=>{page++;votes();});byId('resolution-query').addEventListener('input',resolutions);votes();resolutions();attendance();coverage();
  }).catch(()=>{byId('coverage').textContent='The records could not be loaded. Please try again or follow the official archive link below.';});
})();
