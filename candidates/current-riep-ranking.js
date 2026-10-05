'use strict';
const input=document.getElementById('ranking-search');
const rows=Array.from(document.querySelectorAll('tbody tr'));
const status=document.getElementById('ranking-status');
function render(){
 const query=input.value.trim().toLocaleLowerCase();let count=0;
 for(const row of rows){const match=row.dataset.name.includes(query);row.hidden=!match;if(match)count++;}
 status.textContent=query?`${count} matching Senate records. Original ranks retained.`:'Showing all 38 Senate district records.';
}
input.addEventListener('input',render);
document.getElementById('ranking-clear').addEventListener('click',()=>{input.value='';render();input.focus();});
const selected=document.getElementById(location.hash.slice(1));
if(selected&&rows.includes(selected)){selected.classList.add('ranking-selected');selected.setAttribute('aria-current','true');}
