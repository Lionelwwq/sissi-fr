/* 学习记录 —— 全部存在本机浏览器里，不上传任何地方。
   She can read it herself, and export a short summary to send if she wants to.
   Nothing here leaves the device on its own: this is a study log, not telemetry. */
(function () {
  'use strict';
  var KEY = 'tcf_stats_v1';
  var CAP = 400;                       // keep the recent trail bounded

  function blank() {
    return { chapters: {}, days: {}, words: {}, links: [], recent: [],
             audio: 0, flash: 0, searches: 0, firstTs: Date.now() };
  }
  var S = null;
  function load() {
    if (S) return S;
    try { S = JSON.parse(localStorage.getItem(KEY)) || blank(); }
    catch (e) { S = blank(); }
    for (var k in blank()) if (S[k] === undefined) S[k] = blank()[k];
    /* Chapter records written before the daily plan existed have no `key`, and the
       plan looks chapters up by it — without this migration her entire history is
       invisible to 复习 the first time she opens the new version. */
    for (var ck in S.chapters) if (S.chapters[ck] && !S.chapters[ck].key) S.chapters[ck].key = ck;
    return S;
  }
  var saveTimer = null;
  function writeNow() {
    clearTimeout(saveTimer);
    saveTimer = null;
    mine = true;
    try { localStorage.setItem(KEY, JSON.stringify(S)); }
    catch (e) {                       // quota: drop the trail, keep the totals
      S.recent = S.recent.slice(-60);
      S.links = S.links.slice(-60);
      try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e2) {}
    }
    mine = false;
  }
  /* now=true writes synchronously. The page is about to be frozen or closed, and a
     400 ms timer is 400 ms the tab does not have. */
  function save(now) {
    if (now) { writeNow(); return; }
    clearTimeout(saveTimer);
    saveTimer = setTimeout(writeNow, 400);
  }
  /* A second tab holds the whole log in memory too, and writes it back wholesale.
     Without this the tab that saves last erases whatever the other one recorded. */
  var mine = false;
  window.addEventListener('storage', function (e) {
    if (e.key !== KEY || mine) return;
    if (saveTimer) writeNow();        // bank ours first, then take theirs
    else S = null;
  });

  function today() {
    var d = new Date();
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  function day() {
    load();
    if (!S.days[today()]) S.days[today()] = { sec: 0, audio: 0, words: 0, links: 0 };
    return S.days[today()];
  }
  function trail(kind, text) {
    load();
    S.recent.push({ t: Date.now(), k: kind, x: String(text || '').slice(0, 90) });
    if (S.recent.length > CAP) S.recent = S.recent.slice(-CAP);
  }

  /* ---- dwell time per chapter ---- */
  var cur = null, since = 0;
  /* flush banks the time but keeps the chapter; closeOut also forgets it. Sending the
     phone to the background used to closeOut, so nothing she read after the first app
     switch of the session was ever counted. */
  function flush() {
    if (!cur) return;
    var sec = Math.round((Date.now() - since) / 1000);
    if (sec > 2 && sec < 3600) {          // ignore flicks and forgotten tabs
      load();
      var c = S.chapters[cur.key] || (S.chapters[cur.key] = { no: cur.no, zh: cur.zh, sec: 0, opens: 0 });
      c.sec += sec; c.zh = cur.zh; c.no = cur.no; c.key = cur.key; c.last = Date.now();
      day().sec += sec;
      S.lastTs = Date.now();
      save();
    }
    since = Date.now();
  }
  function closeOut() { flush(); cur = null; }
  function view(ch) {
    closeOut();
    load();
    var key = ch.key || ('ch' + ch.no);
    var c = S.chapters[key] || (S.chapters[key] = { no: ch.no, zh: ch.zh, sec: 0, opens: 0 });
    c.opens++; c.no = ch.no; c.zh = ch.zh; c.key = key; c.last = Date.now();
    cur = { key: key, no: ch.no, zh: ch.zh };
    since = Date.now();
    S.lastTs = Date.now();
    trail('章', '第' + ch.no + '章 ' + ch.zh);
    save();
  }
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { flush(); save(true); } else if (cur) since = Date.now();
  });
  /* pagehide is not necessarily the end: on iOS it fires every time she switches
     apps and the page goes into the back/forward cache. closeOut() cleared the
     current chapter and nothing put it back, so nothing she read after the first
     app switch was ever counted. Bank the time, keep the chapter, and re-arm when
     the page comes back. */
  window.addEventListener('pagehide', function () { flush(); save(true); });
  window.addEventListener('pageshow', function () { if (cur) since = Date.now(); });
  /* One sitting longer than an hour used to be thrown away whole rather than
     clamped. Bank it every minute instead — but only while she is actually here,
     so a tab forgotten on a desk still does not invent study time. */
  var lastAct = Date.now();
  ['pointerdown', 'keydown', 'touchstart', 'wheel'].forEach(function (ev) {
    document.addEventListener(ev, function () { lastAct = Date.now(); }, true);
  });
  setInterval(function () {
    if (!document.hidden && cur && Date.now() - lastAct < 3e5) flush();
  }, 60000);

  /* ---- individual actions ---- */
  function audio(label) { load(); S.audio++; day().audio++; save(); }
  function word(w) {
    load();
    w = String(w || '').toLowerCase();
    if (!w) return;
    S.words[w] = (S.words[w] || 0) + 1;
    day().words++;
    trail('词', w);
    save();
  }
  function link(title, url) {
    load();
    S.links.push({ t: Date.now(), title: String(title || '').slice(0, 80), url: url });
    if (S.links.length > CAP) S.links = S.links.slice(-CAP);
    day().links++;
    trail('打开', title);
    save();
  }
  function flash(n) { load(); S.flash++; trail('背诵', n + ' 张'); save(); }
  function search(q) { load(); S.searches++; trail('搜索', q); save(); }

  /* ---- readable summary ---- */
  function mins(sec) {
    if (sec < 60) return sec + ' 秒';
    if (sec < 3600) return Math.round(sec / 60) + ' 分钟';
    return (sec / 3600).toFixed(1) + ' 小时';
  }
  function stamp(ts) {
    var d = new Date(ts);
    return ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2) + ' ' +
           ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }
  function summary() {
    load();
    var days = Object.keys(S.days).sort();
    var total = 0, active = 0;
    days.forEach(function (d) { total += S.days[d].sec; if (S.days[d].sec > 60) active++; });
    var chs = Object.keys(S.chapters).map(function (k) { return S.chapters[k]; })
                    .sort(function (a, b) { return b.sec - a.sec; });
    var ws = Object.keys(S.words).map(function (w) { return { w: w, n: S.words[w] }; })
                   .sort(function (a, b) { return b.n - a.n; });
    return { days: days, total: total, activeDays: active, chapters: chs, words: ws,
             links: S.links.slice().reverse(), audio: S.audio, flash: S.flash,
             searches: S.searches, last: S.lastTs, since: S.firstTs, recent: S.recent.slice().reverse() };
  }
  function asText() {
    var s = summary();
    var L = ['王思 · 学习记录',
             '统计区间：' + (s.days[0] || '—') + ' 起，共 ' + s.activeDays + ' 个有效学习日',
             '累计时长：' + mins(s.total) + '　发音播放 ' + s.audio + ' 次　查词 ' +
               Object.keys(S.words).length + ' 个　背诵 ' + s.flash + ' 轮',
             '最近一次：' + (s.last ? stamp(s.last) : '—'), '', '【看得最多的章节】'];
    s.chapters.slice(0, 8).forEach(function (c) {
      L.push('  第' + c.no + '章 ' + c.zh + ' —— ' + mins(c.sec) + '，进入 ' + c.opens + ' 次');
    });
    L.push('', '【打开过的视频 / 资源】');
    if (!s.links.length) L.push('  （还没点开过）');
    s.links.slice(0, 15).forEach(function (x) { L.push('  ' + stamp(x.t) + '  ' + x.title); });
    L.push('', '【查得最多的词】');
    L.push('  ' + (s.words.slice(0, 20).map(function (x) { return x.w + '×' + x.n; }).join('、') || '—'));
    return L.join('\n');
  }

  /* 连续学习天数：今天还没开始不算断，从昨天接着数 */
  function dkey(d) {
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  function streak() {
    load();
    var n = 0, d = new Date();
    var t = S.days[dkey(d)];
    if (!(t && t.sec > 60)) d.setDate(d.getDate() - 1);
    while (S.days[dkey(d)] && S.days[dkey(d)].sec > 60) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }
  function dayStat() { var v = day(); return { sec: v.sec, audio: v.audio, words: v.words, links: v.links }; }
  window.tcfStats = { view: view, audio: audio, word: word, link: link, flash: flash,
                      bank: flush,
                      search: search, summary: summary, asText: asText, mins: mins,
                      streak: streak, dayStat: dayStat, today: today,
                      stamp: stamp, reset: function () { S = blank(); save(); } };
})();
