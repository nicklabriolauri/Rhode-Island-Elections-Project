(() => {
  const rows=[...document.querySelectorAll('#ratings-table tbody tr')];
  const chamber=document.getElementById('chamber'),scope=document.getElementById('scope'),search=document.getElementById('search');
  function filter(){let count=0;for(const row of rows){row.hidden=!!((chamber.value&&row.dataset.chamber!==chamber.value)||(scope.value==='rated'&&row.dataset.included!=='true')||(scope.value==='watch'&&row.dataset.watch!=='true')||!row.textContent.toLowerCase().includes(search.value.toLowerCase()));if(!row.hidden)count++;}document.getElementById('result-count').textContent=count+' races shown';}
  for(const control of [chamber,scope,search])control.addEventListener('input',filter);filter();
})();
