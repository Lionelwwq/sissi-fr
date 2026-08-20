# -*- coding: utf-8 -*-
"""lookup.js and stats.js. The study log feeds the daily plan, so every second it
drops is a plan slot that picks the wrong chapter and a streak that breaks for no
reason — these are not cosmetic."""
import io, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")


def patch(name, pairs):
    p = os.path.join(SRC, name)
    t = io.open(p, encoding="utf-8").read()
    for a, b in pairs:
        n = t.count(a)
        assert n == 1, (name, "expected 1 occurrence, found %d" % n, a[:80])
        t = t.replace(a, b)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("patched", name, "-", len(pairs), "edits")


patch("lookup.js", [

    # ---- the long-press guard defeated itself -------------------------------
    # iOS sometimes does send the mouse-event group after a long press. lpStart runs
    # again on that synthetic mousedown, zeroes LP.at, and the click that follows is
    # no longer suppressed — so the sentence plays AND a word lookup hijacks the audio,
    # which is precisely the case the guard was written for. The 700 ms expiry already
    # keeps the window from going stale, so only a real new finger-down should clear it.
    ("  function lpStart(e) {\n"
     "    var pt = e.touches ? e.touches[0] : e;\n"
     "    LP.at = 0;                       // every new gesture starts clean\n",
     "  function lpStart(e) {\n"
     "    var pt = e.touches ? e.touches[0] : e;\n"
     "    if (e.type === 'touchstart') LP.at = 0;   // a real new finger-down, not iOS's synthetic mousedown\n"),

    # ---- a cancelled touch still fired the timer ------------------------------
    ("  document.addEventListener('touchend', lpEnd, true);",
     "  document.addEventListener('touchend', lpEnd, true);\n"
     "  // scroll taking over, or a call arriving, cancels the touch — without this the\n"
     "  // sentence starts reading itself 480 ms later with nobody touching the screen\n"
     "  document.addEventListener('touchcancel', lpEnd, true);"),

    # ---- the iOS unlock could pause a clip that had already started ------------
    ("      var r = au.play();\n"
     "      if (r && r.then) r.then(function () { au.pause(); au.currentTime = 0; if (keep) au.src = keep; })\n"
     "                        .catch(function () {});",
     "      var r = au.play();\n"
     "      if (r && r.then) r.then(function () {\n"
     "        // if a real clip has taken the element over in the meantime, leave it alone —\n"
     "        // this used to be able to silence the very first tap it exists to enable\n"
     "        if (au.src !== SILENT) return;\n"
     "        au.pause(); au.currentTime = 0; if (keep) au.src = keep;\n"
     "      }).catch(function () {});"),

    # ---- 「已加入生词本」 was shown even when the write failed -------------------
    ("      }).then(function () { flash('已加入生词本'); close(); }).catch(function () {});",
     "      }).then(function (r) { return r && r.json ? r.json().catch(function () { return {}; }) : {}; })\n"
     "        .then(function (d) {\n"
     "          // storage full on an iPhone is silent otherwise: she is told it saved and it did not\n"
     "          if (d && d.ok === false) { flash('存不下了，手机存储空间可能满了'); return; }\n"
     "          flash('已加入生词本'); close();\n"
     "        }).catch(function () { flash('没能加入生词本'); });"),
])


patch("stats.js", [

    # ---- save() was always deferred 400 ms, including the save that pagehide
    # schedules — and a closed tab never reaches that timer. Measured: the chapter's
    # seconds written at pagehide were 0 where they should have been 5. Losing the
    # last stretch of every session also keeps quiet days under the 60 s the streak
    # needs, so the 🔥 count breaks on its own.
    ("  var saveTimer = null;\n"
     "  function save() {\n"
     "    clearTimeout(saveTimer);\n"
     "    saveTimer = setTimeout(function () {\n"
     "      try { localStorage.setItem(KEY, JSON.stringify(S)); }\n"
     "      catch (e) {                       // quota: drop the trail, keep the totals\n"
     "        S.recent = S.recent.slice(-60);\n"
     "        S.links = S.links.slice(-60);\n"
     "        try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e2) {}\n"
     "      }\n"
     "    }, 400);\n"
     "  }",
     "  var saveTimer = null;\n"
     "  function writeNow() {\n"
     "    clearTimeout(saveTimer);\n"
     "    saveTimer = null;\n"
     "    mine = true;\n"
     "    try { localStorage.setItem(KEY, JSON.stringify(S)); }\n"
     "    catch (e) {                       // quota: drop the trail, keep the totals\n"
     "      S.recent = S.recent.slice(-60);\n"
     "      S.links = S.links.slice(-60);\n"
     "      try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e2) {}\n"
     "    }\n"
     "    mine = false;\n"
     "  }\n"
     "  /* now=true writes synchronously. The page is about to be frozen or closed, and a\n"
     "     400 ms timer is 400 ms the tab does not have. */\n"
     "  function save(now) {\n"
     "    if (now) { writeNow(); return; }\n"
     "    clearTimeout(saveTimer);\n"
     "    saveTimer = setTimeout(writeNow, 400);\n"
     "  }\n"
     "  /* A second tab holds the whole log in memory too, and writes it back wholesale.\n"
     "     Without this the tab that saves last erases whatever the other one recorded. */\n"
     "  var mine = false;\n"
     "  window.addEventListener('storage', function (e) {\n"
     "    if (e.key !== KEY || mine) return;\n"
     "    if (saveTimer) writeNow();        // bank ours first, then take theirs\n"
     "    else S = null;\n"
     "  });"),

    # ---- pagehide forgot which chapter she was on, and nothing ever re-armed it.
    # On an iPhone pagehide fires on the first app switch, so from then on the session
    # recorded nothing at all.
    ("  document.addEventListener('visibilitychange', function () {\n"
     "    if (document.hidden) flush(); else if (cur) since = Date.now();\n"
     "  });\n"
     "  window.addEventListener('pagehide', closeOut);",
     "  document.addEventListener('visibilitychange', function () {\n"
     "    if (document.hidden) { flush(); save(true); } else if (cur) since = Date.now();\n"
     "  });\n"
     "  /* pagehide is not necessarily the end: on iOS it fires every time she switches\n"
     "     apps and the page goes into the back/forward cache. closeOut() cleared the\n"
     "     current chapter and nothing put it back, so nothing she read after the first\n"
     "     app switch was ever counted. Bank the time, keep the chapter, and re-arm when\n"
     "     the page comes back. */\n"
     "  window.addEventListener('pagehide', function () { flush(); save(true); });\n"
     "  window.addEventListener('pageshow', function () { if (cur) since = Date.now(); });\n"
     "  /* One sitting longer than an hour used to be thrown away whole rather than\n"
     "     clamped. Bank it every minute instead — but only while she is actually here,\n"
     "     so a tab forgotten on a desk still does not invent study time. */\n"
     "  var lastAct = Date.now();\n"
     "  ['pointerdown', 'keydown', 'touchstart', 'wheel'].forEach(function (ev) {\n"
     "    document.addEventListener(ev, function () { lastAct = Date.now(); }, true);\n"
     "  });\n"
     "  setInterval(function () {\n"
     "    if (!document.hidden && cur && Date.now() - lastAct < 3e5) flush();\n"
     "  }, 60000);"),
])
print("ok")
