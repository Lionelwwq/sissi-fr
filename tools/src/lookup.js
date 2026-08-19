/* 点词查询 —— 页面上任何一个法语词都能点：发音 + 词条 + 变位还原
   Earlier this only bound to sentences that had audio, so the French sitting inside
   paragraphs, tips and warning boxes — most of the book — was dead to the touch. */
(function () {
  'use strict';
  if (window.__tcfLookup) return;
  window.__tcfLookup = true;

  var DICT = null, WORDS = null, CONJ = null, loading = null;
  var au = new Audio();
  au.preload = 'auto';
  var pop = null;
  /* Two scripts each held their own audio element and neither knew about the other,
     so a tapped word played on top of the chapter being read aloud and the player's
     stop button could not reach it. A sequence also kept its onended handler after
     being interrupted, and quietly resumed once the interrupting clip finished. */
  var SEQ = 0;
  function takeAudio() {
    SEQ++;
    au.onended = null; au.onerror = null;
    try { au.pause(); } catch (e) {}
    if (window.tcfAudio) window.tcfAudio.stop();
  }

  /* iOS only "unlocks" an audio element if its first play() runs inside the
     synchronous part of a real gesture. Word lookup plays *after* awaiting the
     dictionary fetch, so the gesture has long expired and the element can stay
     locked forever — the card appears and nothing is ever heard. Unlock it up
     front with a silent clip, on the very first touch anywhere. */
  var SILENT = 'data:audio/mpeg;base64,SUQzBAAAAAABEVRYWFgAAAAtAAADY29tbWVudABCaWdTb3VuZEJhbmsuY29tIC8gTGFTb25vdGhlcXVlLm9yZwBURU5DAAAAHQAAA1N3aXRjaCBQbHVzIMKpIE5DSCBTb2Z0d2FyZQBUSVQyAAAABgAAAzIyMzUAVFNTRQAAAA8AAANMYXZmNTcuODMuMTAwAAAAAAAAAAAAAAD/80DEAAAAA0gAAAAATEFNRTMuMTAwVVVVVVVVVVVVVUxBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV/zMsQTAAAAAAAAAAAAAAAA//8AAAAAAAAAAAAAAAAAAAAA';
  var unlocked = false;
  function unlock() {
    if (unlocked) return;
    unlocked = true;
    try {
      var keep = au.src;
      au.src = SILENT;
      var r = au.play();
      if (r && r.then) r.then(function () { au.pause(); au.currentTime = 0; if (keep) au.src = keep; })
                        .catch(function () {});
    } catch (e) {}
  }
  document.addEventListener('touchstart', unlock, true);   // a long press plays before touchend ever fires
  document.addEventListener('touchend', unlock, true);
  document.addEventListener('mousedown', unlock, true);

  // the speed she picked applies to sentences; words used to ignore it
  function rate() {
    try { var v = JSON.parse(localStorage.getItem('tcf_rate')); return v > 0 ? v : 1; }
    catch (e) { return 1; }
  }

  // clitics are written joined but looked up separately: l'école -> école
  var ELIDE = /^(l|d|j|n|s|c|m|t|qu)['’](.+)$/i;
  var WORDRE = /[A-Za-zÀ-ÿ]+(?:['’][A-Za-zÀ-ÿ]+)*/;

  function load() {
    if (DICT) return Promise.resolve();
    if (loading) return loading;
    loading = Promise.all([
      fetch('/api/dict').then(function (r) { return r.json(); }),
      fetch('/api/dict/audio-index').then(function (r) { return r.json(); }),
      fetch('/api/conj').then(function (r) { return r.json(); }).catch(function () { return {}; })
    ]).then(function (a) { DICT = a[0]; WORDS = a[1]; CONJ = a[2] || {}; },
            function (e) { loading = null; throw e; });
    return loading;
  }

  function keyOf(w) {
    var m = ELIDE.exec(w);
    return (m ? m[2] : w).toLowerCase().replace(/['’]$/, '');
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  // entries occasionally arrive with markdown emphasis and their own warning icon;
  // rendered raw they show literal asterisks and a doubled ⚠️
  function note(s) {
    return esc(String(s || '').replace(/^[\s⚠️！!]*/, ''))
      .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
      .replace(/\*(.+?)\*/g, '<i>$1</i>');
  }

  function playWord(w) {
    var id = WORDS && WORDS[keyOf(w)];
    if (!id) { flash('这个词没有单独录音'); return; }
    takeAudio();
    au.src = '/word/' + id;
    au.playbackRate = rate();
    // a silent catch here meant tapping a hundred words gave no sound and no reason
    au.play().catch(function (e) {
      if (e && e.name === 'AbortError') return;
      flash('这个词没能播放（浏览器可能不支持该音频格式）');
    });
  }

  // several words selected: play them one after another, not the whole sentence again
  function playSequence(words) {
    var ids = words.map(function (w) { return WORDS && WORDS[keyOf(w)]; }).filter(Boolean);
    if (!ids.length) { flash('这几个词没有录音'); return; }
    takeAudio();
    var mine = SEQ, i = 0;
    (function step() {
      if (mine !== SEQ || i >= ids.length) return;
      au.src = '/word/' + ids[i++];
      au.playbackRate = rate();
      au.onended = function () { setTimeout(step, 160); };
      au.onerror = function () { setTimeout(step, 160); };   // one bad clip must not stall the rest
      au.play().catch(function (e) { if (!e || e.name !== 'AbortError') setTimeout(step, 160); });
    })();
  }

  function flash(msg) {
    var t = document.getElementById('toast');
    if (!t) { return; }
    t.textContent = msg; t.classList.add('on');
    clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove('on'); }, 1600);
  }

  function close() { if (pop) { pop.remove(); pop = null; } }
  document.addEventListener('click', function (e) {
    if (pop && !pop.contains(e.target)) close();
  }, true);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

  /* « serions » on its own tells a learner nothing; naming the verb and the tense
     is the step they cannot take by themselves. */
  function conjHtml(word) {
    var hits = CONJ && CONJ[keyOf(word)];
    if (!hits || !hits.length) return '';
    return '<div class="wp-conj">' + hits.map(function (h) {
      var who = (h.p && h.p.length) ? '　·　' + esc(h.p.join(' / ')) : '';
      var role = h.role === 'participe' ? '过去分词' : (h.role === 'infinitif' ? '原形' : '');
      return '<div class="wp-cj">🔁 <b>' + esc(h.v) + '</b>　' + esc(h.t) + who +
             (role ? '　<span class="wp-role">' + role + '</span>' : '') +
             '<span class="wp-cex" data-say="' + esc(h.ex) + '">' + esc(h.ex) + '</span></div>';
    }).join('') + '</div>';
  }

  function card(entry, word, x, y, extra) {
    close();
    pop = document.createElement('div');
    pop.className = 'wpop';
    var cj = conjHtml(word);
    var h = [];
    h.push('<div class="wp-head">' +
      '<button class="wp-say" title="发音">🔊</button>' +
      '<b class="wp-w">' + esc(entry ? entry.w : word) + '</b>' +
      (entry && entry.p ? '<span class="wp-pos">' + esc(entry.p) + '</span>' : '') +
      (entry && entry.lv ? '<span class="wp-lv">' + esc(entry.lv) + '</span>' : '') +
      '<span class="wp-x">✕</span></div>');

    if (cj) h.push(cj);

    if (!entry) {
      h.push('<div class="wp-none">' + (cj
        ? '这是一个变位形式，词典正文里没有单独收录。'
        : '词典里还没有这个词（只收录了最高频的 3000 个）。发音仍然可以听。') + '</div>');
    } else {
      if (entry.l && entry.l.toLowerCase() !== entry.w.toLowerCase()) {
        h.push('<div class="wp-lemma">原形 <b>' + esc(entry.l) + '</b>' +
               (entry.f ? ' · ' + esc(entry.f) : '') + '</div>');
      } else if (entry.f) {
        h.push('<div class="wp-lemma">' + esc(entry.f) + '</div>');
      }
      h.push('<div class="wp-zh">' + entry.zh.map(esc).join('；') + '</div>');
      if (entry.c && entry.c.length) {
        h.push('<div class="wp-sec">常用搭配</div>' + entry.c.map(function (c) {
          return '<div class="wp-c"><span class="cf" data-say="' + esc(c[0]) + '">' + esc(c[0]) + '</span>' +
                 '<span class="cz">' + esc(c[1]) + '</span></div>';
        }).join(''));
      }
      if (entry.n) h.push('<div class="wp-note">⚠️ ' + note(entry.n) + '</div>');
      if (entry.ex) h.push('<div class="wp-ex">你在材料里见过：<i>' + esc(entry.ex) + '</i></div>');
    }
    if (extra) h.push(extra);
    h.push('<div class="wp-foot"><button class="wp-add">＋ 加入生词本</button></div>');
    pop.innerHTML = h.join('');
    document.body.appendChild(pop);

    // keep the card on screen
    var r = pop.getBoundingClientRect();
    var left = Math.min(Math.max(8, x - r.width / 2), window.innerWidth - r.width - 8);
    var top = y + 14;
    if (top + r.height > window.innerHeight - 8) top = Math.max(8, y - r.height - 16);
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';

    pop.querySelector('.wp-say').onclick = function (ev) { ev.stopPropagation(); playWord(word); };
    pop.querySelector('.wp-x').onclick = close;
    pop.querySelectorAll('[data-say]').forEach(function (el) {
      el.onclick = function (ev) {
        ev.stopPropagation();
        playSequence((el.dataset.say.match(/[A-Za-zÀ-ÿ']+/g) || []));
      };
    });
    pop.querySelector('.wp-add').onclick = function (ev) {
      ev.stopPropagation();
      fetch('/api/vocab/add', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word: word, lemma: entry ? entry.l : word,
                               gloss: entry ? entry.zh.join('；') : '',
                               sentence: entry ? entry.ex : '' })
      }).then(function () { flash('已加入生词本'); close(); }).catch(function () {});
    };
  }

  function dictFail() { flash('词典还没下载好，连上网再点一次'); }
  function lookup(word, x, y, extra) {
    load().then(function () {
      playWord(word);                    // sound first: that is what she clicked for
      if (window.tcfStats) window.tcfStats.word(word);
      card(DICT[keyOf(word)], word, x, y, extra);
    }).catch(dictFail);
  }

  /* --- turn a click inside French text into a word --- */
  function wordAtPoint(node, offset) {
    var t = node.nodeValue || '';
    var i = offset, j = offset;
    var ok = function (c) { return c && /[A-Za-zÀ-ÿ'’]/.test(c); };
    while (i > 0 && ok(t[i - 1])) i--;
    while (j < t.length && ok(t[j])) j++;
    var w = t.slice(i, j);
    var m = WORDRE.exec(w);
    return m ? m[0] : null;
  }

  /* Anywhere inside the reading pane counts. A click on Chinese simply finds no
     Latin word and falls through, so there is no need to whitelist French islands. */
  var ZONES = '#wrap, .fc, .wpop, .promptbox, .cbox, .b-model, .reccard';
  var DEAD = 'button, a, input, textarea, select, .spk, .wp-head, .wp-foot, [data-say]';

  /* Tapping a word looks it up and stops there, so whole-sentence playback was
     reachable only through the small 🔊. A long press now plays the sentence —
     the gesture the 4px gaps between words used to be doing by accident. */
  var LP = { timer: null, x: 0, y: 0, at: 0 };
  function sentenceUnder(el) {
    var n = el && el.closest ? el.closest('[data-play],[data-aid]') : null;
    return n ? (n.getAttribute('data-play') || n.getAttribute('data-aid')) : null;
  }
  function lpStart(e) {
    var pt = e.touches ? e.touches[0] : e;
    LP.at = 0;                       // every new gesture starts clean
    var host = e.target.closest && e.target.closest(ZONES);
    if (!host || (e.target.closest && e.target.closest(DEAD))) return;
    var aid = sentenceUnder(e.target);
    if (!aid) return;
    LP.x = pt.clientX; LP.y = pt.clientY;
    clearTimeout(LP.timer);
    LP.timer = setTimeout(function () {
      LP.at = Date.now();
      close();
      takeAudio();
      au.src = '/audio/' + aid;
      au.playbackRate = rate();
      au.play().catch(function () {});
      flash('▶ 播放整句');
      if (navigator.vibrate) { try { navigator.vibrate(15); } catch (err) {} }
    }, 480);
  }
  function lpMove(e) {
    var pt = e.touches ? e.touches[0] : e;
    if (!LP.timer) return;
    if (Math.abs(pt.clientX - LP.x) > 12 || Math.abs(pt.clientY - LP.y) > 12) {
      clearTimeout(LP.timer); LP.timer = null;
    }
  }
  function lpEnd() { clearTimeout(LP.timer); LP.timer = null; }
  document.addEventListener('touchstart', lpStart, { passive: true });
  document.addEventListener('touchmove', lpMove, { passive: true });
  document.addEventListener('touchend', lpEnd, true);
  document.addEventListener('mousedown', lpStart, true);
  document.addEventListener('mousemove', lpMove, true);
  document.addEventListener('mouseup', lpEnd, true);

  document.addEventListener('click', function (e) {
    // iOS does not reliably send a click after a long press; this window expires by itself
    if (Date.now() - LP.at < 700) { LP.at = 0; e.preventDefault(); e.stopPropagation(); return; }
    var host = e.target.closest(ZONES);
    if (!host) return;
    if (e.target.closest(DEAD)) return;

    var sel = window.getSelection();
    // a drag-selection of several words means "read these, in order"
    if (sel && !sel.isCollapsed && host.contains(sel.anchorNode)) {
      var text = sel.toString().trim();
      var words = text.match(/[A-Za-zÀ-ÿ]+(?:['’][A-Za-zÀ-ÿ]+)*/g) || [];
      if (words.length > 1 && words.length <= 8) {
        e.preventDefault(); e.stopPropagation();
        load().then(function () {
          playSequence(words);
          var known = words.map(function (w) { return DICT[keyOf(w)]; }).filter(Boolean);
          var list = '<div class="wp-sec">选中的 ' + words.length + ' 个词</div>' +
            words.map(function (w) {
              var d = DICT[keyOf(w)];
              return '<div class="wp-c"><span class="cf" data-say="' + esc(w) + '">' + esc(w) + '</span>' +
                     '<span class="cz">' + (d ? esc(d.zh[0]) : '—') + '</span></div>';
            }).join('');
          card(known[0] || null, words[0], e.clientX, e.clientY, list);
        }).catch(dictFail);
        return;
      }
    }

    var pos = document.caretRangeFromPoint ? document.caretRangeFromPoint(e.clientX, e.clientY) : null;
    if (!pos || pos.startContainer.nodeType !== 3) return;
    var w = wordAtPoint(pos.startContainer, pos.startOffset);
    if (!w || w.length < 2) return;
    // load first: without the dictionary we cannot tell a French word from a stray letter
    load().then(function () {
      if (!DICT[keyOf(w)] && !(CONJ && CONJ[keyOf(w)]) && !(WORDS && WORDS[keyOf(w)])) return;
      lookup(w, e.clientX, e.clientY);
    }).catch(dictFail);
    e.preventDefault(); e.stopPropagation();
  }, true);

  // pre-warm: otherwise her first tap waits on ~1.5 MB of dictionary
  setTimeout(function () { load().catch(function () {}); }, 1500);

  window.tcfLookup = { lookup: lookup, play: playWord, stop: function () {
    SEQ++; au.onended = null; au.onerror = null;
    try { au.pause(); au.currentTime = 0; } catch (e) {}
  } };
})();
