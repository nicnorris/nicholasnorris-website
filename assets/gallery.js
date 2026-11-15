// Painting gallery: thumbnail grid plus a one-at-a-time viewer.
// Each painting has its own link: paintings.html#<slug>
(function () {
  var dataEl = document.getElementById('paintings-data');
  if (!dataEl) return;
  var works = JSON.parse(dataEl.textContent);
  var grid = document.querySelector('.grid');
  var viewer = document.querySelector('.viewer');
  var viewerImg = viewer.querySelector('img');
  var captions = document.querySelectorAll('[data-caption]');
  var others = document.querySelectorAll('[data-hide-in-viewer]');
  var current = -1;

  function setOthers(hidden) {
    others.forEach(function (el) { el.hidden = hidden; });
  }

  function indexOf(slug) {
    for (var i = 0; i < works.length; i++) if (works[i].slug === slug) return i;
    return -1;
  }

  function fill(el, w, i) {
    var prev = works[(i - 1 + works.length) % works.length].slug;
    var next = works[(i + 1) % works.length].slug;
    el.querySelector('.title').textContent = w.title;
    el.querySelector('.year').textContent = w.year;
    el.querySelector('.medium').textContent = w.medium;
    el.querySelector('.size').textContent = w.size;
    el.querySelector('.prev').setAttribute('href', '#' + prev);
    el.querySelector('.next').setAttribute('href', '#' + next);
    el.hidden = false;
  }

  function preload(i) {
    var img = new Image();
    img.src = works[(i + works.length) % works.length].large;
  }

  function show(i) {
    current = i;
    var w = works[i];
    viewerImg.src = w.large;
    viewerImg.alt = w.title + ', ' + w.year + '. ' + w.medium + ', ' + w.size + '.';
    captions.forEach(function (el) { fill(el, w, i); });
    grid.hidden = true;
    setOthers(true);
    viewer.hidden = false;
    document.title = w.title + ' | ' + document.body.dataset.site;
    preload(i + 1);
    preload(i - 1);
    window.scrollTo(0, 0);
  }

  function showGrid() {
    current = -1;
    viewer.hidden = true;
    captions.forEach(function (el) { el.hidden = true; });
    grid.hidden = false;
    setOthers(false);
    document.title = document.body.dataset.title;
  }

  function route() {
    var slug = decodeURIComponent(location.hash.replace('#', ''));
    var i = indexOf(slug);
    if (i >= 0) show(i); else showGrid();
  }

  function go(step) {
    if (current < 0) return;
    location.hash = works[(current + step + works.length) % works.length].slug;
  }

  viewerImg.addEventListener('click', function () { go(1); });

  document.addEventListener('keydown', function (e) {
    if (current < 0) return;
    if (e.key === 'ArrowRight') go(1);
    else if (e.key === 'ArrowLeft') go(-1);
    else if (e.key === 'Escape') location.hash = 'thumbnails';
  });

  var touchX = null;
  viewer.addEventListener('touchstart', function (e) { touchX = e.touches[0].clientX; }, { passive: true });
  viewer.addEventListener('touchend', function (e) {
    if (touchX === null) return;
    var dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
    touchX = null;
  });

  window.addEventListener('hashchange', route);
  route();
})();
