# -*- coding: utf-8 -*-
"""Fixes for the defects the adversarial sweep turned up.

Every edit asserts that its anchor appears exactly once, so a silent no-op —
the way a "fix" ships without fixing anything — cannot happen.
"""
import io, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "static")


def patch(name, pairs):
    p = os.path.join(S, name)
    t = io.open(p, encoding="utf-8").read()
    for a, b in pairs:
        n = t.count(a)
        assert n == 1, (name, n, a[:70])
        t = t.replace(a, b)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("patched", name, len(pairs), "edits")


# ---------------------------------------------------------------- lookup.js
patch("lookup.js", [
    # 1. the long press plays before any touchend exists, so the element was still locked
    ("  document.addEventListener('touchend', unlock, true);",
     "  document.addEventListener('touchstart', unlock, true);   // a long press plays before touchend ever fires\n"
     "  document.addEventListener('touchend', unlock, true);"),

    # 2. a rejected promise was cached forever: one bad fetch and tapping words died for the session
    ("    ]).then(function (a) { DICT = a[0]; WORDS = a[1]; CONJ = a[2] || {}; });",
     "    ]).then(function (a) { DICT = a[0]; WORDS = a[1]; CONJ = a[2] || {}; },\n"
     "            function (e) { loading = null; throw e; });"),

    # 3. one clip at a time — across both scripts, and cancellable
    ("  var pop = null;",
     "  var pop = null;\n"
     "  /* Two scripts each held their own audio element and neither knew about the other,\n"
     "     so a tapped word played on top of the chapter being read aloud and the player's\n"
     "     stop button could not reach it. A sequence also kept its onended handler after\n"
     "     being interrupted, and quietly resumed once the interrupting clip finished. */\n"
     "  var SEQ = 0;\n"
     "  function takeAudio() {\n"
     "    SEQ++;\n"
     "    au.onended = null; au.onerror = null;\n"
     "    try { au.pause(); } catch (e) {}\n"
     "    if (window.tcfAudio) window.tcfAudio.stop();\n"
     "  }"),
    ("    if (!id) { flash('这个词没有单独录音'); return; }\n    au.pause();",
     "    if (!id) { flash('这个词没有单独录音'); return; }\n    takeAudio();"),
    ("    var i = 0;\n    (function step() {\n      if (i >= ids.length) return;",
     "    takeAudio();\n    var mine = SEQ, i = 0;\n    (function step() {\n"
     "      if (mine !== SEQ || i >= ids.length) return;"),

    # 4. the card's own handlers never ran: the capture listener swallowed the click first
    ("  var DEAD = 'button, a, input, textarea, select, .spk, .wp-head, .wp-foot';",
     "  var DEAD = 'button, a, input, textarea, select, .spk, .wp-head, .wp-foot, [data-say]';"),

    # 5. a sticky boolean ate the next real tap whenever iOS skipped the click
    ("  var LP = { timer: null, x: 0, y: 0, fired: false };",
     "  var LP = { timer: null, x: 0, y: 0, at: 0 };"),
    ("    var host = e.target.closest && e.target.closest(ZONES);\n"
     "    if (!host || (e.target.closest && e.target.closest(DEAD))) return;",
     "    LP.at = 0;                       // every new gesture starts clean\n"
     "    var host = e.target.closest && e.target.closest(ZONES);\n"
     "    if (!host || (e.target.closest && e.target.closest(DEAD))) return;"),
    ("    LP.fired = false; LP.x = pt.clientX; LP.y = pt.clientY;",
     "    LP.x = pt.clientX; LP.y = pt.clientY;"),
    ("      LP.fired = true;\n      close();\n      au.pause();",
     "      LP.at = Date.now();\n      close();\n      takeAudio();"),
    ("    if (LP.fired) { LP.fired = false; e.preventDefault(); e.stopPropagation(); return; }",
     "    // iOS does not reliably send a click after a long press; this window expires by itself\n"
     "    if (Date.now() - LP.at < 700) { LP.at = 0; e.preventDefault(); e.stopPropagation(); return; }"),

    # 6. say something when the dictionary is not there, instead of doing nothing
    ("  function lookup(word, x, y, extra) {\n    load().then(function () {",
     "  function dictFail() { flash('词典还没下载好，连上网再点一次'); }\n"
     "  function lookup(word, x, y, extra) {\n    load().then(function () {"),
    ("      card(DICT[keyOf(word)], word, x, y, extra);\n    });\n  }",
     "      card(DICT[keyOf(word)], word, x, y, extra);\n    }).catch(dictFail);\n  }"),
    ("          card(known[0] || null, words[0], e.clientX, e.clientY, list);\n        });",
     "          card(known[0] || null, words[0], e.clientX, e.clientY, list);\n        }).catch(dictFail);"),
    ("      lookup(w, e.clientX, e.clientY);\n    });",
     "      lookup(w, e.clientX, e.clientY);\n    }).catch(dictFail);"),

    # 7. let the player bar reach this element too
    ("  window.tcfLookup = { lookup: lookup, play: playWord };",
     "  window.tcfLookup = { lookup: lookup, play: playWord, stop: function () {\n"
     "    SEQ++; au.onended = null; au.onerror = null;\n"
     "    try { au.pause(); au.currentTime = 0; } catch (e) {}\n"
     "  } };"),
])

# ---------------------------------------------------------------- app.js
patch("app.js", [
    # 8. the big play button replayed the previous chapter: au.src outlives its chapter
    ("  var PLAY_SEQ = 0, VIEW = 'chapter', HITS = [];",
     "  var PLAY_SEQ = 0, VIEW = 'chapter', HITS = [], ARMED = false;"),
    ("  function stopAll() {\n    dropQueue();\n    REP2 = false;\n"
     "    try { au.pause(); au.currentTime = 0; } catch (e) {}",
     "  function stopAll(keepLookup) {\n    dropQueue();\n    REP2 = false;\n    ARMED = false;\n"
     "    try { au.pause(); au.currentTime = 0; } catch (e) {}\n"
     "    // the word / long-press clip lives in lookup.js and used to survive every stop\n"
     "    if (!keepLookup && window.tcfLookup && window.tcfLookup.stop) window.tcfLookup.stop();"),
    ("    if (!fromQueue) dropQueue();\n    REP2 = false;\n    au.pause();",
     "    if (!fromQueue) dropQueue();\n    REP2 = false;\n    ARMED = true;\n"
     "    if (window.tcfLookup && window.tcfLookup.stop) window.tcfLookup.stop();\n    au.pause();"),
    ("    if (au.paused) { if (au.src) { au.play(); this.textContent = '⏸'; } else startQueue(currentClips(), 0); }",
     "    if (au.paused) { if (ARMED && au.src) { au.play(); this.textContent = '⏸'; } else startQueue(currentClips(), 0); }"),
    ("  $('pStop').onclick = function () { au.pause(); au.currentTime = 0; QI = -1; clearHL(); $('pPlay').textContent = '▶'; };",
     "  $('pStop').onclick = function () { stopAll(); };"),
    # lookup.js needs a way in that does not bounce straight back out
    ("  var $ = function (id) { return document.getElementById(id); };",
     "  var $ = function (id) { return document.getElementById(id); };\n"
     "  window.tcfAudio = { stop: function () { stopAll(true); } };"),

    # 9. offline, or a half-downloaded book, left the spinner on screen forever
    ("    if (last > 0) toast('接着上次：第 ' + d.chapters[last].no + ' 章');\n  });",
     "    if (last > 0) toast('接着上次：第 ' + d.chapters[last].no + ' 章');\n"
     "  }).catch(function () {\n"
     "    $('wrap').innerHTML = '<div class=\"loadfail\"><div class=\"lf-i\">\U0001F4E1</div>' +\n"
     "      '<div class=\"lf-t\">课文没能载入</div>' +\n"
     "      '<div class=\"lf-s\">多半是网络断了。连上网之后点下面重试；<br>如果之前完整打开过一次，离线也应该能进。</div>' +\n"
     "      '<button class=\"btn pri\" id=\"lfGo\">重新载入</button></div>';\n"
     "    $('lfGo').onclick = function () { location.reload(); };\n"
     "  });"),
])

# ---------------------------------------------------------------- stats.js
patch("stats.js", [
    # 10. switching to WeChat and back stopped the clock for good: cur was cleared, never restored
    ("  var cur = null, since = 0;\n  function closeOut() {\n    if (!cur) return;",
     "  var cur = null, since = 0;\n"
     "  /* flush banks the time but keeps the chapter; closeOut also forgets it. Sending the\n"
     "     phone to the background used to closeOut, so nothing she read after the first app\n"
     "     switch of the session was ever counted. */\n"
     "  function flush() {\n    if (!cur) return;"),
    ("      S.lastTs = Date.now();\n      save();\n    }\n    cur = null;\n  }",
     "      S.lastTs = Date.now();\n      save();\n    }\n    since = Date.now();\n  }\n"
     "  function closeOut() { flush(); cur = null; }"),
    ("    if (document.hidden) closeOut(); else if (cur) since = Date.now();",
     "    if (document.hidden) flush(); else if (cur) since = Date.now();"),
])
print("ok")
