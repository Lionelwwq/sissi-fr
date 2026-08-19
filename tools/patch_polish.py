# -*- coding: utf-8 -*-
"""Small corrections found while testing the batch above."""
import io, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


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
    # the prose dots show a number; the player bar was announcing "3" instead of the sentence
    ("    if (p && p.getAttribute('data-play')) { play(p.getAttribute('data-play'), p.textContent.trim().slice(0, 70), false, p); return; }",
     "    if (p && p.getAttribute('data-play')) {\n"
     "      play(p.getAttribute('data-play'), (p.getAttribute('title') || p.textContent).trim().slice(0, 70), false, p);\n"
     "      return;\n"
     "    }"),
    # she may arrive without the page having scrolled; give the outline time to be seen
    ("    setTimeout(function () { a.classList.remove('spot'); }, 3000);",
     "    setTimeout(function () { a.classList.remove('spot'); }, 6000);"),
    ("      '<span>今天已学 ' + (s ? s.mins(sec) : '0 秒') +",
     "      '<span>' + (sec < 30 ? '今天还没开始' : '今天已学 ' + s.mins(sec)) +"),
    ("           (pk.x.how ? '　·　' + String(pk.x.how).replace(/<[^>]+>/g, '').slice(0, 64) : ''),",
     "           (pk.x.how ? '　·　' + cut(String(pk.x.how).replace(/<[^>]+>/g, ''), 64) : ''),"),
    ("        s: String(nc.intro || '').slice(0, 62), b: '开始读', go: function () { planGo(ni); } });",
     "        s: cut(String(nc.intro || ''), 62), b: '开始读', go: function () { planGo(ni); } });"),
    ("  function planBuild(vocab) {",
     "  function cut(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }\n"
     "  function planBuild(vocab) {"),
])
print("ok")
