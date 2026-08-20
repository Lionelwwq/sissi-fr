/* Static-hosting shim: maps the desktop app's endpoints onto plain files.
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
