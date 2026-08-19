/* Service worker: she studies on the subway, where the site simply did not open.
   Shell is precached; content and clips are cached the first time they are used. */
var V = 'tcf-f2ad8ffc';
var SHELL = ['./', './index.html', './static/app.css', './static/app.js',
             './static/lookup.css', './static/lookup.js',
             './static/webshim.js', './static/mp3ids.js', './static/stats.js'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(V + '-shell').then(function (c) { return c.addAll(SHELL); })
    .then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k.indexOf(V) !== 0; })
                         .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function cacheFirst(req, bucket) {
  return caches.open(V + '-' + bucket).then(function (c) {
    return c.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res && res.ok) c.put(req, res.clone());
        return res;
      });
    });
  });
}

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.indexOf('/clip/') >= 0) { e.respondWith(cacheFirst(req, 'clip')); return; }
  if (url.pathname.indexOf('/data/') >= 0) { e.respondWith(cacheFirst(req, 'data')); return; }
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(function () { return caches.match('./index.html'); }));
    return;
  }
  e.respondWith(cacheFirst(req, 'shell'));
});
