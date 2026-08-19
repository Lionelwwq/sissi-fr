/* 点词查询 —— 页面上任何一个法语词都能点：发音 + 词条 + 变位还原
   Earlier this only bound to sentences that had audio, so the French sitting inside
   paragraphs, tips and warning boxes — most of the book — was dead to the touch. */
(function () {
  'use strict';
  if (window.__tcfLookup) return;
  window.__tcfLookup = true;

  var DICT = null, WORDS = null, CONJ = null, loading = null;
  var au = new Audio();
  var pop = null;

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
    ]).then(function (a) { DICT = a[0]; WORDS = a[1]; CONJ = a[2] || {}; });
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
    au.pause();
    au.src = window.CLIP(id);
    au.playbackRate = 1;
    au.play().catch(function () {});
  }

  // several words selected: play them one after another, not the whole sentence again
  function playSequence(words) {
    var ids = words.map(function (w) { return WORDS && WORDS[keyOf(w)]; }).filter(Boolean);
    if (!ids.length) { flash('这几个词没有录音'); return; }
    var i = 0;
    (function step() {
      if (i >= ids.length) return;
      au.src = window.CLIP(ids[i++]);
      au.onended = function () { setTimeout(step, 160); };
      au.play().catch(function () {});
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

  function lookup(word, x, y, extra) {
    load().then(function () {
      playWord(word);                    // sound first: that is what she clicked for
      card(DICT[keyOf(word)], word, x, y, extra);
    });
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
  var DEAD = 'button, a, input, textarea, select, .spk, .wp-head, .wp-foot';

  document.addEventListener('click', function (e) {
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
        });
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
    });
    e.preventDefault(); e.stopPropagation();
  }, true);

  window.tcfLookup = { lookup: lookup, play: playWord };
})();
