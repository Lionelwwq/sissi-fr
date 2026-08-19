/* Service worker: she studies on the subway, where the site simply did not open.

   Three things this has to get right, each of which it got wrong once:
   - the book itself is precached, not merely cached on use, or the very first
     offline open sits on the loading spinner forever;
   - clips live in a bucket with no version in its name, because they never change
     and wiping 160 MB of downloaded audio over a one-line CSS edit is unforgivable;
   - the precache bypasses the HTTP cache, or a release published inside GitHub
     Pages' ten-minute max-age window pins the *old* files under the *new* version.
*/
var V = 'tcf-7eb39225';
var CLIPS = 'tcf-clip';
var SHELL = ['./', './index.html', './static/app.css', './static/app.js',
             './static/lookup.css', './static/lookup.js',
             './static/webshim.js', './static/mp3ids.js', './static/stats.js',
             './data/content.json', './data/dict.json',
             './data/word_index.json', './data/conj_index.json'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(V + '-shell').then(function (c) {
    return c.addAll(SHELL.map(function (u) { return new Request(u, { cache: 'reload' }); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  var keep = [V + '-shell', CLIPS];
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return keep.indexOf(k) < 0; })
                         .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function cacheFirst(req, bucket) {
  return caches.open(bucket).then(function (c) {
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
  if (url.pathname.indexOf('/clip/') >= 0) { e.respondWith(cacheFirst(req, CLIPS)); return; }
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).catch(function () { return caches.match('./index.html'); }));
    return;
  }
  e.respondWith(cacheFirst(req, V + '-shell'));
});
