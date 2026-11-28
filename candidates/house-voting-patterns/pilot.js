(() => {
  const script = document.createElement('script');
  script.src = new URL('../voting-patterns/pilot.js?v=house-rollout', document.currentScript.src);
  script.dataset.chamber = 'house';
  document.head.append(script);
})();
