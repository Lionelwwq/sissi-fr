/* TCF 法语学习助手 · 王思专属版 */
(function () {
  'use strict';
  var DOC = null, CUR = 0, QUEUE = [], QI = -1, RATE = 1, REPEAT = false, REP2 = false;
  var PLAY_SEQ = 0, VIEW = 'chapter', HITS = [];
  var au = document.getElementById('au');
  /* 89% of the clips are Ogg/Opus. Safari only learned that container in 17.4, and
     a silent decode failure is indistinguishable from "the app is broken". */
  var CAN_OPUS = (function () {
    try { return !!document.createElement('audio').canPlayType('audio/ogg; codecs=opus'); }
    catch (e) { return true; }
  })();
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

  /* ---------------- utils ---------------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function rich(s) {
    var t = esc(s);
    ['b', 'i', 'u'].forEach(function (g) {
      t = t.split('&lt;' + g + '&gt;').join('<' + g + '>').split('&lt;/' + g + '&gt;').join('</' + g + '>');
    });
    return t.split('&lt;br&gt;').join('<br>').split('\n').join('<br>');
  }
  function toast(m) {
    var t = $('toast'); t.textContent = m; t.classList.add('on');
    clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('on'); }, 1800);
  }
  var store = {
    get: function (k, d) { try { return JSON.parse(localStorage.getItem('tcf_' + k)) ?? d; } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem('tcf_' + k, JSON.stringify(v)); } catch (e) {} }
  };

  /* ---------------- audio ---------------- */
  function clearHL() {
    document.querySelectorAll('.spk.playing').forEach(function (e) { e.classList.remove('playing'); });
    document.querySelectorAll('.mline.play,.dtx.play').forEach(function (e) { e.classList.remove('play'); });
  }
  function highlight(aid) {
    clearHL();
    // model sentences carry data-play, not data-aid — match both or they never light up
    var b = document.querySelector('[data-aid="' + aid + '"]') ||
            document.querySelector('[data-play="' + aid + '"]');
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
  function stopAll() {
    dropQueue();
    REP2 = false;
    try { au.pause(); au.currentTime = 0; } catch (e) {}
    clearHL();
    $('pPlay').textContent = '▶';
    $('pNow').textContent = '点任意法语句子即可发音';
  }

  function play(aid, label, fromQueue) {
    if (!aid) { toast('这一条没有音频'); return; }
    if (!fromQueue) dropQueue();
    REP2 = false;
    au.pause();
    au.src = window.CLIP(aid);
    au.playbackRate = RATE;
    var mine = ++PLAY_SEQ;
    au.play().catch(function (e) {
      // swapping src aborts the previous play(): that is normal, not a broken audio pack
      if (e && (e.name === 'AbortError' || mine !== PLAY_SEQ)) return;
      fetch('/api/ping').then(function () {
        toast(CAN_OPUS ? '这一条没能播放，换一句试试' : '这个浏览器不支持本站的音频格式');
      }).catch(function () { serverGone(); });
    });
    highlight(aid);
    $('pNow').textContent = label || '正在播放…';
    $('pPlay').textContent = '⏸';
  }
  au.addEventListener('error', function () {
    if (QI >= 0 && QI < QUEUE.length - 1) { QI++; playQueueItem(); return; }
    clearHL(); QI = -1;
    $('pPlay').textContent = '▶';
    $('pNow').textContent = CAN_OPUS ? '播放失败' : '浏览器不支持这种音频格式';
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
  function renderBlocks(bs, color) {
    var h = [];
    bs.forEach(function (b, bi) {
      var k = b.kind;
      if (k === 'h3') h.push('<h3 class="b-h3" style="border-color:' + color + '">' + esc(b.title) + '</h3>');
      else if (k === 'h4') h.push('<h4 class="b-h4">' + esc(b.title) + '</h4>');
      else if (k === 'para') h.push('<p class="b-para">' + rich(b.text) + '</p>');
      else if (k === 'bullets') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        h.push('<ul class="b-ul">' + (b.items || []).map(function (x) { return '<li>' + rich(x) + '</li>'; }).join('') + '</ul>');
      } else if (k === 'steps') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        h.push('<ol class="b-steps">' + (b.items || []).map(function (x, i) {
          return '<li><span class="stepn" style="background:' + color + '">' + (i + 1) + '</span><div>' + rich(x) + '</div></li>';
        }).join('') + '</ol>');
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
          }).join('') + '</tbody></table></div>');
      } else if (k === 'cards') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        (b.cards || []).forEach(function (c, ci) {
          var key = CUR + ':' + bi + ':' + ci;
          h.push('<div class="b-card" style="border-left-color:' + color + '" data-ck="' + key + '">' +
            '<div class="cf">' + spk(c.aid, c.fr) + '<span class="frtext" data-play="' + (c.aid || '') + '">' + rich(c.fr) + '</span></div>' +
            '<div class="cz">' + rich(c.zh) + '</div>' +
            (c.note ? '<div class="cn">💡 ' + rich(c.note) + '</div>' : '') + '</div>');
        });
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
          '</div>');
      } else if (k === 'dialogue') {
        if (b.title) h.push('<div class="b-lt">' + esc(b.title) + '</div>');
        h.push('<div class="b-dial"><div style="margin-bottom:8px"><button class="btn" data-playdial="' + bi + '">▶ 播放整段对话（双人配音）</button></div>' +
          (b.dialogue || []).map(function (d) {
            return '<div class="dl ' + (d.me ? 'cand' : 'exam') + '"><div class="dsp">' + esc(d.speaker) + '</div>' +
              '<div class="dtx"><div>' + spk(d.aid, d.fr) + '<span class="frtext" data-play="' + (d.aid || '') + '">' + rich(d.fr) + '</span></div>' +
              '<div class="dzh">' + rich(d.zh) + '</div></div></div>';
          }).join('') + '</div>');
      } else if (k === 'tip') {
        h.push('<div class="b-tip"><div class="bt">💡 ' + esc(b.title || '提示') + '</div>' + rich(b.text) + '</div>');
      } else if (k === 'warn') {
        h.push('<div class="b-warn"><div class="bt">⚠️ ' + esc(b.title || '易错警告') + '</div>' + rich(b.text) + '</div>');
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

  function renderChapter(i) {
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
    $('main').scrollTop = 0;
    if (window.__markScrollables) window.__markScrollables();
    document.querySelectorAll('.navitem').forEach(function (e) { e.classList.toggle('on', +e.dataset.i === i); });
    store.set('last', i);
  }

  /* ---------------- collect audio of current view ---------------- */
  function currentClips() {
    var out = [];
    document.querySelectorAll('[data-play]').forEach(function (e) {
      var a = e.getAttribute('data-play');
      if (a) out.push({ aid: a, text: e.textContent.trim() });
    });
    var seen = {}, uniq = [];
    out.forEach(function (x) { if (!seen[x.aid]) { seen[x.aid] = 1; uniq.push(x); } });
    return uniq;
  }

  /* ---------------- flashcards ---------------- */
  var FC = { list: [], i: 0, shown: false };
  function fcBuild() {
    if (VIEW === 'search') {          //背诵搜索结果，而不是上一次浏览的章节
      return HITS.filter(function (h) { return h.aid; })
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
  function fcShow() {
    var it = FC.list[FC.i];
    if (!it) { fcClose(); toast('本轮结束，做得好！'); return; }
    FC.shown = false;
    $('fcProg').textContent = '第 ' + (FC.i + 1) + ' / ' + FC.list.length + ' 张　·　' +
      (TOUCH ? '点「看答案」，再选会了 / 还不会' : '空格看答案，← 还不会，→ 会了');
    $('fcFr').textContent = it.fr;
    $('fcZh').textContent = '';
    $('fcEx').classList.add('hidden');
    if (it.aid) play(it.aid, it.fr.slice(0, 60));
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
    if (!FC.list.length) { toast(VIEW === 'search' ? '搜索结果里没有可背诵的词卡' : '本章没有可背诵的词卡'); return; }
    $('fcwrap').classList.remove('hidden'); fcShow();
  }
  function fcClose() { $('fcwrap').classList.add('hidden'); stopAll(); }

  /* ---------------- search ---------------- */
  function search(q) {
    q = q.trim().toLowerCase();
    if (q.length < 2) { if (VIEW === 'search') renderChapter(CUR); return; }
    stopAll();
    VIEW = 'search';
    var hits = [], seen = {};
    function push(ch, fr, zh, aid) {
      if (!fr) return;
      if ((fr + ' ' + (zh || '')).toLowerCase().indexOf(q) < 0) return;
      var k = (aid || '') + '|' + fr;
      if (seen[k]) return;
      seen[k] = 1;
      hits.push({ ch: ch, fr: fr, zh: zh || '', aid: aid });
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
      });
    });
    DOC.topics.forEach(function (t) {
      t.entries.forEach(function (e) {
        push({ zh: '话题库 · ' + t.zh, color: t.color }, e.phrase, e.zh, e.aid);
        push({ zh: '话题库 · ' + t.zh, color: t.color }, e.example_fr, e.example_zh, e.aid_ex);
      });
    });
    HITS = hits.slice(0, 300);
    var h = ['<div class="chead" style="background:linear-gradient(120deg,#334155,#334155bb)">' +
      '<div class="cno">搜索结果 · RECHERCHE</div><h1>「' + esc(q) + '」共 ' + hits.length + ' 条</h1></div>'];
    HITS.forEach(function (x) {
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
    if (b) { play(b.dataset.aid, b.dataset.t); return; }
    var p = t.closest('[data-play]');
    if (p && p.getAttribute('data-play')) { play(p.getAttribute('data-play'), p.textContent.trim().slice(0, 70)); return; }
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
  function vbRender(items) {
    $('vbN').textContent = items.length ? items.length + ' 个词' : '';
    if (!items.length) {
      $('vbList').innerHTML = '<div class="vbe">还是空的。<br>看书时点任意法语单词，弹出的卡片右下角有「＋ 加入生词本」。</div>';
      return;
    }
    $('vbList').innerHTML = items.slice().reverse().map(function (x) {
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
  $('btnVocab').onclick = vbOpen;
  $('vbClose').onclick = function () { $('vbwrap').classList.add('hidden'); };
  $('vbList').addEventListener('click', function (e) {
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
  $('fcSpeak').onclick = function () { var it = FC.list[FC.i]; if (it && it.aid) play(it.aid, it.fr); };
  $('pPlay').onclick = function () {
    if (au.paused) { if (au.src) { au.play(); this.textContent = '⏸'; } else startQueue(currentClips(), 0); }
    else { au.pause(); this.textContent = '▶'; }
  };
  $('pStop').onclick = function () { au.pause(); au.currentTime = 0; QI = -1; clearHL(); $('pPlay').textContent = '▶'; };
  $('pNext').onclick = function () { if (QI >= 0 && QI < QUEUE.length - 1) { QI++; playQueueItem(); } };
  $('pPrev').onclick = function () { if (QI > 0) { QI--; playQueueItem(); } };
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
    if (!CAN_OPUS) {
      document.body.classList.add('nosound');
      $('nosound').innerHTML = '🔇 <b>这个浏览器放不出本站的发音。</b><br>' +
        '绝大部分音频是 Opus 格式，Safari 要 <b>iOS 17.4 / macOS 14.4</b> 以上才支持。' +
        '请升级系统，或换 Chrome / Edge 打开，课文和词典不受影响。';
    }
    if (store.get('dark', false)) document.body.classList.add('dark');
    RATE = store.get('rate', 1);
    document.querySelectorAll('#segSpeed button').forEach(function (b) { b.classList.toggle('on', parseFloat(b.dataset.r) === RATE); });
    renderChapter(Math.min(store.get('last', 0), d.chapters.length - 1));
  });
})();
