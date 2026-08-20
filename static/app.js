/* TCF 法语学习助手 · 王思专属版 */
(function () {
  'use strict';
  var DOC = null, CUR = 0, QUEUE = [], QI = -1, RATE = 1, REPEAT = false, REP2 = false;
  var PLAY_SEQ = 0, VIEW = 'chapter', HITS = [], ARMED = false;
  var au = document.getElementById('au');
  /* All 19,574 clips are mp3. They used to be 89% Ogg/Opus, which Safari only learned
     in 17.4 — on an older iPhone a third of the book was silent with no explanation. */
  var TOUCH = matchMedia('(hover:none)').matches;
  /* same iOS unlock story as lookup.js: the flashcard view auto-plays after an
     async render, which is outside the gesture */
  (function () {
    var done = false;
    function unlock() {
      if (done) return;
      done = true;
      try {
        au.muted = true;
        var r = au.play();
        if (r && r.then) r.then(function () { au.pause(); au.currentTime = 0; au.muted = false; })
                          .catch(function () { au.muted = false; });
        else au.muted = false;
      } catch (e) { au.muted = false; }
    }
    document.addEventListener('touchend', unlock, true);
    document.addEventListener('mousedown', unlock, true);
  })();
  var $ = function (id) { return document.getElementById(id); };
  window.tcfAudio = { stop: function () { stopAll(true); } };

  /* ---------------- utils ---------------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  /* Whatever is not on this list is shown to her as literal angle brackets. That has
     bitten twice now: the punctuation lesson in 第 12 章 printed <code>:</code> at her
     instead of a colon, and the wrong-form examples lost the strike-through that was
     the entire point of writing them. Add a tag here before using it in the data. */
  var RICH_TAGS = ['b', 'i', 'u', 's', 'code', 'sup', 'sub'];
  function rich(s) {
    var t = esc(s);
    RICH_TAGS.forEach(function (g) {
      t = t.split('&lt;' + g + '&gt;').join('<' + g + '>').split('&lt;/' + g + '&gt;').join('</' + g + '>');
    });
    return t.split('&lt;br&gt;').join('<br>').split('\n').join('<br>');
  }
  // a flashcard front is plain text, so markup that survives into it is visible
  function plain(s) {
    return String(s == null ? '' : s).replace(/<[^>]+>/g, '');
  }
  /* She types on a phone keyboard, where é and ç cost a long press. Searching for
     「etudiant」 used to find 0 of the 68 étudiant in the book. Fold accents and both
     apostrophes away on each side and the two spellings become the same word. */
  function fold(s) {
    s = String(s == null ? '' : s).toLowerCase().replace(/[\u2018\u2019\u02bc]/g, "'");
    if (s.normalize) { try { s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, ''); } catch (e) {} }
    return s;
  }
  function toast(m) {
    var t = $('toast'); t.textContent = m; t.classList.add('on');
    clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('on'); }, 1800);
  }
  var store = {
    get: function (k, d) {
      try { var v = JSON.parse(localStorage.getItem('tcf_' + k)); return v === null || v === undefined ? d : v; }
      catch (e) { return d; }
    },
    set: function (k, v) { try { localStorage.setItem('tcf_' + k, JSON.stringify(v)); } catch (e) {} }
  };

  /* ---------------- audio ---------------- */
  function clearHL() {
    // dots and table cells take .playing too, and used to keep it for the whole chapter
    document.querySelectorAll('.playing').forEach(function (e) { e.classList.remove('playing'); });
    document.querySelectorAll('.mline.play,.dtx.play').forEach(function (e) { e.classList.remove('play'); });
  }
  function highlight(aid, srcEl) {
    clearHL();
    // model sentences carry data-play, not data-aid — match both or they never light up
    var b = srcEl && srcEl.classList ? srcEl : null;
    if (!b) {
      var all = document.querySelectorAll('[data-aid="' + aid + '"], [data-play="' + aid + '"]');
      var near = window.innerHeight / 3, bd = Infinity;
      for (var i = 0; i < all.length; i++) {
        var d = Math.abs(all[i].getBoundingClientRect().top - near);
        if (d < bd) { bd = d; b = all[i]; }
      }
    }
    if (!b) return;
    b.classList.add('playing');
    var host = b.classList.contains('mline') ? b : (b.closest('.mline') || b.closest('.dtx') || b.closest('.b-card') || b.closest('.pcard'));
    if (host) {
      if (host.classList.contains('mline') || host.classList.contains('dtx')) host.classList.add('play');
      var r = host.getBoundingClientRect();
      if (r.top < 70 || r.bottom > window.innerHeight - 90) host.scrollIntoView({ block: 'center' });
    }
  }
  function serverGone() {
    document.body.innerHTML = '<div style="display:flex;height:100vh;align-items:center;justify-content:center;' +
      'flex-direction:column;gap:14px;font-family:\'Segoe UI\',\'Microsoft YaHei\',sans-serif;color:#5b6474;text-align:center;padding:24px">' +
      '<div style="font-size:40px">🔌</div><div style="font-size:19px;color:#18202e">和程序断开了</div>' +
      '<div>可能是刚才点过「⏻ 退出」，或者程序被关掉了。<br>请重新双击 <b>TCF法语学习助手.exe</b>，然后关掉这个网页。</div></div>';
  }
  /* a queue only advances while it owns playback: anything that interrupts it
     (single clip, chapter switch, search, flashcards) must drop it, or the old
     queue resumes on its own after the interrupting clip ends */
  function dropQueue() {
    QUEUE = [];
    QI = -1;
  }
  function stopAll(keepLookup) {
    dropQueue();
    REP2 = false;
    ARMED = false;
    try { au.pause(); au.currentTime = 0; } catch (e) {}
    // the word / long-press clip lives in lookup.js and used to survive every stop
    if (!keepLookup && window.tcfLookup && window.tcfLookup.stop) window.tcfLookup.stop();
    clearHL();
    $('pPlay').textContent = '▶';
    $('pNow').textContent = '点任意法语句子即可发音';
  }

  function play(aid, label, fromQueue, srcEl) {
    if (!aid) { toast('这一条没有音频'); return; }
    if (!fromQueue) dropQueue();
    REP2 = false;
    ARMED = true;
    if (window.tcfLookup && window.tcfLookup.stop) window.tcfLookup.stop();
    au.pause();
    au.src = window.CLIP(aid);
    au.playbackRate = RATE;
    var mine = ++PLAY_SEQ;
    au.play().then(function () {
      // count it only once it actually made a sound
      missRun = 0;
      if (mine === PLAY_SEQ && window.tcfStats) window.tcfStats.audio(label);
    }, function (e) {
      // swapping src aborts the previous play(): that is normal, not a broken audio pack
      if (e && (e.name === 'AbortError' || mine !== PLAY_SEQ)) return;
      fetch('/api/ping').then(function () {
        toast('这一条没能播放，换一句试试');
      }).catch(function () { serverGone(); });
    });
    highlight(aid, srcEl);
    $('pNow').textContent = label || '正在播放…';
    $('pPlay').textContent = '⏸';
  }
  var missRun = 0;
  au.addEventListener('error', function () {
    /* Offline on a chapter she has not downloaded, every clip 404s instantly and
       the queue used to walk all ~200-400 of them in one synchronous burst. Stop
       after a few and say why — the status text is display:none on phones. */
    if (++missRun >= 4) {
      missRun = 0; dropQueue(); ARMED = false; clearHL();
      $('pPlay').textContent = '▶';
      $('pNow').textContent = '这一章的发音还没下载';
      toast('这一章的发音还没下载，连上网再点一次');
      return;
    }
    if (QI >= 0 && QI < QUEUE.length - 1) { QI++; setTimeout(playQueueItem, 120); return; }
    clearHL(); QI = -1;
    ARMED = false;          // otherwise ▶ keeps retrying the clip that just failed
    $('pPlay').textContent = '▶';
    $('pNow').textContent = '播放失败';
  });
  au.addEventListener('ended', function () {
    if (REPEAT && !REP2) { REP2 = true; au.currentTime = 0; au.play(); return; }
    REP2 = false;
    if (QI >= 0 && QI < QUEUE.length - 1) { QI++; playQueueItem(); }
    else { clearHL(); $('pPlay').textContent = '▶'; QI = -1; $('pNow').textContent = '播放结束'; }
  });
  function playQueueItem() {
    var it = QUEUE[QI];
    if (!it) return;
    play(it.aid, '（' + (QI + 1) + '/' + QUEUE.length + '） ' + it.text.slice(0, 70), true);
  }
  function startQueue(list, from) {
    QUEUE = list.filter(function (x) { return x && x.aid; });
    if (!QUEUE.length) { toast('本章没有可朗读的法语'); return; }
    QI = from || 0;
    playQueueItem();
  }

  /* ---------------- speak button ---------------- */
  function spk(aid, text) {
    if (!aid) return '';
    return '<button class="spk" data-aid="' + aid + '" data-t="' + esc(text || '').slice(0, 90) + '" title="朗读">🔊</button>';
  }

  /* ---------------- rendering ---------------- */
  /* Most of the French in the book sits inside paragraphs, tips and warnings, which
     have no per-sentence slot. One control per block reads them in order. */
  function voiceBar(b, bi) {
    if (!b.voice || !b.voice.length) return '';
    return '<div class="vbar"><button class="vplay" data-voice="' + bi + '">🔊 朗读本段法语' +
      '<span class="vn">' + b.voice.length + ' 句</span></button>' +
      b.voice.map(function (v, i) {
        return '<span class="vsent" data-play="' + v.aid + '" title="' + esc(v.fr) + '">' +
               (i + 1) + '</span>';
      }).join('') + '</div>';
  }

  function renderBlocks(bs, color) {
    var h = [];
    bs.forEach(function (b, bi) {
      var k = b.kind;
      if (k === 'h3') h.push('<h3 class="b-h3" style="border-color:' + color + '">' + esc(b.title) + '</h3>');
      else if (k === 'h4') h.push('<h4 class="b-h4">' + esc(b.title) + '</h4>');
      else if (k === 'para') h.push('<p class="b-para">' + rich(b.text) + '</p>' + voiceBar(b, bi));
      else if (k === 'bullets') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        h.push('<ul class="b-ul">' + (b.items || []).map(function (x) { return '<li>' + rich(x) + '</li>'; }).join('') + '</ul>' + voiceBar(b, bi));
      } else if (k === 'steps') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        h.push('<ol class="b-steps">' + (b.items || []).map(function (x, i) {
          return '<li><span class="stepn" style="background:' + color + '">' + (i + 1) + '</span><div>' + rich(x) + '</div></li>';
        }).join('') + '</ol>' + voiceBar(b, bi));
      } else if (k === 'table') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        var cols = b.columns || [], rows = b.rows || [], aids = b.aids || [];
        h.push('<div class="tabwrap"><table class="b-tab"><thead style="background:' + color + '"><tr>' +
          cols.map(function (c) { return '<th>' + esc(c) + '</th>'; }).join('') + '</tr></thead><tbody>' +
          rows.map(function (r, ri) {
            return '<tr>' + r.map(function (c, ci) {
              var a = (aids[ri] || [])[ci];
              return '<td>' + (a ? '<span class="frtext" data-play="' + a + '">' + rich(c) + '</span> ' + spk(a, c) : rich(c)) + '</td>';
            }).join('') + '</tr>';
          }).join('') + '</tbody></table></div>' + voiceBar(b, bi));
      } else if (k === 'cards') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        (b.cards || []).forEach(function (c, ci) {
          var key = CUR + ':' + bi + ':' + ci;
          h.push('<div class="b-card" style="border-left-color:' + color + '" data-ck="' + key + '">' +
            '<div class="cf">' + spk(c.aid, c.fr) + '<span class="frtext" data-play="' + (c.aid || '') + '">' + rich(c.fr) + '</span></div>' +
            '<div class="cz">' + rich(c.zh) + '</div>' +
            (c.note ? '<div class="cn">💡 ' + rich(c.note) + '</div>' : '') + '</div>');
        });
        h.push(voiceBar(b, bi));
      } else if (k === 'model') {
        var m = b.model || {}, lines = m.lines || [];
        h.push('<div class="b-model" style="border-color:' + color + '">' +
          '<div class="mhead" style="background:' + color + '"><span class="mtag">范文 / Copie modèle</span>' +
          '<span><button class="btn" style="background:rgba(255,255,255,.2);color:#fff;border-color:transparent" ' +
          'data-playmodel="' + bi + '">▶ 整篇朗读</button> ' +
          (m.word_count ? '<span class="mwc">' + esc(m.word_count) + '</span>' : '') + '</span></div>' +
          '<div class="mprompt"><b>题目 Sujet</b><br>' + rich(m.prompt) + '</div>' +
          '<div class="mfr">' + lines.map(function (l) {
            return '<span class="mline" data-play="' + (l.aid || '') + '">' + rich(l.fr) + '</span> ';
          }).join('') + '</div>' +
          '<div class="mzh">' + rich(m.text_zh).split('\n').join('<br>') + '</div>' +
          ((m.notes || []).length ? '<div class="mnotes"><div class="mnt">✍ 讲评 Analyse</div><ol>' +
            m.notes.map(function (n) { return '<li>' + rich(n) + '</li>'; }).join('') + '</ol></div>' : '') +
          '</div>' + voiceBar(b, bi));
      } else if (k === 'dialogue') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        h.push('<div class="b-dial"><div style="margin-bottom:8px"><button class="btn" data-playdial="' + bi + '">▶ 播放整段对话（双人配音）</button></div>' +
          (b.dialogue || []).map(function (d) {
            return '<div class="dl ' + (d.me ? 'cand' : 'exam') + '"><div class="dsp">' + esc(d.speaker) + '</div>' +
              '<div class="dtx"><div>' + spk(d.aid, d.fr) + '<span class="frtext" data-play="' + (d.aid || '') + '">' + rich(d.fr) + '</span></div>' +
              '<div class="dzh">' + rich(d.zh) + '</div></div></div>';
          }).join('') + '</div>');
      } else if (k === 'links') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        /* 91 cards in one chapter is a lot to eyeball; let her narrow it down first */
        var lvn = {}, nEmbed = 0, nCn = 0;
        (b.links || []).forEach(function (x) {
          if (x.level) lvn[x.level] = (lvn[x.level] || 0) + 1;
          if (x.embed) nEmbed++;
          if (x.cn_ok === 'yes') nCn++;
        });
        h.push('<div class="lfilter">' +
          '<button class="lfb on" data-f="all">全部 ' + (b.links || []).length + '</button>' +
          ['A2', 'B1', 'B2'].filter(function (L) { return lvn[L]; }).map(function (L) {
            return '<button class="lfb lv-' + L + '" data-f="lv:' + L + '">' + L + ' ' + lvn[L] + '</button>';
          }).join('') +
          (nEmbed ? '<button class="lfb" data-f="embed">▶ 能直接播 ' + nEmbed + '</button>' : '') +
          (nCn ? '<button class="lfb" data-f="cn">国内可看 ' + nCn + '</button>' : '') +
          '</div>');
        h.push('<div class="lgrid">' + (b.links || []).map(function (x) {
          // only the domain family is a fact; the rest is a guess and says so
          var cn = x.cn_ok === 'yes' ? '<span class="lcn ok">国内可看</span>'
                 : x.cn_ok === 'vpn' ? '<span class="lcn vpn">需要梯子</span>'
                 : '<span class="lcn unsure">大概率能开 · 点一下试试</span>';
          return '<a class="lcard" href="' + esc(x.url) + '" target="_blank" rel="noopener noreferrer"' +
            ' data-lv="' + esc(x.level || '') + '" data-embed-ok="' + (x.embed ? '1' : '0') +
            '" data-cn="' + esc(x.cn_ok || '') + '">' +
            '<div class="lh"><span class="lt">' + esc(x.title) + '</span>' +
            (x.level ? '<span class="lv lv-' + esc(x.level) + '">' + esc(x.level) + '</span>' : '') +
            '</div>' +
            '<div class="lmeta">' + [x.platform, x.kind, x.length, x.accent]
              .filter(Boolean).map(esc).join(' · ') +
            (x.free === false ? ' · <b>需订阅</b>' : '') + '</div>' +
            (x.level_why ? '<div class="llw">' + esc(x.level) + '：' + rich(x.level_why) + '</div>' : '') +
            '<div class="lwhy">' + rich(x.why || '') + '</div>' +
            (x.how ? '<div class="lhow">▸ ' + rich(x.how) + '</div>' : '') +
            '<div class="lfoot">' + cn +
              (x.embed ? '<span class="lplay" data-embed="' + esc(x.embed) + '">▶ 在这里看</span>' : '') +
              '<span class="lgo">去网站 ↗</span></div>' +
            '</a>';
        }).join('') + '</div>');
      } else if (k === 'tip') {
        h.push('<div class="b-tip"><div class="bt">💡 ' + esc(b.title || '提示') + '</div>' + rich(b.text) +
               voiceBar(b, bi) + '</div>');
      } else if (k === 'warn') {
        h.push('<div class="b-warn"><div class="bt">⚠️ ' + esc(b.title || '易错警告') + '</div>' + rich(b.text) +
               voiceBar(b, bi) + '</div>');
      }
    });
    return h.join('');
  }

  function renderTopics() {
    // never hard-code the number: inserting chapters upstream would leave it lying
    var no = (DOC.chapters[CUR] || {}).no || '';
    var h = ['<div class="chead" style="background:linear-gradient(120deg,#be185d,#be185dbb)">' +
      '<div class="cno">第 ' + no + ' 章 · LEXIQUE</div><h1>十大话题 CLB7+ 词组库（200 组）</h1>' +
      '<div class="cfr">Lexique thématique — 10 thèmes × 20 expressions</div></div>',
      '<div class="cintro">每个话题挑 <b>8–10 组</b>最顺口的练到脱口而出。点任意法语即可听加拿大法语发音；' +
      '例句可以整句背下来当"半成品答案"。想集中背诵，点上方 <b>🎴 背诵模式</b>。</div>'];
    DOC.topics.forEach(function (t) {
      h.push('<div class="thead" style="background:linear-gradient(120deg,' + t.color + ',' + t.color + 'cc)">' +
        '<div><h2>' + esc(t.zh) + '</h2><div class="fr">' + esc(t.fr) + '</div></div>' +
        '<div><button class="btn" style="background:rgba(255,255,255,.2);color:#fff;border-color:transparent" ' +
        'data-playtopic="' + t.key + '">▶ 连续朗读本话题</button></div></div>');
      t.entries.forEach(function (e, i) {
        h.push('<div class="pcard" style="border-left-color:' + t.color + '">' +
          '<div class="ph"><span class="idx" style="background:' + t.color + '">' + (i + 1) + '</span>' +
          spk(e.aid, e.phrase) + '<span class="frtext" data-play="' + (e.aid || '') + '">' + esc(e.phrase) + '</span></div>' +
          '<div class="zh">' + rich(e.zh) + '</div>' +
          '<div class="ex">' + spk(e.aid_ex, e.example_fr) + '<span class="frtext" data-play="' + (e.aid_ex || '') + '">' + esc(e.example_fr) + '</span></div>' +
          '<div class="exzh">' + rich(e.example_zh) + '</div>' +
          '<div class="note">💡 ' + rich(e.note) + '</div></div>');
      });
    });
    return h.join('');
  }

  var markTimer = null;
  function markRead(c, i) {
    var done = store.get('done', {});
    if (!done[c.key || i]) { done[c.key || i] = 1; store.set('done', done); markVisited(); }
  }
  function renderChapter(i, restoring) {
    stopAll();               // otherwise the previous chapter keeps reading itself aloud
    CUR = i;
    VIEW = 'chapter';
    var c = DOC.chapters[i];
    var w = $('wrap');
    if (c.key === '__topics__') { w.innerHTML = renderTopics(); }
    else {
      w.innerHTML = '<div class="chead" style="background:linear-gradient(120deg,' + c.color + ',' + c.color + 'bb)">' +
        '<div class="cno">第 ' + c.no + ' 章 · CHAPITRE ' + c.no + '</div><h1>' + esc(c.zh) + '</h1>' +
        '<div class="cfr">' + esc(c.fr) + '</div></div>' +
        '<div class="cintro"><b>本章导读　</b>' + esc(c.intro) + '</div>' +
        renderBlocks(c.blocks, c.color);
    }
    /* on a phone, moving to the next chapter meant opening the drawer and hunting
       for the right row every single time */
    var prev = DOC.chapters[i - 1], next = DOC.chapters[i + 1];
    w.innerHTML += '<div class="chnav">' +
      (prev ? '<button class="chn" data-go="' + (i - 1) + '"><span>← 上一章</span>' +
              '<b>' + esc(prev.zh) + '</b></button>' : '<span></span>') +
      (next ? '<button class="chn nx" data-go="' + (i + 1) + '"><span>下一章 →</span>' +
              '<b>' + esc(next.zh) + '</b></button>' : '<span></span>') +
      '</div>';
    $('main').scrollTop = 0;
    if (window.__markScrollables) window.__markScrollables();
    document.querySelectorAll('.navitem').forEach(function (e) { e.classList.toggle('on', +e.dataset.i === i); });
    store.set('last', i);
    if (window.tcfStats) window.tcfStats.view(c);
    /* Restoring where she left off is not the same as reading it. Marking the
       restored chapter read made a fresh install claim 1 / 56 before she had seen
       the welcome screen, and pushed the plan's 新课 slot to 第 2 章 on day one.
       Deliberate navigation counts immediately; a restore has to earn it. */
    clearTimeout(markTimer);
    if (restoring) markTimer = setTimeout(function () { markRead(c, i); }, 45000);
    else markRead(c, i);
    markVisited();
  }

  function markVisited() {
    var done = store.get('done', {}), n = 0;
    document.querySelectorAll('.navitem').forEach(function (e) {
      var c = DOC && DOC.chapters[+e.dataset.i];
      if (c && done[c.key || +e.dataset.i]) { e.classList.add('seen'); n++; }
    });
    var total = DOC ? DOC.chapters.length : 0;
    if (total && $('pgBar')) {
      $('pgBar').style.width = Math.round(n / total * 100) + '%';
      $('pgTx').textContent = n + ' / ' + total + ' 章';
    }
  }

  /* ---------------- collect audio of current view ---------------- */
  function currentClips() {
    var out = [];
    document.querySelectorAll('[data-play]').forEach(function (e) {
      var a = e.getAttribute('data-play');
      // the prose dots show only a number; their title carries the sentence
      if (a) out.push({ aid: a, text: (e.getAttribute('title') || e.textContent).trim() });
    });
    var seen = {}, uniq = [];
    out.forEach(function (x) { if (!seen[x.aid]) { seen[x.aid] = 1; uniq.push(x); } });
    return uniq;
  }

  /* ---------------- flashcards ---------------- */
  var FC = { list: [], i: 0, shown: false };
  function fcBuild() {
    if (VIEW === 'search') {          //背诵搜索结果，而不是上一次浏览的章节
      return HITS.filter(function (h) { return h.aid && h.zh; })
                 .map(function (h) { return { fr: h.fr, zh: h.zh, aid: h.aid }; });
    }
    var c = DOC.chapters[CUR], list = [];
    if (c.key === '__topics__') {
      DOC.topics.forEach(function (t) {
        t.entries.forEach(function (e) {
          list.push({ fr: e.phrase, zh: e.zh, aid: e.aid, exf: e.example_fr, exz: e.example_zh, note: e.note });
        });
      });
    } else {
      c.blocks.forEach(function (b) {
        if (b.kind === 'cards') (b.cards || []).forEach(function (x) {
          list.push({ fr: x.fr, zh: x.zh, aid: x.aid, note: x.note });
        });
      });
    }
    return list;
  }
  /* 「＋ 加入生词本」 collected words she could look at but never drill — the list was
     a dead end. Same flashcard machinery, fed from her own saved words. */
  function fcFromVocab(items) {
    stopAll();
    FC.list = items.filter(function (x) { return x.word; }).map(function (x) {
      return { fr: x.word, zh: x.gloss || '（没有释义）', note: x.lemma && x.lemma !== x.word ? '原形 ' + x.lemma : '',
               exf: x.sentence || '', aid: null, vocab: true };
    });
    FC.i = 0;
    if (!FC.list.length) { toast('生词本还是空的'); return; }
    $('vbwrap').classList.add('hidden');
    $('fcwrap').classList.remove('hidden');
    if (window.tcfStats) window.tcfStats.flash(FC.list.length);
    fcShow();
  }
  function fcShow() {
    var it = FC.list[FC.i];
    if (!it) { fcClose(); toast('本轮结束，做得好！'); return; }
    FC.shown = false;
    $('fcProg').textContent = '第 ' + (FC.i + 1) + ' / ' + FC.list.length + ' 张　·　' +
      (TOUCH ? '点「看答案」，再选会了 / 还不会' : '空格看答案，← 还不会，→ 会了');
    $('fcFr').textContent = plain(it.fr);   // some table cells carry <b>, and this is plain text
    $('fcZh').textContent = '';
    $('fcEx').classList.add('hidden');
    if (it.aid) play(it.aid, it.fr.slice(0, 60));
    // saved words have no chapter clip; they play from the word pack instead
    else if (it.vocab && window.tcfLookup) window.tcfLookup.play(it.fr);
  }
  function fcReveal() {
    var it = FC.list[FC.i]; if (!it) return;
    FC.shown = true;
    $('fcZh').innerHTML = rich(it.zh) + (it.note ? '　　💡 ' + rich(it.note) : '');
    if (it.exf) {
      $('fcExFr').textContent = it.exf; $('fcExZh').textContent = it.exz || '';
      $('fcEx').classList.remove('hidden');
    }
  }
  function fcNext(known) {
    var it = FC.list[FC.i];
    if (!known && it) FC.list.push(it);           // wrong ones come back at the end
    FC.LAST = { i: FC.i, len: FC.list.length, pushed: !known && !!it };
    FC.i++; fcShow();
  }
  /* fat-finger insurance: 「会了」 and 「还不会」 sit next to each other on a phone */
  function fcBack() {
    if (!FC.LAST || FC.i !== FC.LAST.i + 1) { toast('只能撤销上一张'); return; }
    if (FC.LAST.pushed) FC.list.pop();
    FC.i = FC.LAST.i;
    FC.LAST = null;
    fcShow();
    fcReveal();
  }
  function fcOpen() {
    stopAll();               // a running chapter queue would talk over every card
    FC.list = fcBuild(); FC.i = 0;
    if (!FC.list.length) { toast(VIEW === 'search' ? '这些结果里没有带中文的句子，背不了' : '本章没有可背诵的词卡'); return; }
    $('fcwrap').classList.remove('hidden');
    if (window.tcfStats) window.tcfStats.flash(FC.list.length);
    fcShow();
  }
  function fcClose() { $('fcwrap').classList.add('hidden'); stopAll(); }

  /* ---------------- search ---------------- */
  var SCROLL0 = 0;
  function search(q) {
    q = fold(q.trim());
    if (q.length < 2) {
      // coming back from a search used to dump her at the top of a chapter that can
      // be eighty screens long
      if (VIEW === 'search') { var back = SCROLL0; renderChapter(CUR); $('main').scrollTop = back; }
      return;
    }
    if (VIEW !== 'search') SCROLL0 = $('main').scrollTop;
    stopAll();
    VIEW = 'search';
    var hits = [], seen = {};
    function push(ch, fr, zh, aid) {
      if (!fr) return;
      if (fold(fr + ' ' + (zh || '')).indexOf(q) < 0) return;
      var k = (aid || '') + '|' + fr;
      if (seen[k]) return;
      seen[k] = 1;
      hits.push({ ch: ch, fr: fr, zh: zh || '', aid: aid });
    }
    // a resource matches on its title, platform and blurb, and links out instead of playing
    function pushLink(ch, x) {
      var hay = fold([x.title, x.platform, x.kind, x.why, x.how, x.accent, x.level].join(' '));
      if (hay.indexOf(q) < 0) return;
      var k = 'L|' + x.url;
      if (seen[k]) return;
      seen[k] = 1;
      hits.push({ ch: ch, fr: x.title, zh: x.why || '', url: x.url, level: x.level,
                  meta: [x.platform, x.kind, x.length].filter(Boolean).join(' · ') });
    }
    DOC.chapters.forEach(function (c) {
      if (c.key === '__topics__') return;
      c.blocks.forEach(function (b) {
        (b.cards || []).forEach(function (x) { push(c, x.fr, x.zh, x.aid); });
        (b.dialogue || []).forEach(function (x) { push(c, x.fr, x.zh, x.aid); });
        // tables and model sentences carry most of the French in the book — index them too
        ((b.model || {}).lines || []).forEach(function (l) { push(c, l.fr, '', l.aid); });
        (b.rows || []).forEach(function (row, ri) {
          row.forEach(function (cell, ci) {
            var a = ((b.aids || [])[ri] || [])[ci];
            if (a) push(c, cell, (row[ci + 1] || row[ci - 1] || ''), a);
          });
        });
        // prose sentences and the resource library were rendered but not searchable:
        // ~4000 French lines and 168 links that could only be found by scrolling
        (b.voice || []).forEach(function (v) { push(c, v.fr, '', v.aid); });
        (b.links || []).forEach(function (x) {
          pushLink(c, x);
        });
      });
    });
    DOC.topics.forEach(function (t) {
      t.entries.forEach(function (e) {
        push({ zh: '话题库 · ' + t.zh, color: t.color }, e.phrase, e.zh, e.aid);
        push({ zh: '话题库 · ' + t.zh, color: t.color }, e.example_fr, e.example_zh, e.aid_ex);
      });
    });
    HITS = hits.slice(0, 300);
    if (window.tcfStats) window.tcfStats.search(q);
    var h = ['<div class="chead" style="background:linear-gradient(120deg,#334155,#334155bb)">' +
      '<div class="cno">搜索结果 · RECHERCHE</div><h1>「' + esc(q) + '」共 ' + hits.length + ' 条</h1></div>'];
    HITS.forEach(function (x) {
      if (x.url) {                       // a resource: open it, there is nothing to play
        h.push('<a class="lcard" href="' + esc(x.url) + '" target="_blank" rel="noopener noreferrer">' +
          '<div class="lh"><span class="lt">' + esc(x.fr) + '</span>' +
          (x.level ? '<span class="lv lv-' + esc(x.level) + '">' + esc(x.level) + '</span>' : '') + '</div>' +
          (x.meta ? '<div class="lmeta">' + esc(x.meta) + '</div>' : '') +
          (x.zh ? '<div class="lwhy">' + rich(x.zh) + '</div>' : '') +
          '<div class="lfoot"><span class="lcn unsure">📍 ' + esc(x.ch.zh) + '</span>' +
          '<span class="lgo">打开 ↗</span></div></a>');
        return;
      }
      h.push('<div class="b-card" style="border-left-color:' + (x.ch.color || '#334155') + '">' +
        '<div class="cf">' + spk(x.aid, x.fr) + '<span class="frtext" data-play="' + (x.aid || '') + '">' + rich(x.fr) + '</span></div>' +
        (x.zh ? '<div class="cz">' + rich(x.zh) + '</div>' : '') +
        '<div class="cn">📍 ' + esc(x.ch.zh) + '</div></div>');
    });
    if (hits.length > 300) h.push('<p class="b-para">（只显示前 300 条，试试更具体的关键词）</p>');
    if (!hits.length) h.push('<p class="b-para">没有找到。试试换个说法，或者只输入其中两三个词。</p>');
    $('wrap').innerHTML = h.join('');
    $('main').scrollTop = 0;
  }

  /* ---------------- events ---------------- */
  var qt;
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    var b = t.closest('[data-aid]');
    if (b) { play(b.dataset.aid, b.dataset.t, false, b); return; }
    var p = t.closest('[data-play]');
    if (p && p.getAttribute('data-play')) {
      play(p.getAttribute('data-play'), (p.getAttribute('title') || p.textContent).trim().slice(0, 70), false, p);
      return;
    }
    var vp = t.closest('[data-voice]');
    if (vp) {
      var vb = (VIEW === 'chapter' ? DOC.chapters[CUR].blocks[+vp.dataset.voice] : null);
      if (vb && vb.voice) startQueue(vb.voice.map(function (v) { return { aid: v.aid, text: v.fr }; }), 0);
      return;
    }
    var pm = t.closest('[data-playmodel]');
    if (pm) {
      var c = DOC.chapters[CUR], blk = c.blocks[+pm.dataset.playmodel];
      startQueue(((blk.model || {}).lines || []).map(function (l) { return { aid: l.aid, text: l.fr }; }), 0);
      return;
    }
    var pd = t.closest('[data-playdial]');
    if (pd) {
      var c2 = DOC.chapters[CUR], blk2 = c2.blocks[+pd.dataset.playdial];
      startQueue((blk2.dialogue || []).map(function (d) { return { aid: d.aid, text: d.speaker + ': ' + d.fr }; }), 0);
      return;
    }
    var pt = t.closest('[data-playtopic]');
    if (pt) {
      var tp = DOC.topics.filter(function (x) { return x.key === pt.dataset.playtopic; })[0];
      var list = [];
      tp.entries.forEach(function (e) {
        if (e.aid) list.push({ aid: e.aid, text: e.phrase });
        if (e.aid_ex) list.push({ aid: e.aid_ex, text: e.example_fr });
      });
      startQueue(list, 0);
      return;
    }
    var go = t.closest('[data-go]');
    if (go) { renderChapter(+go.dataset.go); return; }
    var fb = t.closest('.lfb');
    if (fb) {
      ev.preventDefault();
      var bar = fb.closest('.lfilter');
      bar.querySelectorAll('.lfb').forEach(function (x) { x.classList.toggle('on', x === fb); });
      var f = fb.dataset.f, grid = bar.nextElementSibling;
      grid.querySelectorAll('.lcard').forEach(function (c) {
        var show = f === 'all' ? true
                 : f === 'embed' ? c.dataset.embedOk === '1'
                 : f === 'cn' ? c.dataset.cn === 'yes'
                 : c.dataset.lv === f.slice(3);
        c.classList.toggle('hidden', !show);
      });
      return;
    }
    var pl = t.closest('[data-embed]');
    if (pl) {
      ev.preventDefault(); ev.stopPropagation();
      var card = pl.closest('.lcard');
      var open = card.querySelector('.lframe');
      if (open) { open.remove(); pl.textContent = '▶ 在这里看'; return; }
      var box = document.createElement('div');
      box.className = 'lframe';
      box.innerHTML = '<iframe src="' + pl.dataset.embed + '" scrolling="no" frameborder="0" ' +
                      'allowfullscreen="true" loading="lazy"></iframe>';
      card.appendChild(box);
      pl.textContent = '▼ 收起';
      if (window.tcfStats) window.tcfStats.link(card.querySelector('.lt').textContent, pl.dataset.embed);
      return;
    }
    var lc = t.closest('.lcard');
    if (lc && window.tcfStats) {
      window.tcfStats.link(lc.querySelector('.lt').textContent, lc.getAttribute('href'));
    }
    var nv = t.closest('.navitem');
    if (nv) {
      clearTimeout(qt);            // a pending debounce would repaint search results over the chapter
      $('q').value = '';
      renderChapter(+nv.dataset.i);
      drawer(false);
      return;
    }
  });

  /* ---------------- vocab book ---------------- */
  /* 「＋ 加入生词本」 used to have nowhere to lead once the trainer page was gone. */
  var VOCAB = [];
  function vbRender(items) {
    VOCAB = items || [];
    $('vbN').textContent = items.length ? items.length + ' 个词' : '';
    if (!items.length) {
      $('vbList').innerHTML = '<div class="vbe">还是空的。<br>看书时点任意法语单词，弹出的卡片右下角有「＋ 加入生词本」。</div>';
      return;
    }
    $('vbList').innerHTML =
      '<div class="vbact"><button class="btn pri" id="vbDrill">🎴 背这 ' + items.length + ' 个词</button>' +
      '<button class="btn" id="vbShuffle">🔀 打乱顺序背</button></div>' +
      items.slice().reverse().map(function (x) {
      return '<div class="vbi"><button class="btn vbs" data-w="' + esc(x.word) + '">🔊</button>' +
        '<div class="vbt"><div class="vbw">' + esc(x.word) +
        (x.lemma && x.lemma.toLowerCase() !== x.word.toLowerCase() ? ' <span class="vbl2">← ' + esc(x.lemma) + '</span>' : '') +
        '</div><div class="vbg">' + esc(x.gloss || '') + '</div>' +
        (x.sentence ? '<div class="vbx">' + esc(x.sentence) + '</div>' : '') + '</div>' +
        '<button class="btn vbd" data-del="' + esc(x.word) + '">删除</button></div>';
    }).join('');
  }
  function vbOpen() {
    stopAll();
    $('vbwrap').classList.remove('hidden');
    $('vbList').innerHTML = '<div class="vbe">读取中…</div>';
    fetch('/api/vocab/list').then(function (r) { return r.json(); }).then(vbRender)
      .catch(function () { $('vbList').innerHTML = '<div class="vbe">读不出来，程序可能已经退出了。</div>'; });
  }

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
    setTimeout(function () { a.classList.remove('spot'); }, 6000);
  }

  function cut(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }
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
        items.push({ k: 'review', icon: '🔁', tag: '复习', t: '第 ' + c.no + ' 章 · ' + c.zh,
          s: (ago === null ? '' : ago <= 0 ? '今天看过，再过一遍' : ago + ' 天没回头了') +
             (r.sec ? '　·　当时读了 ' + window.tcfStats.mins(r.sec) : ''),
          b: '打开这一章', go: function () { planGo(ri); } });
      } else if (sp.k === 'new') {
        var ni = chIndexByKey(sp.key); if (ni < 0) return;
        var nc = DOC.chapters[ni];
        items.push({ k: 'new', icon: '📖', tag: '新课', t: '第 ' + nc.no + ' 章 · ' + nc.zh,
          s: cut(String(nc.intro || ''), 62), b: '开始读', go: function () { planGo(ni); } });
      } else if (sp.k === 'res') {
        var hit = null;
        allLinks().forEach(function (o) { if (!hit && o.x.url === sp.url) hit = o; });
        if (!hit) return;
        var x = hit.x;
        items.push({ k: 'res', icon: '🎧', tag: '听力', t: x.title,
          s: [x.platform, x.level, x.length].filter(Boolean).join(' · ') +
             (x.how ? '　·　' + cut(String(x.how).replace(/<[^>]+>/g, ''), 64) : ''),
          b: x.embed ? '去看（能站内播）' : '去看这一条',
          go: function () { planGo(hit.ci, function () { spotlight(x.url); }); } });
      } else if (sp.k === 'vocab' && sp.w) {
        var have = {};
        (vocab || []).forEach(function (v) { have[v.word] = v; });
        var picks = sp.w.map(function (w) { return have[w]; }).filter(Boolean);
        if (!picks.length) return;
        items.push({ k: 'vocab', icon: '🎴', tag: '生词', t: '背 ' + picks.length + ' 个自己存的词',
          s: picks.slice(0, 6).map(function (x) { return x.word; }).join('、') + (picks.length > 6 ? ' …' : ''),
          b: '开始背', go: function () { $('dpwrap').classList.add('hidden'); fcFromVocab(picks); } });
      } else if (sp.k === 'vocab') {
        var ci = chIndexByKey(sp.cards); if (ci < 0) return;
        items.push({ k: 'vocab', icon: '🎴', tag: '词卡', t: '背第 ' + DOC.chapters[ci].no + ' 章的词卡',
          s: '生词本还不到 5 个词。看书时点任意法语单词，卡片右下角能存进去，攒起来以后就背自己的。',
          b: '打开背诵', go: function () { planGo(ci, fcOpen); } });
      } else if (sp.k === 'talk') {
        var tp = (DOC.topics || [])[sp.t]; if (!tp) return;
        var es = tp.entries || [];
        var three = (sp.e || []).map(function (i) { return es[i]; }).filter(Boolean);
        items.push({ k: 'talk', icon: '🗣', tag: '口语', t: 'Tâche 3 · ' + tp.zh + '，说满 90 秒',
          s: '录下来再回放。至少用上：' + three.map(function (x) { return x.phrase; }).join(' / '),
          b: '打开话题库', go: function () { planGo(chIndexByKey('__topics__')); } });
      }
    });
    return items;
  }

  function planRender() {
    // bank the minutes she is accumulating right now, or the panel reports the
    // last save instead of the truth
    if (window.tcfStats && window.tcfStats.bank) window.tcfStats.bank();
    var p = store.get('plan', {});
    if (p.day !== PLAN.day) p = { day: PLAN.day, done: {} };
    p.done = p.done || {};
    var s = window.tcfStats;
    var sec = s && s.dayStat ? s.dayStat().sec : 0;
    var stk = s && s.streak ? s.streak() : 0;
    var nDone = PLAN.items.filter(function (it) { return p.done[it.k]; }).length;

    var h = ['<div class="dpsum">' +
      '<div class="dpring' + (nDone >= PLAN.items.length ? ' full' : '') + '">' + nDone + '<i>/' + PLAN.items.length + '</i></div>' +
      '<div class="dpst"><b>' + (nDone >= PLAN.items.length ? '今天的都做完了 🎉' : '今天还剩 ' + (PLAN.items.length - nDone) + ' 件') + '</b>' +
      '<span>' + (sec < 30 ? '今天还没开始' : '今天已学 ' + s.mins(sec)) +
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

  /* The dot has to appear without building the whole plan first, and it has to be able
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
    // tapping 📅 before the book finished downloading used to throw on a null DOC and
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
        /* If an entry can no longer be built — she deleted the words it named, or a
           resource moved — the slot disappears from the list but its key would stay in
           the spec, and planPeek would nag about a task she can never tick. Prune. */
        if (PLAN.items.length !== p.spec.length) {
          var live = {};
          PLAN.items.forEach(function (it) { live[it.k] = 1; });
          p.spec = p.spec.filter(function (sp) { return live[sp.k]; });
          store.set('plan', p);
        }
        planRender();
      })
      .catch(function () {
        $('dpBody').innerHTML = '<div class="vbe">计划没能排出来，关掉重新点一次试试。</div>';
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
      p.done = p.done || {};
      p.done[t.dataset.tick] = p.done[t.dataset.tick] ? 0 : 1;
      store.set('plan', p);
      planRender();
      return;
    }
  });


  /* ---------------- 句子笔记本 ----------------
     生词本收的是词，这里收的是整句：划选任意一段法语，下面冒出「📓 存进笔记本」。
     存下来的句子带着出处和录音，随时能重听、能跳回原文。全部只存在这台设备上。 */
  var NOTES = store.get('notes', []);
  if (!Array.isArray(NOTES)) NOTES = [];
  function notesSave() { store.set('notes', NOTES.slice(-500)); }
  function notesDot() {
    // a class on the button, not a child node: the ⋯ menu relabels it with textContent
    var b = $('btnNotes');
    if (b) b.classList.toggle('dotted', !!NOTES.length);
  }

  // what she selected, plus where it came from
  function selInfo() {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    var txt = sel.toString().replace(/\s+/g, ' ').trim();
    if (txt.length < 4 || txt.length > 400) return null;
    var node = sel.anchorNode;
    var el = node && (node.nodeType === 1 ? node : node.parentElement);
    if (!el || !el.closest || !el.closest('#wrap')) return null;
    var host = el.closest('[data-play],[data-aid]');
    var aid = host ? (host.getAttribute('data-play') || host.getAttribute('data-aid')) : '';
    /* Where the Chinese lives depends on how the block was rendered: beside the French
       in a card, in the neighbouring cell of a table, or as the next sibling. Search
       the same three places the indexer does rather than guess one. */
    var zh = '';
    var td = el.closest('td');
    if (td) {
      var sibTd = td.nextElementSibling || td.previousElementSibling;
      if (sibTd) zh = sibTd.textContent.trim();
    }
    if (!zh) {
      var card = el.closest('.b-card,.dl,.pcard,.dtx,.b-model');
      var z = card && card.querySelector('.cz,.dzh,.exzh,.zh,.mzh,.dz');
      if (!z) {
        var sib = (card || el).nextElementSibling;
        if (sib && /(^|\s)(cz|dzh|exzh|zh|mzh|dz)(\s|$)/.test(sib.className || '')) z = sib;
      }
      if (z) zh = z.textContent.trim();
    }
    zh = zh.replace(/\s+/g, ' ').slice(0, 160);
    // the neighbouring cell is only a translation if it is actually Chinese;
    // otherwise it is the next French example and labelling it 译文 would be a lie
    if (zh === txt || !/[一-鿿]/.test(zh)) zh = '';
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
    if (top + h > window.innerHeight - 70) top = info.rect.top - h - 10;
    // a selection can sit anywhere, but the pill has to stay somewhere she can reach it
    top = Math.min(Math.max(8, top), window.innerHeight - h - 12);
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
      return x.t + (x.zh ? '\n  ' + x.zh : '') + '\n  —— 第 ' + x.no + ' 章 ' + (x.ch || '');
    }).join('\n\n');
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

  /* ---------------- study log ----------------
     Everything below reads from localStorage only; nothing is uploaded. She sees
     her own numbers, and can copy a summary to send if she wants to. */
  function stRender() {
    if (!window.tcfStats) { $('stBody').innerHTML = '<div class="vbe">记录功能没加载</div>'; return; }
    var s = window.tcfStats.summary(), M = window.tcfStats.mins, T = window.tcfStats.stamp;
    var todayKey = new Date().toISOString().slice(0, 10);
    var h = [];
    h.push('<div class="stcards">' +
      '<div class="stc"><b>' + M(s.total) + '</b><span>累计学习</span></div>' +
      '<div class="stc"><b>' + s.activeDays + ' 天</b><span>有效学习日</span></div>' +
      '<div class="stc"><b>' + s.audio + '</b><span>播放发音</span></div>' +
      '<div class="stc"><b>' + s.words.length + '</b><span>查过的词</span></div></div>');
    if (s.last) h.push('<div class="stnote">最近一次：' + T(s.last) + '</div>');

    h.push('<div class="stsec">看得最多的章节</div>');
    if (!s.chapters.length) h.push('<div class="vbe">还没有记录</div>');
    else h.push('<div class="stlist">' + s.chapters.slice(0, 10).map(function (c) {
      var w = Math.max(3, Math.round(c.sec / s.chapters[0].sec * 100));
      return '<div class="stbar"><div class="stbt">第' + c.no + '章 ' + esc(c.zh) + '</div>' +
             '<div class="stbg"><i style="width:' + w + '%"></i></div>' +
             '<div class="stbv">' + M(c.sec) + ' · ' + c.opens + ' 次</div></div>';
    }).join('') + '</div>');

    h.push('<div class="stsec">打开过的视频 / 资源</div>');
    if (!s.links.length) h.push('<div class="vbe">还没点开过第 30 章里的资源</div>');
    else h.push('<div class="stlist">' + s.links.slice(0, 20).map(function (x) {
      return '<div class="stlink"><span class="stts">' + T(x.t) + '</span>' +
             '<a href="' + esc(x.url) + '" target="_blank" rel="noopener noreferrer">' + esc(x.title) + '</a></div>';
    }).join('') + '</div>');

    h.push('<div class="stsec">查得最多的词</div>');
    h.push('<div class="stwords">' + (s.words.slice(0, 30).map(function (x) {
      return '<span class="stw">' + esc(x.w) + '<i>' + x.n + '</i></span>';
    }).join('') || '<div class="vbe">还没查过词</div>') + '</div>');

    h.push('<div class="stsec">最近做了什么</div>');
    h.push('<div class="stlist">' + (s.recent.slice(0, 25).map(function (r) {
      return '<div class="strec"><span class="stts">' + T(r.t) + '</span>' +
             '<span class="stk">' + esc(r.k) + '</span>' + esc(r.x) + '</div>';
    }).join('') || '<div class="vbe">—</div>') + '</div>');

    h.push('<div class="stfoot">这些记录只存在这台设备的浏览器里，<b>不会自动发给任何人</b>。' +
           '想让 Lionel 看到进度，点右上角「复制摘要」再粘贴给他。</div>');
    $('stBody').innerHTML = h.join('');
  }
  $('btnStats').onclick = function () { stRender(); $('stwrap').classList.remove('hidden'); };
  $('stClose').onclick = function () { $('stwrap').classList.add('hidden'); };
  $('stCopy').onclick = function () {
    var txt = window.tcfStats ? window.tcfStats.asText() : '';
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(function () { toast('已复制，粘贴到微信发给 Lionel 就行'); })
        .catch(function () { stFallback(txt); });
    } else stFallback(txt);
  };
  function stFallback(txt) {
    // clipboard API needs a secure context and permission; a selectable box always works
    $('stBody').innerHTML = '<div class="stnote">长按下面的文字全选复制：</div>' +
      '<textarea class="stta" readonly>' + esc(txt) + '</textarea>';
    var ta = document.querySelector('.stta');
    ta.focus(); ta.select();
  }

  $('btnVocab').onclick = vbOpen;
  /* on a phone the search box lives inside the drawer, so it took two steps to find */
  $('btnSearch').onclick = function () { drawer(true); setTimeout(function () { $('q').focus(); }, 60); };
  /* The ⋯ menu was laid out at the right coordinates and painted nowhere: .topbar
     scrolls sideways (overflow:auto), which clips its descendants, and position:fixed
     does not escape that either because .topbar's own backdrop-filter makes it the
     containing block for fixed children. Hit-testing each item returned .chead — all
     four of 生词本 / 笔记本 / 学习记录 / 夜间模式 were unreachable on every phone.
     Move it out of the toolbar entirely and place it by hand. */
  document.body.appendChild($('moreMenu'));
  $('btnMore').onclick = function (e) {
    e.stopPropagation();
    var m = $('moreMenu');
    var r = this.getBoundingClientRect();
    m.style.top = Math.round(r.bottom + 8) + 'px';
    m.style.right = Math.round(window.innerWidth - r.right) + 'px';
    m.classList.toggle('hidden');
  };
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.morewrap') && !e.target.closest('#moreMenu')) $('moreMenu').classList.add('hidden');
  });

  /* first run: she opens the app with no idea that anything is tappable */
  if (!store.get('seen', false)) {
    $('welcome').classList.remove('hidden');
    $('wcGo').onclick = function () {
      $('welcome').classList.add('hidden');
      store.set('seen', true);
    };
  }
  $('vbClose').onclick = function () { $('vbwrap').classList.add('hidden'); };
  $('vbList').addEventListener('click', function (e) {
    if (e.target.closest('#vbDrill')) { fcFromVocab(VOCAB.slice().reverse()); return; }
    if (e.target.closest('#vbShuffle')) {
      var a = VOCAB.slice();
      for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
      fcFromVocab(a);
      return;
    }
    var s = e.target.closest('.vbs');
    if (s) { if (window.tcfLookup) window.tcfLookup.play(s.dataset.w); return; }
    var d = e.target.closest('.vbd');
    if (d) {
      fetch('/api/vocab/remove', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word: d.dataset.del }) })
        .then(function () { return fetch('/api/vocab/list'); })
        .then(function (r) { return r.json(); }).then(vbRender);
    }
  });

  $('btnPlayAll').onclick = function () { startQueue(currentClips(), 0); };
  $('btnCards').onclick = fcOpen;
  $('fcClose').onclick = fcClose;
  $('fcReveal').onclick = fcReveal;
  $('fcKnow').onclick = function () { fcNext(true); };
  $('fcAgain').onclick = function () { fcNext(false); };
  $('fcBack').onclick = fcBack;
  $('fcSpeak').onclick = function () {
    var it = FC.list[FC.i];
    if (!it) return;
    if (it.aid) play(it.aid, it.fr);
    else if (window.tcfLookup) window.tcfLookup.play(it.fr);   // saved words live in the word pack
  };
  $('pPlay').onclick = function () {
    // a tapped word plays from lookup.js's own element; starting a whole-chapter
    // read-aloud on top of it is never what she meant by pressing ▶
    if (au.paused && window.tcfLookup && window.tcfLookup.busy && window.tcfLookup.busy()) {
      window.tcfLookup.stop();
      $('pNow').textContent = '已停下';
      return;
    }
    if (au.paused) { if (ARMED && au.src) { au.play(); this.textContent = '⏸'; } else startQueue(currentClips(), 0); }
    else { au.pause(); this.textContent = '▶'; }
  };
  $('pStop').onclick = function () { stopAll(); };
  /* Playing one sentence drops the queue, so ⏭ and ⏮ were inert after the single
     most-used control in the app. Rebuild the chapter's list around whatever is
     playing and step from there. */
  function stepTo(d) {
    if (QI < 0 || !QUEUE.length) {
      var list = currentClips(), cur = (au.src || '').split('/').pop().replace(/\.[a-z0-9]+$/, '');
      var at = -1;
      for (var i = 0; i < list.length; i++) if (list[i].aid === cur) { at = i; break; }
      if (at < 0) { if (!list.length) { toast('本章没有可朗读的法语'); return; } startQueue(list, 0); return; }
      QUEUE = list; QI = at;
    }
    var n = QI + d;
    if (n < 0) { toast('已经是第一句'); return; }
    if (n > QUEUE.length - 1) { toast('已经是最后一句'); return; }
    QI = n; playQueueItem();
  }
  $('pNext').onclick = function () { stepTo(1); };
  $('pPrev').onclick = function () { stepTo(-1); };
  $('btnRepeat').onclick = function () { REPEAT = !REPEAT; this.classList.toggle('on', REPEAT); toast(REPEAT ? '复读开：每句念两遍' : '复读关'); };
  $('segSpeed').addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    RATE = parseFloat(b.dataset.r); au.playbackRate = RATE;
    this.querySelectorAll('button').forEach(function (x) { x.classList.toggle('on', x === b); });
    store.set('rate', RATE);
  });
  $('btnDark').onclick = function () {
    document.body.classList.toggle('dark');
    store.set('dark', document.body.classList.contains('dark'));
  };
  /* ---------------- phone drawer ---------------- */
  var scrim = document.createElement('div');
  scrim.id = 'scrim';
  document.body.appendChild(scrim);
  function drawer(open) {
    $('side').classList.toggle('open', open);
    document.body.classList.toggle('drawer', open);
  }
  $('btnMenu').onclick = function () { drawer(!$('side').classList.contains('open')); };
  scrim.onclick = function () { drawer(false); };   // tapping the page used to leave it open
  $('btnQuit').onclick = function () {
    if (!confirm('要退出程序吗？\n\n退出后这个网页就不能用了，下次学习请重新双击 TCF法语学习助手.exe。')) return;
    au.pause();
    fetch('/api/quit', { method: 'POST' }).catch(function () {});
    setTimeout(function () {
      document.body.innerHTML = '<div style="display:flex;height:100vh;align-items:center;justify-content:center;' +
        'flex-direction:column;gap:14px;font-family:\'Segoe UI\',\'Microsoft YaHei\',sans-serif;color:#5b6474">' +
        '<div style="font-size:40px">👋</div><div style="font-size:19px;color:#18202e">程序已退出</div>' +
        '<div>可以关掉这个网页了。下次学习请重新双击 <b>TCF法语学习助手.exe</b></div>' +
        '<div style="font-size:13px">Bonne chance !</div></div>';
    }, 400);
  };
  // on a phone the drawer covers the results; Enter gets it out of the way
  $('q').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { this.blur(); drawer(false); }
  });
  $('q').addEventListener('input', function () { clearTimeout(qt); var v = this.value; qt = setTimeout(function () { if ($('q').value === v) search(v); }, 220); });

  document.addEventListener('keydown', function (e) {
    if (!$('fcwrap').classList.contains('hidden')) {
      if (e.key === ' ') { e.preventDefault(); FC.shown ? fcNext(true) : fcReveal(); }
      else if (e.key === 'ArrowRight') fcNext(true);
      else if (e.key === 'ArrowLeft') fcNext(false);
      else if (e.key === 'Escape') fcClose();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); $('q').focus(); }
    if (e.target.tagName === 'INPUT') return;
    if (e.key === ' ') { e.preventDefault(); $('pPlay').click(); }
  });

  /* ---------------- phone layout ----------------
     The toolbar wrapped to three rows on a 375px screen. Speed and repeat are
     playback controls, so on narrow screens they move into the player bar. */
  function placeControls() {
    var narrow = window.innerWidth <= 860;
    var seg = $('segSpeed'), rep = $('btnRepeat');
    var host = narrow ? $('player') : document.querySelector('.topbar');
    if (seg.parentNode !== host) {
      if (narrow) { host.appendChild(seg); host.appendChild(rep); }
      else {
        var anchor = document.querySelector('.topbar .spacer');
        host.insertBefore(seg, anchor);
        host.insertBefore(rep, anchor);
      }
    }
    /* the toolbar wanted 476px on a 360px screen, pushing 📊 and 🌙 off the edge;
       the secondary actions move into a ⋯ menu instead of being unreachable */
    var menu = $('moreMenu'), bar = document.querySelector('.topbar');
    var secondary = [$('btnVocab'), $('btnNotes'), $('btnStats'), $('btnDark')];
    var LABEL = { btnStats: '📊 学习记录', btnDark: '🌙 夜间模式', btnVocab: '📒 生词本',
                  btnNotes: '📓 笔记本' };
    if (narrow) {
      secondary.forEach(function (b) {
        if (!b || b.parentNode === menu) return;
        // a bare 📊 in a dropdown means nothing; spell it out once it leaves the toolbar
        if (!b.dataset.icon) b.dataset.icon = b.textContent.trim();
        b.textContent = LABEL[b.id] || b.dataset.icon;
        menu.appendChild(b);
      });
    } else if (secondary[0] && secondary[0].parentNode === menu) {
      secondary.forEach(function (b) { if (b && b.dataset.icon) b.textContent = b.dataset.icon; });
      var sp = document.querySelector('.topbar .spacer');
      bar.insertBefore(secondary[0], sp);
      bar.insertBefore(secondary[1], sp);
      bar.appendChild(secondary[2]);
    }
    if (!narrow) menu.classList.add('hidden');
  }
  placeControls();
  var rz;
  window.addEventListener('resize', function () { clearTimeout(rz); rz = setTimeout(placeControls, 150); });

  /* a table wider than its box gives no hint that it scrolls sideways */
  function markScrollables() {
    document.querySelectorAll('.tabwrap').forEach(function (w) {
      w.classList.toggle('scrolls', w.scrollWidth > w.clientWidth + 4);
    });
  }
  window.__markScrollables = markScrollables;

  /* ---------------- boot ---------------- */
  fetch('/api/content').then(function (r) { return r.json(); }).then(function (d) {
    DOC = d;
    var h = [], lastPart = null;
    d.chapters.forEach(function (c, i) {
      if (c.part !== lastPart) {
        lastPart = c.part;
        h.push('<div class="navpart">第 ' + c.part + ' 部分 · ' + esc(c.partzh) + '</div>');
      }
      h.push('<div class="navitem" data-i="' + i + '"><span class="n">' + c.no + '</span><span class="t">' + esc(c.zh) + '</span></div>');
    });
    $('nav').innerHTML = h.join('');
    /* the welcome screen used to hard-code how many resources there were, and said 91
       long after there were 168; count them instead so it cannot drift again */
    var wr = $('wcRes');
    if (wr) {
      var nres = 0, nemb = 0;
      d.chapters.forEach(function (c) {
        (c.blocks || []).forEach(function (b) {
          (b.links || []).forEach(function (x) { nres++; if (x.embed) nemb++; });
        });
      });
      if (nres) wr.textContent = nres + ' 条里 ' + nemb + ' 条能直接在站内播，每一条';
    }
    notesDot();
    if (store.get('dark', false)) document.body.classList.add('dark');
    RATE = store.get('rate', 1);
    document.querySelectorAll('#segSpeed button').forEach(function (b) { b.classList.toggle('on', parseFloat(b.dataset.r) === RATE); });
    var last = Math.min(store.get('last', 0), d.chapters.length - 1);
    renderChapter(last, true);
    markVisited();
    if (last > 0) toast('接着上次：第 ' + d.chapters[last].no + ' 章');
    var sec0 = window.tcfStats && window.tcfStats.dayStat ? window.tcfStats.dayStat().sec : 1;
    if (!$('welcome') || $('welcome').classList.contains('hidden')) {
      if (sec0 < 30 && store.get('planShown', '') !== dayKey()) {
        store.set('planShown', dayKey());
        setTimeout(planOpen, 700);
      } else { PLAN.day = dayKey(); planPeek(); }
    }
  }).catch(function () {
    $('wrap').innerHTML = '<div class="loadfail"><div class="lf-i">📡</div>' +
      '<div class="lf-t">课文没能载入</div>' +
      '<div class="lf-s">多半是网络断了。连上网之后点下面重试；<br>如果之前完整打开过一次，离线也应该能进。</div>' +
      '<button class="btn pri" id="lfGo">重新载入</button></div>';
    $('lfGo').onclick = function () { location.reload(); };
  });
})();
