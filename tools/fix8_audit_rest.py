# -*- coding: utf-8 -*-
"""The rest of the confirmed audit findings.

The ⋯ menu one is the reason this file exists: I measured it as "visible and
hittable" earlier and said so. That measurement was wrong — getBoundingClientRect
still reports the layout box of a clipped element, and my hit test landed on a
topbar button I mistook for a menu item. Hit-testing each item at its own centre
with the welcome overlay dismissed returns .chead every time: the menu is painted
nowhere and reachable nowhere."""
import io, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")


def patch(path, pairs, label=None):
    t = io.open(path, encoding="utf-8").read()
    for a, b in pairs:
        n = t.count(a)
        assert n == 1, (os.path.basename(path), "expected 1 occurrence, found %d" % n, a[:80])
        t = t.replace(a, b)
    io.open(path, "w", encoding="utf-8", newline="\n").write(t)
    print("patched", label or os.path.basename(path), "-", len(pairs), "edits")


# ---------------------------------------------------------------- app.css
patch(os.path.join(SRC, "app.css"), [

    # ---- the ⋯ menu was clipped out of existence on every phone --------------
    # .topbar scrolls sideways (overflow:auto), which also clips its descendants.
    # #moreMenu is position:absolute inside it, so 生词本 / 笔记本 / 学习记录 / 夜间模式
    # were laid out at y=66..257 and painted nowhere. position:fixed escapes the
    # clip; app.js sets the coordinates when it opens.
    ("#moreMenu{position:absolute;right:0;top:calc(100% + 8px);background:var(--card);",
     "#moreMenu{position:fixed;background:var(--card);"),

    # ---- ⏹ was hidden on phones, and ▶ cannot reach lookup-owned audio -------
    # A tapped word or a long-pressed sentence plays from lookup.js's own element.
    # With ⏹ gone the only stop control was ▶, which does not know about it and
    # started a whole-chapter read-aloud on top instead.
    ("  #player #pStop{display:none}\n",
     "  /* ⏹ is NOT redundant: a tapped word plays from lookup.js's element, which ▶\n"
     "     cannot reach. Keep it and shrink it instead. */\n"
     "  #player #pStop{min-width:38px;padding:0 4px}\n"),

    # ---- dark mode kept light-mode-only text colours on the 第 30 章 badges ----
    ("body.dark .lcn.ok{background:#173324}\n"
     "body.dark .lcn.vpn{background:#3a2a18}",
     "body.dark .lcn.ok{background:#173324;color:#6ee7a4}\n"
     "body.dark .lcn.vpn{background:#3a2a18;color:#f0b476}"),

    # ---- …and on the A2 / B1 / B2 filter chips -------------------------------
    ("body.dark .lgo{color:var(--accent)}",
     "body.dark .lgo{color:var(--accent)}\n"
     "/* the level chips carry their colour inline for light mode; on #182131 those\n"
     "   greens and blues sit at 2.5-3.2:1, so the whole filter row is unreadable */\n"
     "body.dark .lfb.lv-A2{border-color:#3fa96e;color:#6ee7a4}\n"
     "body.dark .lfb.lv-B1{border-color:#4a9fd8;color:#8ecbf5}\n"
     "body.dark .lfb.lv-B2{border-color:#d08a3c;color:#f0b476}\n"
     "body.dark .lv-A2{background:#1b7a45;color:#fff}\n"
     "body.dark .lv-B1{background:#1d6fa5;color:#fff}\n"
     "body.dark .lv-B2{background:#8a3f07;color:#fff}"),

    # ---- a ticked plan row was dimmed until it could not be read -------------
    (".dpi.ok{opacity:.55}",
     "/* done, not gone: .55 took the row under 3:1. The tick and the strike-through\n"
     "   already say it is finished. */\n"
     ".dpi.ok{opacity:.82}"),
    (".dpring i{font-size:12px;font-style:normal;opacity:.7}",
     ".dpring i{font-size:12px;font-style:normal;opacity:.88}"),
])


# ---------------------------------------------------------------- app.js
patch(os.path.join(SRC, "app.js"), [

    # ---- position the (now fixed) ⋯ menu under its button --------------------
    ("  $('btnMore').onclick = function (e) { e.stopPropagation(); $('moreMenu').classList.toggle('hidden'); };",
     "  $('btnMore').onclick = function (e) {\n"
     "    e.stopPropagation();\n"
     "    var m = $('moreMenu');\n"
     "    // fixed positioning is what gets it out of the toolbar's overflow clip, so the\n"
     "    // coordinates have to come from here rather than from CSS\n"
     "    var r = this.getBoundingClientRect();\n"
     "    m.style.top = Math.round(r.bottom + 8) + 'px';\n"
     "    m.style.right = Math.round(window.innerWidth - r.right) + 'px';\n"
     "    m.classList.toggle('hidden');\n"
     "  };"),

    # ---- offline, one tap on 朗读本章 burned through every clip in the chapter --
    ("  au.addEventListener('error', function () {\n"
     "    if (QI >= 0 && QI < QUEUE.length - 1) { QI++; playQueueItem(); return; }",
     "  var missRun = 0;\n"
     "  au.addEventListener('error', function () {\n"
     "    /* Offline on a chapter she has not downloaded, every clip 404s instantly and\n"
     "       the queue used to walk all ~200-400 of them in one synchronous burst. Stop\n"
     "       after a few and say why — the status text is display:none on phones. */\n"
     "    if (++missRun >= 4) {\n"
     "      missRun = 0; dropQueue(); ARMED = false; clearHL();\n"
     "      $('pPlay').textContent = '▶';\n"
     "      $('pNow').textContent = '这一章的发音还没下载';\n"
     "      toast('这一章的发音还没下载，连上网再点一次');\n"
     "      return;\n"
     "    }\n"
     "    if (QI >= 0 && QI < QUEUE.length - 1) { QI++; setTimeout(playQueueItem, 120); return; }"),

    ("    au.play().then(function () {\n"
     "      // count it only once it actually made a sound\n"
     "      if (mine === PLAY_SEQ && window.tcfStats) window.tcfStats.audio(label);",
     "    au.play().then(function () {\n"
     "      // count it only once it actually made a sound\n"
     "      missRun = 0;\n"
     "      if (mine === PLAY_SEQ && window.tcfStats) window.tcfStats.audio(label);"),

    # ---- ▶ used to talk over a word that lookup.js was already playing --------
    ("  $('pPlay').onclick = function () {\n"
     "    if (au.paused) { if (ARMED && au.src) { au.play(); this.textContent = '⏸'; } else startQueue(currentClips(), 0); }\n"
     "    else { au.pause(); this.textContent = '▶'; }\n"
     "  };",
     "  $('pPlay').onclick = function () {\n"
     "    // a tapped word plays from lookup.js's own element; starting a whole-chapter\n"
     "    // read-aloud on top of it is never what she meant by pressing ▶\n"
     "    if (au.paused && window.tcfLookup && window.tcfLookup.busy && window.tcfLookup.busy()) {\n"
     "      window.tcfLookup.stop();\n"
     "      $('pNow').textContent = '已停下';\n"
     "      return;\n"
     "    }\n"
     "    if (au.paused) { if (ARMED && au.src) { au.play(); this.textContent = '⏸'; } else startQueue(currentClips(), 0); }\n"
     "    else { au.pause(); this.textContent = '▶'; }\n"
     "  };"),

    # ---- the plan showed 「今天还没开始」 while she was mid-session ---------------
    ("  function planRender() {\n"
     "    var p = store.get('plan', {});",
     "  function planRender() {\n"
     "    // bank the minutes she is accumulating right now, or the panel reports the\n"
     "    // last save instead of the truth\n"
     "    if (window.tcfStats && window.tcfStats.bank) window.tcfStats.bank();\n"
     "    var p = store.get('plan', {});"),
])


# ---------------------------------------------------------------- lookup.js
patch(os.path.join(SRC, "lookup.js"), [

    # ---- 「▶ 播放整句」 was announced even when nothing played --------------------
    ("      au.playbackRate = rate();\n"
     "      au.play().catch(function () {});\n"
     "      flash('▶ 播放整句');",
     "      au.playbackRate = rate();\n"
     "      au.play().then(function () { flash('▶ 播放整句'); }, function (e) {\n"
     "        // offline on a chapter she has not downloaded, this said 「播放整句」 and was\n"
     "        // silent — indistinguishable from the app being broken\n"
     "        if (e && e.name === 'AbortError') return;\n"
     "        flash('这一句还没下载，连上网再试');\n"
     "      });"),

    # ---- let the player bar find out that we own the audio -------------------
    ("  window.tcfLookup = { lookup: lookup, play: playWord, stop: function () {",
     "  window.tcfLookup = { lookup: lookup, play: playWord,\n"
     "    busy: function () { return !!au.src && !au.paused && !au.ended; },\n"
     "    stop: function () {"),
])


# ---------------------------------------------------------------- stats.js
patch(os.path.join(SRC, "stats.js"), [

    # ---- records written before this release have no `key` -------------------
    # planSpec filters on chIndexByKey(c.key); an undefined key returns -1, so her
    # whole reading history was silently invisible to the 复习 slot after upgrading.
    ("    for (var k in blank()) if (S[k] === undefined) S[k] = blank()[k];\n"
     "    return S;",
     "    for (var k in blank()) if (S[k] === undefined) S[k] = blank()[k];\n"
     "    /* Chapter records written before the daily plan existed have no `key`, and the\n"
     "       plan looks chapters up by it — without this migration her entire history is\n"
     "       invisible to 复习 the first time she opens the new version. */\n"
     "    for (var ck in S.chapters) if (S.chapters[ck] && !S.chapters[ck].key) S.chapters[ck].key = ck;\n"
     "    return S;"),

    ("  window.tcfStats = { view: view, audio: audio, word: word, link: link, flash: flash,",
     "  window.tcfStats = { view: view, audio: audio, word: word, link: link, flash: flash,\n"
     "                      bank: flush,"),
])


# ---------------------------------------------------------------- serve.py (the exe)
patch(os.path.join(HERE, "serve.py"), [
    # Same problem build_web.py had: these paths describe the old scratchpad layout,
    # so serve.py could not start from the repo either.
    ("BASE = base_dir()\n"
     "DATA = os.path.join(BASE, \"data\")\n"
     "if not os.path.isdir(DATA):\n"
     "    DATA = BASE                      # frozen build keeps the packs flat\n"
     "STATIC = os.path.join(BASE, \"static\")",
     "BASE = base_dir()\n"
     "REPO = os.path.dirname(BASE)         # unfrozen, serve.py lives in <repo>/tools\n"
     "DATA = os.path.join(BASE, \"data\")\n"
     "if not os.path.isdir(DATA):\n"
     "    DATA = BASE                      # frozen build keeps the packs flat\n"
     "if not os.path.exists(os.path.join(DATA, \"content.json\")) and \\\n"
     "        os.path.exists(os.path.join(REPO, \"data\", \"content.json\")):\n"
     "    DATA = os.path.join(REPO, \"data\")\n"
     "STATIC = os.path.join(BASE, \"static\")\n"
     "if not os.path.isdir(STATIC):\n"
     "    STATIC = os.path.join(BASE, \"src\")   # the desktop sources live in tools/src\n"
     "CLIPDIR = os.path.join(REPO, \"clip\")     # clips are unpacked in the repo, not zipped"),

    ("def send_clip(names, member_base):\n"
     "    \"\"\"Look for <base>.<ext> across the given packs and stream the first hit.\"\"\"\n"
     "    for name in names:",
     "def send_clip(names, member_base):\n"
     "    \"\"\"Look for <base>.<ext> across the given packs and stream the first hit.\"\"\"\n"
     "    # running from the repo there are no zips, just clip/<id>.mp3\n"
     "    for ext in (\".mp3\", \".opus\"):\n"
     "        p = os.path.join(CLIPDIR, member_base + ext)\n"
     "        if os.path.exists(p):\n"
     "            with open(p, \"rb\") as f:\n"
     "                blob = f.read()\n"
     "            r = Response(blob, mimetype=MIME[ext])\n"
     "            r.headers[\"Cache-Control\"] = \"public, max-age=604800\"\n"
     "            r.headers[\"Content-Length\"] = str(len(blob))\n"
     "            return r\n"
     "    for name in names:"),
])

print("ok")
