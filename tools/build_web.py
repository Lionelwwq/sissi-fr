# -*- coding: utf-8 -*-
"""Derive the hosted static site from the desktop sources.

Run it from anywhere:  python tools/build_web.py

The server the exe talks to was thin (four JSON reads, clips out of zips, a vocab
file), so the whole thing collapses into static files plus a fetch shim. tools/src/
stays the single source of truth: this transforms it rather than keeping a copy.

It builds IN PLACE into the repo root, which is what GitHub Pages serves. That means
no rmtree anywhere near a directory that also holds .git and 264 MB of audio: the
clips are never touched, only index.html / static/ / sw.js are rewritten.

Clips normally already live in <repo>/clip. Pass --zips DIR to (re)extract them from
audio.zip / words.zip / conj.zip in DIR, which is only needed after synthesising new
audio.
"""
import hashlib, io, json, os, shutil, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
CLIP = os.path.join(ROOT, "clip")
OUT = ROOT

zips = None
if "--zips" in sys.argv:
    zips = sys.argv[sys.argv.index("--zips") + 1]

for d in (SRC, DATA):
    assert os.path.isdir(d), "missing " + d
os.makedirs(os.path.join(OUT, "static"), exist_ok=True)
os.makedirs(CLIP, exist_ok=True)


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


# ---------------------------------------------------------------- clips
if zips:
    n = 0
    for zname in ("audio.zip", "words.zip", "conj.zip"):
        with zipfile.ZipFile(os.path.join(zips, zname)) as z:
            for name in z.namelist():
                with open(os.path.join(CLIP, name), "wb") as f:
                    f.write(z.read(name))
                n += 1
    print("extracted %d clips from %s" % (n, zips))

names = os.listdir(CLIP)
mp3 = [x for x in names if x.endswith(".mp3")]
print("clips: %d, of which mp3: %d" % (len(names), len(mp3)))
assert names, "clip/ is empty — pass --zips DIR to extract them"

# a synchronous lookup: the audio element needs the extension before any fetch resolves.
# Once every clip is mp3 the lookup table is 350 kB of the same answer, so drop it.
if len(mp3) == len(names):
    write(os.path.join(OUT, "static", "mp3ids.js"), "window.__ALLMP3=1;\n")
else:
    table = dict((x.rsplit(".", 1)[0], 1) for x in mp3)
    write(os.path.join(OUT, "static", "mp3ids.js"),
          "window.__MP3=" + json.dumps(table, separators=(",", ":")) + ";\n")

# ---------------------------------------------------------------- data
for f in ("content.json", "dict.json", "word_index.json", "conj_index.json"):
    assert os.path.exists(os.path.join(DATA, f)), "missing data/" + f

# ---------------------------------------------------------------- js / css
for f in ("app.css", "stats.js", "lookup.css"):
    shutil.copy(os.path.join(SRC, f), os.path.join(OUT, "static", f))

app = read(os.path.join(SRC, "app.js"))
old = "au.src = '/audio/' + aid;"
assert app.count(old) == 1, app.count(old)
app = app.replace(old, "au.src = window.CLIP(aid);")
assert "'/audio/" not in app, "app.js still has a server path"
write(os.path.join(OUT, "static", "app.js"), app)

lk = read(os.path.join(SRC, "lookup.js"))
for a, b in (("au.src = '/word/' + id;", "au.src = window.CLIP(id);"),
             ("au.src = '/word/' + ids[i++];", "au.src = window.CLIP(ids[i++]);"),
             # long-press-to-play-a-sentence: missing this one made the gesture the welcome
             # screen teaches silently dead on the hosted copy, while the exe stayed fine
             ("au.src = '/audio/' + aid;", "au.src = window.CLIP(aid);")):
    assert lk.count(a) == 1, (a, lk.count(a))
    lk = lk.replace(a, b)
# nothing may reach for a server path any more, whatever gets added later
assert "'/word/" not in lk and "'/audio/" not in lk, "lookup.js still has a server path"
write(os.path.join(OUT, "static", "lookup.js"), lk)

SHIM = """/* Static-hosting shim: maps the desktop app's endpoints onto plain files.
   Loaded before app.js so nothing downstream knows the server is gone. */
(function () {
  'use strict';
  var MAP = {
    '/api/content': 'data/content.json',
    '/api/dict': 'data/dict.json',
    '/api/dict/audio-index': 'data/word_index.json',
    '/api/conj': 'data/conj_index.json'
  };
  var ALL = !!window.__ALLMP3, MP3 = window.__MP3 || {};
  window.CLIP = function (id) { return 'clip/' + id + (ALL || MP3[id] ? '.mp3' : '.opus'); };

  var KEY = 'tcf_vocab';
  function vocab() {
    try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; }
  }
  // storage full on an iPhone used to be swallowed here, and the card still said 已加入
  function save(v) {
    try { localStorage.setItem(KEY, JSON.stringify(v)); return true; } catch (e) { return false; }
  }
  function json(o) {
    return Promise.resolve(new Response(JSON.stringify(o),
      { status: 200, headers: { 'Content-Type': 'application/json' } }));
  }
  function body(opt) {
    try { return JSON.parse((opt || {}).body || '{}'); } catch (e) { return {}; }
  }

  var real = window.fetch.bind(window);
  window.fetch = function (url, opt) {
    var u = String(url);
    if (MAP[u]) return real(MAP[u], opt);
    if (u === '/api/ping') return json({ ok: true, app: 'tcf-coach-web' });
    if (u === '/api/quit') return json({ ok: true });
    if (u === '/api/vocab/list') return json(vocab());
    if (u === '/api/vocab/add') {
      var d = body(opt), v = vocab(), ok = true;
      if (d.word && !v.some(function (x) { return (x.word || '').toLowerCase() === d.word.toLowerCase(); })) {
        v.push({ word: d.word, lemma: d.lemma || d.word, gloss: d.gloss || '', sentence: d.sentence || '' });
        ok = save(v);
      }
      return json({ ok: ok, n: v.length });
    }
    if (u === '/api/vocab/remove') {
      var w = (body(opt).word || '').toLowerCase();
      var kept = vocab().filter(function (x) { return (x.word || '').toLowerCase() !== w; });
      var ok2 = save(kept);
      return json({ ok: ok2, n: kept.length });
    }
    return real(url, opt);
  };
})();
"""
write(os.path.join(OUT, "static", "webshim.js"), SHIM)

# ---------------------------------------------------------------- offline
SW = """/* Service worker: she studies on the subway, where the site simply did not open.

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
var V = 'tcf-__VER__';
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
"""

SW_REG = """<script>
/* only the hosted copy needs a service worker; the exe already serves from disk */
if ('serviceWorker' in navigator && location.protocol === 'https:') {
  addEventListener('load', function () { navigator.serviceWorker.register('sw.js').catch(function () {}); });
}
</script>
"""

# ---------------------------------------------------------------- html
html = read(os.path.join(SRC, "index.html"))
html = html.replace('href="/static/', 'href="static/').replace('src="/static/', 'src="static/')
# no server to quit, and personal material should not be indexed
html = html.replace('<button class="btn" id="btnQuit" title="退出程序">⏻ 退出</button>',
                    '<button class="btn hidden" id="btnQuit">⏻</button>')
html = html.replace('<meta name="viewport"',
                    '<meta name="robots" content="noindex, nofollow">\n<meta name="viewport"')
html = html.replace('<script src="static/app.js"></script>',
                    '<script src="static/mp3ids.js"></script>\n'
                    '<script src="static/webshim.js"></script>\n'
                    '<script src="static/app.js"></script>')
html = html.replace('</body>', SW_REG + '</body>')
assert 'static/webshim.js' in html and 'href="static/app.css"' in html and 'sw.js' in html
write(os.path.join(OUT, "index.html"), html)

# The service worker serves data/ cache-first, so the cache key has to move whenever
# the *content* moves too. Keying on the shell alone meant a chapters-only deploy was
# invisible to anyone who had already opened the site — the worst kind of silent bug.
h = hashlib.md5()
for f in ("index.html", "static/app.js", "static/app.css", "static/lookup.js",
          "static/lookup.css", "static/webshim.js", "static/mp3ids.js", "static/stats.js"):
    h.update(read(os.path.join(OUT, f)).encode("utf-8"))
for f in ("data/content.json", "data/word_index.json", "data/conj_index.json", "data/dict.json"):
    with open(os.path.join(OUT, f), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
ver = h.hexdigest()[:8]
write(os.path.join(OUT, "sw.js"), SW.replace("__VER__", ver))
print("sw.js version", ver)

write(os.path.join(OUT, ".nojekyll"), "")
write(os.path.join(OUT, "robots.txt"), "User-agent: *\nDisallow: /\n")
# GitHub Pages ignores this; it is here so a move to Netlify/Cloudflare keeps the
# clips immutable. Offline caching does not depend on it — the service worker does.
write(os.path.join(OUT, "_headers"),
      "/clip/*\n  Cache-Control: public, max-age=31536000, immutable\n")

total = sum(os.path.getsize(os.path.join(r, f))
            for r, _, fs in os.walk(OUT) if ".git" not in r for f in fs)
print("site: %.1f MB (clips included)" % (total / 1e6))
