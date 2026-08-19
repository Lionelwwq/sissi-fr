# -*- coding: utf-8 -*-
"""今天练什么 —— a daily plan built from her own study log.

Chapter 31 hands her a fixed weekly timetable; nobody reads a fixed timetable
twice. This rebuilds the list every day out of what she has actually done:
the chapter she has not been back to in longest, the next unread one, a resource
she has not opened, words from her own vocabulary book, and one speaking prompt.
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


# ---------------------------------------------------------------- index.html
patch("index.html", [
    ('      <button class="btn" id="btnMenu">☰</button>',
     '      <button class="btn" id="btnMenu">☰</button>\n'
     '      <button class="btn today" id="btnPlan" title="今天练什么">📅<span class="lbl"> 今天</span>'
     '<i class="dot hidden" id="planDot"></i></button>'),
    ('<div id="stwrap" class="hidden">',
     '<div id="dpwrap" class="hidden">\n'
     '  <div class="dp">\n'
     '    <div class="dph"><b>📅 今天练什么</b><span class="dpd" id="dpDate"></span>\n'
     '      <span class="spacer"></span><button class="btn" id="dpClose">✕ 关闭</button></div>\n'
     '    <div id="dpBody" class="dpb"></div>\n'
     '  </div>\n'
     '</div>\n\n'
     '<div id="stwrap" class="hidden">'),
])

# ---------------------------------------------------------------- stats.js
patch("stats.js", [
    # the plan needs to know when each chapter was last opened, and which chapter a row is
    ("    var c = S.chapters[key] || (S.chapters[key] = { no: ch.no, zh: ch.zh, sec: 0, opens: 0 });\n"
     "    c.opens++; c.no = ch.no; c.zh = ch.zh;",
     "    var c = S.chapters[key] || (S.chapters[key] = { no: ch.no, zh: ch.zh, sec: 0, opens: 0 });\n"
     "    c.opens++; c.no = ch.no; c.zh = ch.zh; c.key = key; c.last = Date.now();"),
    ("      var c = S.chapters[cur.key] || (S.chapters[cur.key] = { no: cur.no, zh: cur.zh, sec: 0, opens: 0 });\n"
     "      c.sec += sec; c.zh = cur.zh; c.no = cur.no;",
     "      var c = S.chapters[cur.key] || (S.chapters[cur.key] = { no: cur.no, zh: cur.zh, sec: 0, opens: 0 });\n"
     "      c.sec += sec; c.zh = cur.zh; c.no = cur.no; c.key = cur.key; c.last = Date.now();"),
    ("  window.tcfStats = { view: view, audio: audio, word: word, link: link, flash: flash,\n"
     "                      search: search, summary: summary, asText: asText, mins: mins,",
     "  /* 连续学习天数：今天还没开始不算断，从昨天接着数 */\n"
     "  function dkey(d) {\n"
     "    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);\n"
     "  }\n"
     "  function streak() {\n"
     "    load();\n"
     "    var n = 0, d = new Date();\n"
     "    var t = S.days[dkey(d)];\n"
     "    if (!(t && t.sec > 60)) d.setDate(d.getDate() - 1);\n"
     "    while (S.days[dkey(d)] && S.days[dkey(d)].sec > 60) { n++; d.setDate(d.getDate() - 1); }\n"
     "    return n;\n"
     "  }\n"
     "  function dayStat() { var v = day(); return { sec: v.sec, audio: v.audio, words: v.words, links: v.links }; }\n"
     "  window.tcfStats = { view: view, audio: audio, word: word, link: link, flash: flash,\n"
     "                      search: search, summary: summary, asText: asText, mins: mins,\n"
     "                      streak: streak, dayStat: dayStat, today: today,"),
])

# ---------------------------------------------------------------- app.js
PLAN_JS = r"""
  /* ---------------- 今天练什么 ----------------
     第 31 章给的是一张固定的周计划表，看两遍就不会再看第三遍。这一版每天按她自己的
     记录重排：最久没回头的一章、下一章新课、还没点开过的资源、生词本里的词，再加
     一道口语题。每条都能一键跳过去，勾掉之后当天不再出现。 */
  var PLAN = { day: '', items: [] };
  function dayKey() {
    var d = new Date();
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  /* 同一天必须给出同一份清单：每刷新一次就重排的东西不叫计划。
     用日期做种子的伪随机，换一天才换内容。 */
  function seeded(s) {
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return function () { h = (h * 1664525 + 1013904223) >>> 0; return h / 4294967296; };
  }
  function chIndexByKey(key) {
    if (!DOC) return -1;
    for (var i = 0; i < DOC.chapters.length; i++) {
      var c = DOC.chapters[i];
      if ((c.key || ('ch' + c.no)) === key) return i;
    }
    return -1;
  }
  function allLinks() {
    var out = [];
    DOC.chapters.forEach(function (c, i) {
      (c.blocks || []).forEach(function (b) {
        (b.links || []).forEach(function (x) { out.push({ x: x, ci: i }); });
      });
    });
    return out;
  }
  function planGo(i, after) {
    $('dpwrap').classList.add('hidden');
    renderChapter(i);
    drawer(false);
    if (after) setTimeout(after, 80);
  }
  // the resource lives among 168 cards; landing on the chapter is not landing on it
  function spotlight(url) {
    var a = document.querySelector('#wrap .lcard[href="' + url + '"]');
    if (!a) return;
    a.scrollIntoView({ block: 'center' });
    a.classList.add('spot');
    setTimeout(function () { a.classList.remove('spot'); }, 3000);
  }

  function planBuild(vocab) {
    var R = seeded(PLAN.day);
    var st = window.tcfStats ? window.tcfStats.summary() : { chapters: [], links: [] };
    var done = store.get('done', {});
    var items = [];

    // ① 最久没回头的一章
    var read = st.chapters.filter(function (c) { return c.sec > 45 && chIndexByKey(c.key) >= 0; })
                          .sort(function (a, b) { return (a.last || 0) - (b.last || 0); });
    if (read.length) {
      var r = read[0], ri = chIndexByKey(r.key);
      var ago = r.last ? Math.floor((Date.now() - r.last) / 864e5) : null;
      items.push({ k: 'review', icon: '🔁', tag: '复习', t: '第 ' + r.no + ' 章 · ' + r.zh,
        s: (ago === null ? '' : ago <= 0 ? '今天看过，再过一遍' : ago + ' 天没回头了') +
           '　·　当时读了 ' + window.tcfStats.mins(r.sec),
        b: '打开这一章', go: function () { planGo(ri); } });
    }

    // ② 下一章新课
    var nxt = -1;
    for (var i = 0; i < DOC.chapters.length; i++) {
      if (!done[DOC.chapters[i].key || i]) { nxt = i; break; }
    }
    if (nxt < 0) {                       // 全书读完了：挑当时停留最短的一章重读
      var least = st.chapters.slice().sort(function (a, b) { return a.sec - b.sec; })[0];
      nxt = least ? chIndexByKey(least.key) : 0;
    }
    if (nxt >= 0) {
      var nc = DOC.chapters[nxt], ni = nxt;
      items.push({ k: 'new', icon: '📖', tag: '新课', t: '第 ' + nc.no + ' 章 · ' + nc.zh,
        s: String(nc.intro || '').slice(0, 62), b: '开始读', go: function () { planGo(ni); } });
    }

    // ③ 一条还没点开过的听力材料
    var opened = {};
    (st.links || []).forEach(function (l) { opened[l.url] = 1; });
    var pool = allLinks().filter(function (o) {
      return !opened[o.x.url] && !opened[o.x.embed] && o.x.cn_ok !== 'vpn';
    });
    var pref = pool.filter(function (o) { return o.x.level === 'A2' || o.x.level === 'B1'; });
    var cand = pref.length ? pref : pool;
    if (cand.length) {
      var pk = cand[Math.floor(R() * cand.length)];
      items.push({ k: 'res', icon: '🎧', tag: '听力', t: pk.x.title,
        s: [pk.x.platform, pk.x.level, pk.x.length].filter(Boolean).join(' · ') +
           (pk.x.how ? '　·　' + String(pk.x.how).replace(/<[^>]+>/g, '').slice(0, 64) : ''),
        b: pk.x.embed ? '去看（能站内播）' : '去看这一条',
        go: function () { planGo(pk.ci, function () { spotlight(pk.x.url); }); } });
    }

    // ④ 生词：够 5 个就背自己存的，否则先背这一章的词卡
    if (vocab && vocab.length >= 5) {
      var a = vocab.slice();
      for (var j = a.length - 1; j > 0; j--) {
        var k2 = Math.floor(R() * (j + 1)), tmp = a[j]; a[j] = a[k2]; a[k2] = tmp;
      }
      var picks = a.slice(0, Math.min(12, a.length));
      items.push({ k: 'vocab', icon: '🎴', tag: '生词', t: '背 ' + picks.length + ' 个自己存的词',
        s: picks.slice(0, 6).map(function (x) { return x.word; }).join('、') + (picks.length > 6 ? ' …' : ''),
        b: '开始背', go: function () { $('dpwrap').classList.add('hidden'); fcFromVocab(picks); } });
    } else {
      var ci = read.length ? chIndexByKey(read[0].key) : (nxt >= 0 ? nxt : 0);
      items.push({ k: 'vocab', icon: '🎴', tag: '词卡', t: '背这一章的词卡',
        s: '生词本还不到 5 个词。看书时点任意法语单词，卡片右下角能存进去，攒起来以后就背自己的。',
        b: '打开背诵', go: function () { planGo(ci, fcOpen); } });
    }

    // ⑤ 开口 90 秒
    var tps = DOC.topics || [];
    if (tps.length) {
      var tp = tps[Math.floor(R() * tps.length)], es = tp.entries || [], three = [];
      while (three.length < 3 && es.length) {
        var e = es[Math.floor(R() * es.length)];
        if (three.indexOf(e) < 0) three.push(e);
      }
      items.push({ k: 'talk', icon: '🗣', tag: '口语', t: 'Tâche 3 · ' + tp.zh + '，说满 90 秒',
        s: '录下来再回放。至少用上：' + three.map(function (x) { return x.phrase; }).join(' / '),
        b: '打开话题库', go: function () { planGo(chIndexByKey('__topics__')); } });
    }
    return items;
  }

  function planRender() {
    var p = store.get('plan', {});
    if (p.day !== PLAN.day) p = { day: PLAN.day, done: {} };
    var s = window.tcfStats;
    var sec = s && s.dayStat ? s.dayStat().sec : 0;
    var stk = s && s.streak ? s.streak() : 0;
    var nDone = PLAN.items.filter(function (it) { return p.done[it.k]; }).length;

    var h = ['<div class="dpsum">' +
      '<div class="dpring' + (nDone >= PLAN.items.length ? ' full' : '') + '">' + nDone + '<i>/' + PLAN.items.length + '</i></div>' +
      '<div class="dpst"><b>' + (nDone >= PLAN.items.length ? '今天的都做完了 🎉' : '今天还剩 ' + (PLAN.items.length - nDone) + ' 件') + '</b>' +
      '<span>今天已学 ' + (s ? s.mins(sec) : '0 秒') +
      (stk > 0 ? '　·　🔥 连续 ' + stk + ' 天' : '') + '</span></div></div>'];

    h.push('<div class="dplist">' + PLAN.items.map(function (it, i) {
      var ok = !!p.done[it.k];
      return '<div class="dpi' + (ok ? ' ok' : '') + '">' +
        '<button class="dpck" data-tick="' + it.k + '" title="标记完成">' + (ok ? '✓' : '') + '</button>' +
        '<div class="dpc"><div class="dpt"><span class="dpg">' + it.icon + ' ' + it.tag + '</span>' + esc(it.t) + '</div>' +
        (it.s ? '<div class="dps">' + esc(it.s) + '</div>' : '') + '</div>' +
        '<button class="btn dpb2" data-plango="' + i + '">' + esc(it.b) + '</button></div>';
    }).join('') + '</div>');

    h.push('<div class="dpfoot">清单每天早上按你自己的记录重排——看得最久没回头的、还没读的、还没点开过的。' +
           '做不完不要紧，做一条也比不做强。</div>');
    $('dpBody').innerHTML = h.join('');
    $('dpDate').textContent = PLAN.day;
    var dot = $('planDot');
    if (dot) dot.classList.toggle('hidden', nDone >= PLAN.items.length);
  }

  function planOpen() {
    PLAN.day = dayKey();
    $('dpwrap').classList.remove('hidden');
    $('dpBody').innerHTML = '<div class="vbe">正在排今天的计划…</div>';
    fetch('/api/vocab/list').then(function (r) { return r.json(); })
      .catch(function () { return []; })
      .then(function (v) {
        PLAN.items = planBuild(v || []);
        planRender();
      });
  }
  $('btnPlan').onclick = planOpen;
  $('dpClose').onclick = function () { $('dpwrap').classList.add('hidden'); };
  $('dpBody').addEventListener('click', function (e) {
    var g = e.target.closest('[data-plango]');
    if (g) { var it = PLAN.items[+g.dataset.plango]; if (it && it.go) it.go(); return; }
    var t = e.target.closest('[data-tick]');
    if (t) {
      var p = store.get('plan', {});
      if (p.day !== PLAN.day) p = { day: PLAN.day, done: {} };
      p.done[t.dataset.tick] = p.done[t.dataset.tick] ? 0 : 1;
      store.set('plan', p);
      planRender();
      return;
    }
  });
"""

patch("app.js", [
    ("  /* ---------------- study log ----------------", PLAN_JS + "\n  /* ---------------- study log ----------------"),
    # a plan she has to remember to open is a plan she will not open; show it when the
    # day has not started yet, and mark the button while anything is left
    ("    markVisited();\n    if (last > 0) toast('接着上次：第 ' + d.chapters[last].no + ' 章');",
     "    markVisited();\n"
     "    if (last > 0) toast('接着上次：第 ' + d.chapters[last].no + ' 章');\n"
     "    var sec0 = window.tcfStats && window.tcfStats.dayStat ? window.tcfStats.dayStat().sec : 1;\n"
     "    if (!$('welcome') || $('welcome').classList.contains('hidden')) {\n"
     "      if (sec0 < 30 && store.get('planShown', '') !== dayKey()) {\n"
     "        store.set('planShown', dayKey());\n"
     "        setTimeout(planOpen, 700);\n"
     "      } else { PLAN.day = dayKey(); planPeek(); }\n"
     "    }"),
])

# a cheap version of planRender that only decides whether the button gets its dot
patch("app.js", [
    ("  function planOpen() {",
     "  // the dot has to appear without building the whole plan first\n"
     "  function planPeek() {\n"
     "    var p = store.get('plan', {});\n"
     "    var keys = ['review', 'new', 'res', 'vocab', 'talk'];\n"
     "    var undone = p.day !== PLAN.day || keys.some(function (k) { return !(p.done || {})[k]; });\n"
     "    var dot = $('planDot');\n"
     "    if (dot) dot.classList.toggle('hidden', !undone);\n"
     "  }\n"
     "  function planOpen() {"),
])

# ---------------------------------------------------------------- app.css
CSS = """

/* ---- 今天练什么 ---- */
.btn.today{border-color:var(--accent);color:var(--accent);font-weight:600;position:relative}
.btn.today .dot{position:absolute;top:5px;right:5px;width:8px;height:8px;border-radius:50%;
  background:var(--accent2);display:block}
.btn.today .dot.hidden{display:none}
#dpwrap{position:fixed;inset:0;background:rgba(10,16,26,.86);z-index:215;display:flex;
  align-items:center;justify-content:center;padding:16px}
#dpwrap.hidden{display:none}
.dp{background:var(--card);border-radius:14px;width:min(700px,100%);max-height:88vh;
  display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.4)}
.dph{display:flex;align-items:center;gap:8px;padding:13px 16px;border-bottom:1px solid var(--line);font-size:16px}
.dph .spacer{flex:1}
.dpd{font-size:12px;color:var(--muted)}
.dpb{overflow:auto;padding:14px 16px 18px}
.dpsum{display:flex;align-items:center;gap:14px;background:var(--accent-soft);border-radius:12px;padding:12px 14px}
.dpring{flex:0 0 auto;width:52px;height:52px;border-radius:50%;border:3px solid var(--accent);
  color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700}
.dpring i{font-size:12px;font-style:normal;opacity:.7}
.dpring.full{background:var(--accent);color:#fff}
.dpst b{display:block;font-size:16px}
.dpst span{font-size:12.5px;color:var(--muted)}
.dplist{display:flex;flex-direction:column;gap:9px;margin-top:12px}
.dpi{display:flex;align-items:flex-start;gap:11px;border:1px solid var(--line);border-radius:11px;
  padding:11px 12px;background:var(--card)}
.dpi.ok{opacity:.55}
.dpi.ok .dpt{text-decoration:line-through}
.dpck{flex:0 0 auto;width:26px;height:26px;border-radius:7px;border:1.5px solid var(--line);
  background:transparent;color:var(--accent);font-size:15px;font-weight:700;cursor:pointer;line-height:1}
.dpi.ok .dpck{background:var(--accent);border-color:var(--accent);color:#fff}
.dpc{flex:1;min-width:0}
.dpt{font-size:14.5px;font-weight:600;line-height:1.5}
.dpg{display:inline-block;background:var(--accent-soft);color:var(--accent);border-radius:6px;
  font-size:11.5px;font-weight:700;padding:2px 7px;margin-right:7px;vertical-align:1px}
.dps{font-size:12.5px;color:var(--muted);margin-top:4px;line-height:1.65}
.dpb2{flex:0 0 auto;align-self:center;white-space:nowrap}
.dpfoot{margin-top:14px;font-size:12px;color:var(--muted);line-height:1.7}
.lcard.spot{outline:3px solid var(--accent2);outline-offset:2px}
/* the boot fetch can fail; saying so beats a spinner that never stops */
.loadfail{text-align:center;padding:60px 20px;color:var(--muted)}
.lf-i{font-size:42px}
.lf-t{font-size:19px;color:var(--ink);margin:10px 0 6px}
.lf-s{font-size:13.5px;line-height:1.8;margin-bottom:16px}
@media (max-width:860px){
  .dpi{flex-wrap:wrap}
  .dpb2{width:100%;margin-top:8px;min-height:42px}
  .dpring{width:46px;height:46px;font-size:18px}
}
"""
p = os.path.join(S, "app.css")
t = io.open(p, encoding="utf-8").read()
assert ".dpi{" not in t
io.open(p, "w", encoding="utf-8", newline="\n").write(t + CSS)
print("appended app.css")
print("ok")
