# -*- coding: utf-8 -*-
"""New feature: 句子笔记本.

The vocabulary book collects single words. What she kept asking for is the other
half — mark a whole sentence she wants to be able to say, and keep it. Select any
text in the reading pane, a small pill appears under the selection, one tap files it
away with the chapter it came from and its audio, if the sentence has any.

Storage is localStorage, like the study log and the daily plan. The vocabulary book
goes through /api/vocab/* only for historical reasons; notes do not need a server,
so this works identically in the exe and on the hosted copy."""
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


# ---------------------------------------------------------------- markup
patch("index.html", [
    ('      <button class="btn" id="btnVocab">📒 生词本</button>',
     '      <button class="btn" id="btnVocab">📒 生词本</button>\n'
     '      <button class="btn" id="btnNotes">📓 笔记本<i class="dot hidden" id="notesDot"></i></button>'),

    ('<div id="vbwrap" class="hidden">',
     '<div id="nbwrap" class="hidden">\n'
     '  <div class="vb">\n'
     '    <div class="vbh"><b>📓 笔记本</b><span id="nbN" class="vbn"></span>\n'
     '      <span class="spacer"></span>\n'
     '      <button class="btn" id="nbCopy">复制全部</button>\n'
     '      <button class="btn" id="nbClose">✕ 关闭</button></div>\n'
     '    <div id="nbList" class="vbl"></div>\n'
     '  </div>\n'
     '</div>\n'
     '\n'
     '<div id="selchip" class="hidden">\n'
     '  <button class="scb" id="scSay">🔊</button>\n'
     '  <button class="scb pri" id="scAdd">📓 存进笔记本</button>\n'
     '</div>\n'
     '\n'
     '<div id="vbwrap" class="hidden">'),

    ('<b>📊 学习记录</b>会记下你看了哪章、查了哪些词、点开过哪些视频——只存在这台设备上，<b>不会自动发给任何人</b>。</div>',
     '<b>看到想记住的句子，用手指划选它</b>，下面会冒出「📓 存进笔记本」——存下来的句子随时能重听、能跳回原文。<br>'
     '<b>📊 学习记录</b>会记下你看了哪章、查了哪些词、点开过哪些视频——只存在这台设备上，<b>不会自动发给任何人</b>。</div>'),
])


# ---------------------------------------------------------------- styles
CSS = """
/* ---------- 句子笔记本 ---------- */
/* The pill sits BELOW the selection: iOS puts its own Copy / Look Up bar above one,
   and two floating bars fighting for the same 40 px is how a feature gets abandoned. */
#selchip{position:fixed;z-index:500;display:flex;gap:6px;padding:5px;border-radius:12px;
         background:var(--card);border:1px solid var(--line);box-shadow:var(--shadow-lg)}
#selchip.hidden{display:none!important}
.scb{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:9px;
     padding:9px 12px;font-size:13.5px;font-family:inherit;cursor:pointer;white-space:nowrap;
     min-height:40px}
.scb.pri{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
body.dark .scb.pri{color:#0e1420}
#selchip .scb:active{transform:translateY(1px)}

#nbwrap{position:fixed;top:0;right:0;bottom:0;left:0;inset:0;background:rgba(10,16,26,.86);
        z-index:210;display:flex;align-items:center;justify-content:center;padding:20px}
#nbwrap.hidden{display:none!important}
.nbi{border-bottom:1px solid var(--line);padding:11px 5px;display:flex;gap:10px;align-items:flex-start}
.nbi:last-child{border-bottom:0}
.nbc{flex:1;min-width:0}
.nbfr{font-size:15.5px;line-height:1.6;letter-spacing:.15px}
.nbzh{font-size:13.5px;color:var(--muted);margin-top:3px}
.nbsrc{font-size:12px;color:var(--muted);margin-top:5px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.nbsrc button{border:0;background:none;color:var(--accent);font-size:12px;font-family:inherit;
              cursor:pointer;padding:4px 2px;min-height:32px}
.nbact{flex:0 0 auto;display:flex;flex-direction:column;gap:4px}
.nbact button{border:1px solid var(--line);background:var(--card);border-radius:9px;
              width:40px;height:40px;font-size:15px;cursor:pointer;color:var(--ink)}
/* the sentence she jumped back to has to be findable in a screen of French */
.spotx{outline:3px solid var(--accent);outline-offset:3px;border-radius:6px;
       background:var(--accent-soft)}
"""

p = os.path.join(SRC, "app.css")
t = io.open(p, encoding="utf-8").read()
assert "#selchip" not in t, "already patched"
io.open(p, "w", encoding="utf-8", newline="\n").write(t + CSS)
print("appended 句子笔记本 styles to app.css")


# ---------------------------------------------------------------- behaviour
JS = """
  /* ---------------- 句子笔记本 ----------------
     生词本收的是词，这里收的是整句：划选任意一段法语，下面冒出「📓 存进笔记本」。
     存下来的句子带着出处和录音，随时能重听、能跳回原文。全部只存在这台设备上。 */
  var NOTES = store.get('notes', []);
  if (!Array.isArray(NOTES)) NOTES = [];
  function notesSave() { store.set('notes', NOTES.slice(-500)); }
  function notesDot() {
    var d = $('notesDot');
    if (d) d.classList.toggle('hidden', !NOTES.length);
  }

  // what she selected, plus where it came from
  function selInfo() {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    var txt = sel.toString().replace(/\\s+/g, ' ').trim();
    if (txt.length < 4 || txt.length > 400) return null;
    var node = sel.anchorNode;
    var el = node && (node.nodeType === 1 ? node : node.parentElement);
    if (!el || !el.closest || !el.closest('#wrap')) return null;
    var host = el.closest('[data-play],[data-aid]');
    var aid = host ? (host.getAttribute('data-play') || host.getAttribute('data-aid')) : '';
    var card = el.closest('.b-card,.dl,.pcard,.mline,.dtx');
    var zh = '';
    if (card) {
      var z = card.querySelector('.cz,.dzh,.exzh,.zh');
      if (z) zh = z.textContent.trim().slice(0, 160);
    }
    var r;
    try { r = sel.getRangeAt(0).getBoundingClientRect(); } catch (e) { return null; }
    if (!r || (!r.width && !r.height)) return null;
    return { t: txt, aid: aid || '', zh: zh, rect: r };
  }

  var SEL = null;
  function chipHide() { SEL = null; $('selchip').classList.add('hidden'); }
  function chipShow() {
    var info = selInfo();
    if (!info) { chipHide(); return; }
    SEL = info;
    var chip = $('selchip');
    chip.classList.remove('hidden');
    $('scSay').classList.toggle('hidden', !info.aid);
    var w = chip.offsetWidth, h = chip.offsetHeight;
    var left = Math.min(Math.max(8, info.rect.left + info.rect.width / 2 - w / 2), window.innerWidth - w - 8);
    var top = info.rect.bottom + 10;
    if (top + h > window.innerHeight - 70) top = Math.max(8, info.rect.top - h - 10);
    chip.style.left = left + 'px';
    chip.style.top = top + 'px';
  }
  var chipTimer = null;
  document.addEventListener('selectionchange', function () {
    clearTimeout(chipTimer);
    // wait for the drag to settle, or the pill jitters along with her finger
    chipTimer = setTimeout(chipShow, 220);
  });
  $('main').addEventListener('scroll', chipHide, { passive: true });
  $('scSay').onclick = function (e) {
    e.stopPropagation();
    if (SEL && SEL.aid) play(SEL.aid, SEL.t.slice(0, 60));
  };
  $('scAdd').onclick = function (e) {
    e.stopPropagation();
    if (!SEL) return;
    var c = DOC && DOC.chapters[CUR];
    if (NOTES.some(function (x) { return x.t === SEL.t; })) { toast('这句已经在笔记本里了'); chipHide(); return; }
    NOTES.push({ t: SEL.t, zh: SEL.zh, aid: SEL.aid, ts: Date.now(),
                 key: c ? (c.key || ('ch' + c.no)) : '', no: c ? c.no : 0, ch: c ? c.zh : '' });
    notesSave(); notesDot();
    toast('已存进笔记本，共 ' + NOTES.length + ' 句');
    try { window.getSelection().removeAllRanges(); } catch (err) {}
    chipHide();
  };

  function spotSentence(aid, text) {
    var el = aid ? document.querySelector('#wrap [data-play="' + aid + '"], #wrap [data-aid="' + aid + '"]') : null;
    if (!el && text) {
      var probe = text.slice(0, 24);
      var all = document.querySelectorAll('#wrap .frtext, #wrap .mline, #wrap .cf, #wrap .b-para, #wrap .dtx');
      for (var i = 0; i < all.length; i++) {
        if (all[i].textContent.indexOf(probe) >= 0) { el = all[i]; break; }
      }
    }
    if (!el) { toast('这一句在本章里找不到了'); return; }
    el.scrollIntoView({ block: 'center' });
    el.classList.add('spotx');
    setTimeout(function () { el.classList.remove('spotx'); }, 6000);
  }

  function nbRender() {
    $('nbN').textContent = NOTES.length ? NOTES.length + ' 句' : '';
    if (!NOTES.length) {
      $('nbList').innerHTML = '<div class="vbe">还是空的。<br><br>' +
        '看书时用手指<b>划选</b>一句想记住的法语，下面会冒出「📓 存进笔记本」。' +
        '存下来的句子带着出处和录音，随时能重听、能跳回原文。</div>';
      return;
    }
    var h = NOTES.slice().reverse().map(function (x, ri) {
      var i = NOTES.length - 1 - ri;
      return '<div class="nbi">' +
        '<div class="nbc">' +
          '<div class="nbfr">' + esc(x.t) + '</div>' +
          (x.zh ? '<div class="nbzh">' + esc(x.zh) + '</div>' : '') +
          '<div class="nbsrc"><span>📍 ' + (x.no ? '第 ' + x.no + ' 章 · ' : '') + esc(x.ch || '') + '</span>' +
          '<span>' + window.tcfStats.stamp(x.ts) + '</span>' +
          '<button data-nbgo="' + i + '">跳回原文 ↗</button></div>' +
        '</div>' +
        '<div class="nbact">' +
          (x.aid ? '<button data-nbsay="' + i + '" title="重听">🔊</button>' : '') +
          '<button data-nbdel="' + i + '" title="删掉">✕</button>' +
        '</div></div>';
    }).join('');
    $('nbList').innerHTML = h;
  }
  function nbOpen() { nbRender(); $('nbwrap').classList.remove('hidden'); }
  $('btnNotes').onclick = nbOpen;
  $('nbClose').onclick = function () { $('nbwrap').classList.add('hidden'); };
  $('nbCopy').onclick = function () {
    if (!NOTES.length) { toast('笔记本还是空的'); return; }
    var txt = NOTES.map(function (x) {
      return x.t + (x.zh ? '\\n  ' + x.zh : '') + '\\n  —— 第 ' + x.no + ' 章 ' + (x.ch || '');
    }).join('\\n\\n');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(function () { toast('已复制 ' + NOTES.length + ' 句'); })
        .catch(function () { toast('复制失败，长按选中也可以'); });
    } else { toast('这个浏览器不支持一键复制'); }
  };
  $('nbList').addEventListener('click', function (e) {
    var g = e.target.closest('[data-nbgo]'), s = e.target.closest('[data-nbsay]'), d = e.target.closest('[data-nbdel]');
    if (s) { var n1 = NOTES[+s.dataset.nbsay]; if (n1) play(n1.aid, n1.t.slice(0, 60)); return; }
    if (d) {
      var i = +d.dataset.nbdel;
      NOTES.splice(i, 1); notesSave(); notesDot(); nbRender();
      return;
    }
    if (g) {
      var n2 = NOTES[+g.dataset.nbgo]; if (!n2) return;
      $('nbwrap').classList.add('hidden');
      var ci = chIndexByKey(n2.key);
      if (ci < 0) { toast('这一章找不到了'); return; }
      renderChapter(ci);
      drawer(false);
      setTimeout(function () { spotSentence(n2.aid, n2.t); }, 90);
    }
  });
"""

p = os.path.join(SRC, "app.js")
t = io.open(p, encoding="utf-8").read()
assert "句子笔记本" not in t, "already patched"

ANCHOR = "  /* ---------------- study log ----------------"
assert t.count(ANCHOR) == 1
t = t.replace(ANCHOR, JS + "\n" + ANCHOR)

# put 📓 in the ⋯ menu on a phone, like the other secondary actions
OLD = ("    var secondary = [$('btnVocab'), $('btnStats'), $('btnDark')];\n"
       "    var LABEL = { btnStats: '📊 学习记录', btnDark: '🌙 夜间模式', btnVocab: '📒 生词本' };")
NEW = ("    var secondary = [$('btnVocab'), $('btnNotes'), $('btnStats'), $('btnDark')];\n"
       "    var LABEL = { btnStats: '📊 学习记录', btnDark: '🌙 夜间模式', btnVocab: '📒 生词本',\n"
       "                  btnNotes: '📓 笔记本' };")
assert t.count(OLD) == 1
t = t.replace(OLD, NEW)

# show the dot on boot if she has notes
OLD2 = "    if (store.get('dark', false)) document.body.classList.add('dark');"
assert t.count(OLD2) == 1
t = t.replace(OLD2, "    notesDot();\n" + OLD2)

io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("app.js: 句子笔记本 added")
