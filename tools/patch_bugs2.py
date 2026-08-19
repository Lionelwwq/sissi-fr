# -*- coding: utf-8 -*-
"""Second batch: the data/rendering defects the sweep confirmed."""
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


patch("app.js", [
    # 11. the numbered dots of a paragraph kept pulsing forever: only .spk was ever cleared
    ("  function clearHL() {\n"
     "    document.querySelectorAll('.spk.playing').forEach(function (e) { e.classList.remove('playing'); });",
     "  function clearHL() {\n"
     "    // dots and table cells take .playing too, and used to keep it for the whole chapter\n"
     "    document.querySelectorAll('.playing').forEach(function (e) { e.classList.remove('playing'); });"),

    # 12. one phrase appears in several topics and shares one aid, so looking the node up
    #     by aid highlighted — and scrolled to — a card in a different topic
    ("  function highlight(aid) {\n"
     "    clearHL();\n"
     "    // model sentences carry data-play, not data-aid — match both or they never light up\n"
     "    var b = document.querySelector('[data-aid=\"' + aid + '\"]') ||\n"
     "            document.querySelector('[data-play=\"' + aid + '\"]');\n"
     "    if (!b) return;",
     "  function highlight(aid, srcEl) {\n"
     "    clearHL();\n"
     "    // model sentences carry data-play, not data-aid — match both or they never light up\n"
     "    var b = srcEl && srcEl.classList ? srcEl : null;\n"
     "    if (!b) {\n"
     "      var all = document.querySelectorAll('[data-aid=\"' + aid + '\"], [data-play=\"' + aid + '\"]');\n"
     "      var near = window.innerHeight / 3, bd = Infinity;\n"
     "      for (var i = 0; i < all.length; i++) {\n"
     "        var d = Math.abs(all[i].getBoundingClientRect().top - near);\n"
     "        if (d < bd) { bd = d; b = all[i]; }\n"
     "      }\n"
     "    }\n"
     "    if (!b) return;"),
    ("  function play(aid, label, fromQueue) {", "  function play(aid, label, fromQueue, srcEl) {"),
    ("    highlight(aid);\n    if (window.tcfStats) window.tcfStats.audio(label);",
     "    highlight(aid, srcEl);\n    if (window.tcfStats) window.tcfStats.audio(label);"),
    ("    if (b) { play(b.dataset.aid, b.dataset.t); return; }",
     "    if (b) { play(b.dataset.aid, b.dataset.t, false, b); return; }"),
    ("    if (p && p.getAttribute('data-play')) { play(p.getAttribute('data-play'), p.textContent.trim().slice(0, 70)); return; }",
     "    if (p && p.getAttribute('data-play')) { play(p.getAttribute('data-play'), p.textContent.trim().slice(0, 70), false, p); return; }"),

    # 13. the 403 clips picked out of the 讲评 had audio but no control anywhere on the page:
    #     model was the one block kind with a `voice` list and no voiceBar
    ("          ((m.notes || []).length ? '<div class=\"mnotes\"><div class=\"mnt\">✍ 讲评 Analyse</div><ol>' +\n"
     "            m.notes.map(function (n) { return '<li>' + rich(n) + '</li>'; }).join('') + '</ol></div>' : '') +\n"
     "          '</div>');",
     "          ((m.notes || []).length ? '<div class=\"mnotes\"><div class=\"mnt\">✍ 讲评 Analyse</div><ol>' +\n"
     "            m.notes.map(function (n) { return '<li>' + rich(n) + '</li>'; }).join('') + '</ol></div>' : '') +\n"
     "          '</div>' + voiceBar(b, bi));"),
])

# 14. the welcome screen still advertised the resource library's old size
patch("index.html", [
    ("第 30 章是<b>视频与听力资源库</b>，91 条都验证过、标了国内点不点得开。",
     "第 30 章是<b>视频与听力资源库</b>，<span id=\"wcRes\">每一条</span>都验证过，标了难度和国内能不能打开。"),
])
patch("app.js", [
    ("    if (store.get('dark', false)) document.body.classList.add('dark');",
     "    /* the welcome screen used to hard-code how many resources there were, and said 91\n"
     "       long after there were 168; count them instead so it cannot drift again */\n"
     "    var wr = $('wcRes');\n"
     "    if (wr) {\n"
     "      var nres = 0, nemb = 0;\n"
     "      d.chapters.forEach(function (c) {\n"
     "        (c.blocks || []).forEach(function (b) {\n"
     "          (b.links || []).forEach(function (x) { nres++; if (x.embed) nemb++; });\n"
     "        });\n"
     "      });\n"
     "      if (nres) wr.textContent = nres + ' 条里 ' + nemb + ' 条能直接在站内播，每一条';\n"
     "    }\n"
     "    if (store.get('dark', false)) document.body.classList.add('dark');"),
])
print("ok")
