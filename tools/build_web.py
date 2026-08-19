# -*- coding: utf-8 -*-
"""Derive a pure-static site from the desktop build.

The server was thin (four JSON reads, clips out of zips, a vocab file), so the whole
thing collapses into static files plus a fetch shim. The desktop JS stays the single
source of truth: this transforms it rather than keeping a second copy.
"""
import hashlib, io, json, os, shutil, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "static")
DATA = os.path.join(HERE, "data")
WEB = os.path.join(HERE, "web")

if os.path.isdir(WEB):
    shutil.rmtree(WEB)
for d in ("static", "data", "clip"):
    os.makedirs(os.path.join(WEB, d))


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


# ---------------------------------------------------------------- clips
mp3 = {}
n = 0
for zname in ("audio.zip", "words.zip", "conj.zip"):
    with zipfile.ZipFile(os.path.join(DATA, zname)) as z:
        for name in z.namelist():
            base, ext = name.rsplit(".", 1)
            if ext == "mp3":
                mp3[base] = 1
            with open(os.path.join(WEB, "clip", name), "wb") as f:
                f.write(z.read(name))
            n += 1
print("clips extracted:", n, "of which mp3:", len(mp3))

# a synchronous lookup: the audio element needs the extension before any fetch resolves.
# Once every clip is mp3 the lookup table is 350 kB of the same answer, so drop it.
if len(mp3) == n:
    write(os.path.join(WEB, "static", "mp3ids.js"), "window.__ALLMP3=1;\n")
else:
    write(os.path.join(WEB, "static", "mp3ids.js"),
          "window.__MP3=" + json.dumps(mp3, separators=(",", ":")) + ";\n")

# ---------------------------------------------------------------- data
shutil.copy(os.path.join(DATA, "content.json"), os.path.join(WEB, "data", "content.json"))
shutil.copy(os.path.join(DATA, "bank_dict.json"), os.path.join(WEB, "data", "dict.json"))
shutil.copy(os.path.join(DATA, "word_index.json"), os.path.join(WEB, "data", "word_index.json"))
shutil.copy(os.path.join(DATA, "conj_index.json"), os.path.join(WEB, "data", "conj_index.json"))

# ---------------------------------------------------------------- js / css
shutil.copy(os.path.join(SRC, "app.css"), os.path.join(WEB, "static", "app.css"))
shutil.copy(os.path.join(SRC, "stats.js"), os.path.join(WEB, "static", "stats.js"))
shutil.copy(os.path.join(SRC, "lookup.css"), os.path.join(WEB, "static", "lookup.css"))

app = read(os.path.join(SRC, "app.js"))
old = "au.src = '/audio/' + aid;"
assert app.count(old) == 1, app.count(old)
app = app.replace(old, "au.src = window.CLIP(aid);")
assert "'/audio/" not in app, "app.js still has a server path"
write(os.path.join(WEB, "static", "app.js"), app)

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
write(os.path.join(WEB, "static", "lookup.js"), lk)

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
  function save(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} }
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
      var d = body(opt), v = vocab();
      if (d.word && !v.some(function (x) { return (x.word || '').toLowerCase() === d.word.toLowerCase(); })) {
        v.push({ word: d.word, lemma: d.lemma || d.word, gloss: d.gloss || '', sentence: d.sentence || '' });
        save(v);
      }
      return json({ ok: true, n: v.length });
    }
    if (u === '/api/vocab/remove') {
      var w = (body(opt).word || '').toLowerCase();
      var kept = vocab().filter(function (x) { return (x.word || '').toLowerCase() !== w; });
      save(kept);
      return json({ ok: true, n: kept.length });
    }
    return real(url, opt);
  };
})();
"""
write(os.path.join(WEB, "static", "webshim.js"), SHIM)

# ---------------------------------------------------------------- offline
SW = """/* Service worker: she studies on the subway, where the site simply did not open.

   Three things this has to get right, each of which it got wrong once:
   - the book itself is precached, not merely cached on use, or the very first
     offline open sits on the loading spinner forever;
   - clips live in a bucket with no version in its name, because they never change
     and wiping 160 MB of downloaded audio over a one-line CSS edit is unforgivable;
   - the precache bypasses the HTTP cache, or a release published inside GitHub
     Pages' ten-minute max-age window pins the *old* files under the *new* version.
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
write(os.path.join(WEB, "index.html"), html)

# The service worker serves data/ cache-first, so the cache key has to move whenever
# the *content* moves too. Keying on the shell alone meant a chapters-only deploy was
# invisible to anyone who had already opened the site — the worst kind of silent bug.
h = hashlib.md5()
for f in ("index.html", "static/app.js", "static/app.css", "static/lookup.js",
          "static/lookup.css", "static/webshim.js", "static/mp3ids.js", "static/stats.js"):
    h.update(read(os.path.join(WEB, f)).encode("utf-8"))
for f in ("data/content.json", "data/word_index.json", "data/conj_index.json", "data/dict.json"):
    p = os.path.join(WEB, f)
    if os.path.exists(p):
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
ver = h.hexdigest()[:8]
write(os.path.join(WEB, "sw.js"), SW.replace("__VER__", ver))
print("sw.js version", ver)

write(os.path.join(WEB, ".nojekyll"), "")
write(os.path.join(WEB, "robots.txt"), "User-agent: *\nDisallow: /\n")
write(os.path.join(WEB, "_headers"),
      "/clip/*\n  Cache-Control: public, max-age=31536000, immutable\n")

total = sum(os.path.getsize(os.path.join(r, f))
            for r, _, fs in os.walk(WEB) for f in fs)
files = sum(len(fs) for _, _, fs in os.walk(WEB))
print("web/: %d files, %.1f MB" % (files, total / 1e6))
