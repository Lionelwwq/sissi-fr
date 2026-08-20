/* Service worker: she studies on the subway, where the site simply did not open.

   Five things this has to get right, each of which it got wrong once:
   - the book itself is precached, not merely cached on use, or the very first
     offline open sits on the loading spinner forever;
   - clips live in a bucket with no version in its name, because they never change
     and wiping 264 MB of downloaded audio over a one-line CSS edit is unforgivable;
   - the precache bypasses the HTTP cache, or a release published inside GitHub
     Pages' ten-minute max-age window pins the *old* files under the *new* version;
   - an <audio> element asks for a byte range, and the 206 that answers it can never
     be written to a Cache. Every clip she played was therefore online-only: the text
     worked underground and the sound did not. Fetch the whole file alongside it;
   - the page itself must be re-cached as she browses. install only runs when this
     file changes, so after iOS evicts the site's storage nothing ever refills it —
     measured: everything came back on demand except index.html, which the navigate
     branch never stored, leaving the app permanently broken offline;
   - the HTML comes out of the same bucket as the scripts, or a release serves new
     markup to old code for as long as the new worker takes to install.
*/
var V = 'tcf-28bbbf13';
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

function keepFull(c, url) {
  // a plain no-Range request, so the answer is a storable 200 rather than a 206
  return fetch(url, { cache: 'no-store' }).then(function (full) {
    if (full && full.status === 200) return c.put(url, full);
  }).catch(function () {});
}

function cacheFirst(req, bucket) {
  return caches.open(bucket).then(function (c) {
    return c.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        if (res && res.ok) {
          if (res.status === 206) keepFull(c, req.url);
          else c.put(req, res.clone()).catch(function () { keepFull(c, req.url); });
        }
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
    /* Cache-first from THIS version's bucket, like every other asset.
       Serving the page from the network while its scripts come from the cache means a
       release can hand her tomorrow's index.html running yesterday's app.js — and a
       network-first navigation has no failure mode for a half-connected subway signal
       either: it does not reject, it hangs, and a hang is a white screen on a site that
       is fully downloaded. Reading both from the same bucket makes a release an atomic
       swap: she keeps the old version until the new worker has finished installing. */
    e.respondWith(caches.open(V + '-shell').then(function (c) {
      return c.match('./index.html').then(function (hit) {
        var net = fetch(req).then(function (res) {
          if (res && res.ok) c.put('./index.html', res.clone()).catch(function () {});
          return res;
        });
        if (!hit) return net.catch(function () { return caches.match('./index.html'); });
        net.catch(function () {});      // refresh in the background, never block on it
        return hit;
      });
    }));
    return;
  }
  e.respondWith(cacheFirst(req, V + '-shell'));
});
