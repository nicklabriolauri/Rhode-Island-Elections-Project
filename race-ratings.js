(() => {
 const boards=[...document.querySelectorAll('.ratings-board')];
 const chamber=document.getElementById('chamber');
 function update(){for(const board of boards)board.hidden=!!(chamber.value&&board.dataset.chamber!==chamber.value);}
 chamber.addEventListener('change',update);update();
})();
