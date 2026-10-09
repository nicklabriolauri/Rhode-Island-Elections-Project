(() => {
 const boards=[...document.querySelectorAll('.ratings-board')];
 const chamber=document.getElementById('chamber'),swing=document.getElementById('swing');
 function update(){for(const board of boards)board.hidden=board.dataset.swing!==swing.value||!!(chamber.value&&board.dataset.chamber!==chamber.value);}
 for(const control of [chamber,swing])control.addEventListener('change',update);update();
})();
