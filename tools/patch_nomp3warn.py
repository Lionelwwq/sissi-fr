# -*- coding: utf-8 -*-
"""Every clip is mp3 now, so the Opus warning has become a lie on exactly the
devices it was written for: an old iPhone would be told the sound will not work
while it plays perfectly."""
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
    ("  /* 89% of the clips are Ogg/Opus. Safari only learned that container in 17.4, and\n"
     "     a silent decode failure is indistinguishable from \"the app is broken\". */\n"
     "  var CAN_OPUS = (function () {\n"
     "    try { return !!document.createElement('audio').canPlayType('audio/ogg; codecs=opus'); }\n"
     "    catch (e) { return true; }\n"
     "  })();\n",
     "  /* All 19,574 clips are mp3. They used to be 89% Ogg/Opus, which Safari only learned\n"
     "     in 17.4 — on an older iPhone a third of the book was silent with no explanation. */\n"),
    ("      toast(CAN_OPUS ? '这一条没能播放，换一句试试' : '这个浏览器不支持本站的音频格式');",
     "      toast('这一条没能播放，换一句试试');"),
    ("    $('pNow').textContent = CAN_OPUS ? '播放失败' : '浏览器不支持这种音频格式';",
     "    $('pNow').textContent = '播放失败';"),
    ("    if (!CAN_OPUS) {\n"
     "      document.body.classList.add('nosound');\n"
     "      $('nosound').innerHTML = '🔇 <b>这个浏览器放不出本站的发音。</b><br>' +\n"
     "        '绝大部分音频是 Opus 格式，Safari 要 <b>iOS 17.4 / macOS 14.4</b> 以上才支持。' +\n"
     "        '请升级系统，或换 Chrome / Edge 打开，课文和词典不受影响。';\n"
     "    }\n", ""),
])
print("ok")
