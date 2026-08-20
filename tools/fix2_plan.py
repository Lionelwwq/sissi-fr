# -*- coding: utf-8 -*-
"""The daily plan was re-derived from live state on every open, so acting on an item
removed it and a different task slid into the slot — her ✓ then sat on something she
had never done, and the red dot could never clear. Decide the day's list once, store
a small serialisable spec, and render from that."""
import io, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")

OLD_BUILD = """  function cut(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }
  function planBuild(vocab) {
    // one generator per slot: otherwise adding a word to the vocabulary book shifts how
    // many numbers the shuffle eats and the speaking topic changes for no reason
    var Rres = seeded(PLAN.day + ':res'), Rvoc = seeded(PLAN.day + ':voc'), Rtalk = seeded(PLAN.day + ':talk');
    var st = window.tcfStats ? window.tcfStats.summary() : { chapters: [], links: [] };
    var done = store.get('done', {});
    var items = [];

    // ① 最久没回头的一章
    var read = st.chapters.filter(function (c) { return c.sec > 45 && chIndexByKey(c.key) >= 0; })
                          .sort(function (a, b) { return (a.last || 0) - (b.last || 0); });
    if (read.length) {
      var r = read[0], ri = chIndexByKey(r.key);
      var ago = r.last ? Math.floor((Date.now() - r.last) / 864e5) : null;
      items.push({ k: 'review', icon: '\U0001f501', tag: '复习', t: '第 ' + r.no + ' 章 · ' + r.zh,
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
      items.push({ k: 'new', icon: '\U0001f4d6', tag: '新课', t: '第 ' + nc.no + ' 章 · ' + nc.zh,
        s: cut(String(nc.intro || ''), 62), b: '开始读', go: function () { planGo(ni); } });
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
      var pk = cand[Math.floor(Rres() * cand.length)];
      items.push({ k: 'res', icon: '\U0001f3a7', tag: '听力', t: pk.x.title,
        s: [pk.x.platform, pk.x.level, pk.x.length].filter(Boolean).join(' · ') +
           (pk.x.how ? '　·　' + cut(String(pk.x.how).replace(/<[^>]+>/g, ''), 64) : ''),
        b: pk.x.embed ? '去看（能站内播）' : '去看这一条',
        go: function () { planGo(pk.ci, function () { spotlight(pk.x.url); }); } });
    }

    // ④ 生词：够 5 个就背自己存的，否则先背这一章的词卡
    if (vocab && vocab.length >= 5) {
      var a = vocab.slice();
      for (var j = a.length - 1; j > 0; j--) {
        var k2 = Math.floor(Rvoc() * (j + 1)), tmp = a[j]; a[j] = a[k2]; a[k2] = tmp;
      }
      var picks = a.slice(0, Math.min(12, a.length));
      items.push({ k: 'vocab', icon: '\U0001f3b4', tag: '生词', t: '背 ' + picks.length + ' 个自己存的词',
        s: picks.slice(0, 6).map(function (x) { return x.word; }).join('、') + (picks.length > 6 ? ' …' : ''),
        b: '开始背', go: function () { $('dpwrap').classList.add('hidden'); fcFromVocab(picks); } });
    } else {
      var ci = read.length ? chIndexByKey(read[0].key) : (nxt >= 0 ? nxt : 0);
      items.push({ k: 'vocab', icon: '\U0001f3b4', tag: '词卡', t: '背这一章的词卡',
        s: '生词本还不到 5 个词。看书时点任意法语单词，卡片右下角能存进去，攒起来以后就背自己的。',
        b: '打开背诵', go: function () { planGo(ci, fcOpen); } });
    }

    // ⑤ 开口 90 秒
    var tps = DOC.topics || [];
    if (tps.length) {
      var tp = tps[Math.floor(Rtalk() * tps.length)], es = tp.entries || [], three = [];
      while (three.length < 3 && es.length) {
        var e = es[Math.floor(Rtalk() * es.length)];
        if (three.indexOf(e) < 0) three.push(e);
      }
      items.push({ k: 'talk', icon: '\U0001f5e3', tag: '口语', t: 'Tâche 3 · ' + tp.zh + '，说满 90 秒',
        s: '录下来再回放。至少用上：' + three.map(function (x) { return x.phrase; }).join(' / '),
        b: '打开话题库', go: function () { planGo(chIndexByKey('__topics__')); } });
    }
    return items;
  }
"""

NEW_BUILD = """  function cut(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }
  function daysBetween(ts) {          // calendar days, not elapsed hours: 22:00 → 08:00 is yesterday
    if (!ts) return null;
    var a = new Date(ts), b = new Date();
    a.setHours(0, 0, 0, 0); b.setHours(0, 0, 0, 0);
    return Math.round((b - a) / 864e5);
  }
  function chapterHasCards(i) {
    var c = DOC.chapters[i];
    if (!c) return false;
    if (c.key === '__topics__') return !!(DOC.topics && DOC.topics.length);
    return (c.blocks || []).some(function (b) { return b.kind === 'cards' && (b.cards || []).length; });
  }
  function nearestCardChapter(from) {   // 「背这一章的词卡」 must land somewhere that has any
    if (chapterHasCards(from)) return from;
    for (var d = 1; d < DOC.chapters.length; d++) {
      if (chapterHasCards(from + d)) return from + d;
      if (chapterHasCards(from - d)) return from - d;
    }
    return -1;
  }

  /* The day's list is decided once and kept. It used to be re-derived on every open,
     so acting on an item removed it, a new task slid into the slot, and the ✓ she
     ticked afterwards sat on something she had never seen. */
  function planSpec(vocab) {
    // one generator per slot: otherwise adding a word to the vocabulary book shifts how
    // many numbers the shuffle eats and the speaking topic changes for no reason
    var Rres = seeded(PLAN.day + ':res'), Rvoc = seeded(PLAN.day + ':voc'), Rtalk = seeded(PLAN.day + ':talk');
    var st = window.tcfStats ? window.tcfStats.summary() : { chapters: [], links: [] };
    var done = store.get('done', {});
    var spec = [];

    // ① 最久没回头的一章
    var read = st.chapters.filter(function (c) { return c.sec > 45 && chIndexByKey(c.key) >= 0; })
                          .sort(function (a, b) { return (a.last || 0) - (b.last || 0); });
    if (read.length) spec.push({ k: 'review', key: read[0].key });

    // ② 下一章新课
    var nxt = -1;
    for (var i = 0; i < DOC.chapters.length; i++) {
      if (!done[DOC.chapters[i].key || i]) { nxt = i; break; }
    }
    if (nxt < 0) {                       // 全书读完了：挑当时停留最短的一章重读
      var least = st.chapters.slice().sort(function (a, b) { return a.sec - b.sec; })[0];
      nxt = least ? chIndexByKey(least.key) : 0;
    }
    if (nxt >= 0) spec.push({ k: 'new', key: DOC.chapters[nxt].key || ('ch' + DOC.chapters[nxt].no) });

    // ③ 一条还没点开过的听力材料
    var opened = {};
    (st.links || []).forEach(function (l) { opened[l.url] = 1; });
    var pool = allLinks().filter(function (o) {
      return !opened[o.x.url] && !opened[o.x.embed] && o.x.cn_ok !== 'vpn';
    });
    var pref = pool.filter(function (o) { return o.x.level === 'A2' || o.x.level === 'B1'; });
    var cand = pref.length ? pref : pool;
    if (cand.length) spec.push({ k: 'res', url: cand[Math.floor(Rres() * cand.length)].x.url });

    // ④ 生词：够 5 个就背自己存的，否则先背这一章的词卡
    if (vocab && vocab.length >= 5) {
      var a = vocab.slice();
      for (var j = a.length - 1; j > 0; j--) {
        var k2 = Math.floor(Rvoc() * (j + 1)), tmp = a[j]; a[j] = a[k2]; a[k2] = tmp;
      }
      spec.push({ k: 'vocab', w: a.slice(0, Math.min(12, a.length)).map(function (x) { return x.word; }) });
    } else {
      var from = read.length ? chIndexByKey(read[0].key) : (nxt >= 0 ? nxt : 0);
      var ci = nearestCardChapter(from);
      if (ci >= 0) spec.push({ k: 'vocab', cards: DOC.chapters[ci].key || ('ch' + DOC.chapters[ci].no) });
    }

    // ⑤ 开口 90 秒
    var tps = DOC.topics || [];
    if (tps.length) {
      var ti = Math.floor(Rtalk() * tps.length), es = (tps[ti] || {}).entries || [], pick = [];
      // guard the count: a topic with fewer than three entries used to spin here forever
      var want = Math.min(3, es.length), spins = 0;
      while (pick.length < want && spins++ < 200) {
        var ei = Math.floor(Rtalk() * es.length);
        if (pick.indexOf(ei) < 0) pick.push(ei);
      }
      spec.push({ k: 'talk', t: ti, e: pick });
    }
    return spec;
  }

  /* spec → what she sees. Titles and 「N 天没回头」 are recomputed live so they stay
     truthful, but which chapter / which clip / which words never move within a day. */
  function planHydrate(spec, vocab) {
    var st = window.tcfStats ? window.tcfStats.summary() : { chapters: [], links: [] };
    var byKey = {};
    (st.chapters || []).forEach(function (c) { byKey[c.key] = c; });
    var items = [];
    (spec || []).forEach(function (sp) {
      if (sp.k === 'review') {
        var ri = chIndexByKey(sp.key); if (ri < 0) return;
        var c = DOC.chapters[ri], r = byKey[sp.key] || {};
        var ago = daysBetween(r.last);
        items.push({ k: 'review', icon: '\U0001f501', tag: '复习', t: '第 ' + c.no + ' 章 · ' + c.zh,
          s: (ago === null ? '' : ago <= 0 ? '今天看过，再过一遍' : ago + ' 天没回头了') +
             (r.sec ? '　·　当时读了 ' + window.tcfStats.mins(r.sec) : ''),
          b: '打开这一章', go: function () { planGo(ri); } });
      } else if (sp.k === 'new') {
        var ni = chIndexByKey(sp.key); if (ni < 0) return;
        var nc = DOC.chapters[ni];
        items.push({ k: 'new', icon: '\U0001f4d6', tag: '新课', t: '第 ' + nc.no + ' 章 · ' + nc.zh,
          s: cut(String(nc.intro || ''), 62), b: '开始读', go: function () { planGo(ni); } });
      } else if (sp.k === 'res') {
        var hit = null;
        allLinks().forEach(function (o) { if (!hit && o.x.url === sp.url) hit = o; });
        if (!hit) return;
        var x = hit.x;
        items.push({ k: 'res', icon: '\U0001f3a7', tag: '听力', t: x.title,
          s: [x.platform, x.level, x.length].filter(Boolean).join(' · ') +
             (x.how ? '　·　' + cut(String(x.how).replace(/<[^>]+>/g, ''), 64) : ''),
          b: x.embed ? '去看（能站内播）' : '去看这一条',
          go: function () { planGo(hit.ci, function () { spotlight(x.url); }); } });
      } else if (sp.k === 'vocab' && sp.w) {
        var have = {};
        (vocab || []).forEach(function (v) { have[v.word] = v; });
        var picks = sp.w.map(function (w) { return have[w]; }).filter(Boolean);
        if (!picks.length) return;
        items.push({ k: 'vocab', icon: '\U0001f3b4', tag: '生词', t: '背 ' + picks.length + ' 个自己存的词',
          s: picks.slice(0, 6).map(function (x) { return x.word; }).join('、') + (picks.length > 6 ? ' …' : ''),
          b: '开始背', go: function () { $('dpwrap').classList.add('hidden'); fcFromVocab(picks); } });
      } else if (sp.k === 'vocab') {
        var ci = chIndexByKey(sp.cards); if (ci < 0) return;
        items.push({ k: 'vocab', icon: '\U0001f3b4', tag: '词卡', t: '背第 ' + DOC.chapters[ci].no + ' 章的词卡',
          s: '生词本还不到 5 个词。看书时点任意法语单词，卡片右下角能存进去，攒起来以后就背自己的。',
          b: '打开背诵', go: function () { planGo(ci, fcOpen); } });
      } else if (sp.k === 'talk') {
        var tp = (DOC.topics || [])[sp.t]; if (!tp) return;
        var es = tp.entries || [];
        var three = (sp.e || []).map(function (i) { return es[i]; }).filter(Boolean);
        items.push({ k: 'talk', icon: '\U0001f5e3', tag: '口语', t: 'Tâche 3 · ' + tp.zh + '，说满 90 秒',
          s: '录下来再回放。至少用上：' + three.map(function (x) { return x.phrase; }).join(' / '),
          b: '打开话题库', go: function () { planGo(chIndexByKey('__topics__')); } });
      }
    });
    return items;
  }
"""

OLD_TAIL = """  function planRender() {
    var p = store.get('plan', {});
    if (p.day !== PLAN.day) p = { day: PLAN.day, done: {} };
"""
NEW_TAIL = """  function planRender() {
    var p = store.get('plan', {});
    if (p.day !== PLAN.day) p = { day: PLAN.day, done: {} };
    p.done = p.done || {};
"""

OLD_PEEK = """  // the dot has to appear without building the whole plan first
  function planPeek() {
    var p = store.get('plan', {});
    var keys = ['review', 'new', 'res', 'vocab', 'talk'];
    var undone = p.day !== PLAN.day || keys.some(function (k) { return !(p.done || {})[k]; });
    var dot = $('planDot');
    if (dot) dot.classList.toggle('hidden', !undone);
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
"""
NEW_PEEK = """  /* The dot has to appear without building the whole plan first, and it has to be able
     to go out again: it used to check five hard-coded slot names while the plan often
     has four, so 「全都做完了」 still nagged forever. Ask the stored spec instead. */
  function planPeek() {
    var p = store.get('plan', {});
    var dot = $('planDot');
    if (!dot) return;
    if (p.day !== PLAN.day || !p.spec) { dot.classList.remove('hidden'); return; }
    var done = p.done || {};
    var undone = p.spec.some(function (sp) { return !done[sp.k]; });
    dot.classList.toggle('hidden', !undone);
  }
  function planOpen() {
    PLAN.day = dayKey();
    $('dpwrap').classList.remove('hidden');
    $('dpBody').innerHTML = '<div class="vbe">正在排今天的计划…</div>';
    // tapping \U0001f4c5 before the book finished downloading used to throw on a null DOC and
    // leave the panel on 「正在排…」 for good
    if (!DOC) {
      $('dpBody').innerHTML = '<div class="vbe">课文还没载入完，稍等一下再点一次。</div>';
      return;
    }
    fetch('/api/vocab/list').then(function (r) { return r.json(); })
      .catch(function () { return []; })
      .then(function (v) {
        v = v || [];
        var p = store.get('plan', {});
        if (p.day !== PLAN.day || !p.spec || !p.spec.length) {
          p = { day: PLAN.day, done: {}, spec: planSpec(v) };
          store.set('plan', p);
        }
        PLAN.items = planHydrate(p.spec, v);
        planRender();
      })
      .catch(function () {
        $('dpBody').innerHTML = '<div class="vbe">计划没能排出来，关掉重新点一次试试。</div>';
      });
  }
"""

OLD_TICK = """      var p = store.get('plan', {});
      if (p.day !== PLAN.day) p = { day: PLAN.day, done: {} };
      p.done[t.dataset.tick] = p.done[t.dataset.tick] ? 0 : 1;
"""
NEW_TICK = """      var p = store.get('plan', {});
      if (p.day !== PLAN.day) p = { day: PLAN.day, done: {} };
      p.done = p.done || {};
      p.done[t.dataset.tick] = p.done[t.dataset.tick] ? 0 : 1;
"""

p = os.path.join(SRC, "app.js")
t = io.open(p, encoding="utf-8").read()
for old, new, label in ((OLD_BUILD, NEW_BUILD, "planBuild -> planSpec/planHydrate"),
                        (OLD_TAIL, NEW_TAIL, "planRender guard"),
                        (OLD_PEEK, NEW_PEEK, "planPeek/planOpen"),
                        (OLD_TICK, NEW_TICK, "tick guard")):
    n = t.count(old)
    assert n == 1, (label, "expected 1, found %d" % n)
    t = t.replace(old, new)
    print("  ok:", label)
assert "planBuild(" not in t, "a caller of the old planBuild survived"
io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("app.js plan module rebuilt")
