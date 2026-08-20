# -*- coding: utf-8 -*-
"""Round-3 fixes to app.js, found by an eight-lens adversarial sweep plus hands-on
testing of the live site. Every replacement is asserted to occur exactly once, so a
future edit that moves the anchor fails loudly instead of silently patching nothing."""
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


patch("app.js", [

    # ---- 1. the only non-ES5 token in the codebase ---------------------------
    # `??` is a syntax error before Safari 13.1 / iOS 13.4, and a syntax error in
    # app.js is a blank page, not a degraded one. Everything else here is ES5 on
    # purpose — the audio was converted to mp3 for exactly the phone this excludes.
    ("    get: function (k, d) { try { return JSON.parse(localStorage.getItem('tcf_' + k)) ?? d; } catch (e) { return d; } },",
     "    get: function (k, d) {\n"
     "      try { var v = JSON.parse(localStorage.getItem('tcf_' + k)); return v === null || v === undefined ? d : v; }\n"
     "      catch (e) { return d; }\n"
     "    },"),

    # ---- 2. esc() left double quotes alone, and half its callers write into an
    # attribute (title=, data-t=, data-say=, href=). Nothing in the book contains a
    # quote today; the next sentence that does would break the markup around it.
    ("  function esc(s) {\n"
     "    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');\n"
     "  }\n"
     "  function rich(s) {\n"
     "    var t = esc(s);\n"
     "    ['b', 'i', 'u'].forEach(function (g) {\n"
     "      t = t.split('&lt;' + g + '&gt;').join('<' + g + '>').split('&lt;/' + g + '&gt;').join('</' + g + '>');\n"
     "    });\n"
     "    return t.split('&lt;br&gt;').join('<br>').split('\\n').join('<br>');\n"
     "  }",
     "  function esc(s) {\n"
     "    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')\n"
     "      .replace(/>/g, '&gt;').replace(/\"/g, '&quot;');\n"
     "  }\n"
     "  /* Whatever is not on this list is shown to her as literal angle brackets. That has\n"
     "     bitten twice now: the punctuation lesson in 第 12 章 printed <code>:</code> at her\n"
     "     instead of a colon, and the wrong-form examples lost the strike-through that was\n"
     "     the entire point of writing them. Add a tag here before using it in the data. */\n"
     "  var RICH_TAGS = ['b', 'i', 'u', 's', 'code', 'sup', 'sub'];\n"
     "  function rich(s) {\n"
     "    var t = esc(s);\n"
     "    RICH_TAGS.forEach(function (g) {\n"
     "      t = t.split('&lt;' + g + '&gt;').join('<' + g + '>').split('&lt;/' + g + '&gt;').join('</' + g + '>');\n"
     "    });\n"
     "    return t.split('&lt;br&gt;').join('<br>').split('\\n').join('<br>');\n"
     "  }\n"
     "  // a flashcard front is plain text, so markup that survives into it is visible\n"
     "  function plain(s) {\n"
     "    return String(s == null ? '' : s).replace(/<[^>]+>/g, '');\n"
     "  }\n"
     "  /* She types on a phone keyboard, where é and ç cost a long press. Searching for\n"
     "     「etudiant」 used to find 0 of the 68 étudiant in the book. Fold accents and both\n"
     "     apostrophes away on each side and the two spellings become the same word. */\n"
     "  function fold(s) {\n"
     "    s = String(s == null ? '' : s).toLowerCase().replace(/[\\u2018\\u2019\\u02bc]/g, \"'\");\n"
     "    if (s.normalize) { try { s = s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, ''); } catch (e) {} }\n"
     "    return s;\n"
     "  }"),

    # ---- 3. a failed clip left ARMED set, and ▶ then tried to resume the source
    # that had just failed instead of starting the chapter — dead for the session.
    ("  au.addEventListener('error', function () {\n"
     "    if (QI >= 0 && QI < QUEUE.length - 1) { QI++; playQueueItem(); return; }\n"
     "    clearHL(); QI = -1;\n"
     "    $('pPlay').textContent = '▶';\n"
     "    $('pNow').textContent = '播放失败';\n"
     "  });",
     "  au.addEventListener('error', function () {\n"
     "    if (QI >= 0 && QI < QUEUE.length - 1) { QI++; playQueueItem(); return; }\n"
     "    clearHL(); QI = -1;\n"
     "    ARMED = false;          // otherwise ▶ keeps retrying the clip that just failed\n"
     "    $('pPlay').textContent = '▶';\n"
     "    $('pNow').textContent = '播放失败';\n"
     "  });"),

    # ---- 4. 学习记录 counted plays that never made a sound. Offline on a chapter she
    # had not downloaded, one tap on 朗读本章 added a few hundred phantom plays.
    ("    var mine = ++PLAY_SEQ;\n"
     "    au.play().catch(function (e) {\n"
     "      // swapping src aborts the previous play(): that is normal, not a broken audio pack\n"
     "      if (e && (e.name === 'AbortError' || mine !== PLAY_SEQ)) return;\n"
     "      fetch('/api/ping').then(function () {\n"
     "        toast('这一条没能播放，换一句试试');\n"
     "      }).catch(function () { serverGone(); });\n"
     "    });\n"
     "    highlight(aid, srcEl);\n"
     "    if (window.tcfStats) window.tcfStats.audio(label);",
     "    var mine = ++PLAY_SEQ;\n"
     "    au.play().then(function () {\n"
     "      // count it only once it actually made a sound\n"
     "      if (mine === PLAY_SEQ && window.tcfStats) window.tcfStats.audio(label);\n"
     "    }, function (e) {\n"
     "      // swapping src aborts the previous play(): that is normal, not a broken audio pack\n"
     "      if (e && (e.name === 'AbortError' || mine !== PLAY_SEQ)) return;\n"
     "      fetch('/api/ping').then(function () {\n"
     "        toast('这一条没能播放，换一句试试');\n"
     "      }).catch(function () { serverGone(); });\n"
     "    });\n"
     "    highlight(aid, srcEl);"),

    # ---- 5. ⏭ / ⏮ did nothing after a single-sentence play, because playing one
    # sentence drops the queue. Build the chapter's queue around the current clip.
    ("  $('pNext').onclick = function () { if (QI >= 0 && QI < QUEUE.length - 1) { QI++; playQueueItem(); } };\n"
     "  $('pPrev').onclick = function () { if (QI > 0) { QI--; playQueueItem(); } };",
     "  /* Playing one sentence drops the queue, so ⏭ and ⏮ were inert after the single\n"
     "     most-used control in the app. Rebuild the chapter's list around whatever is\n"
     "     playing and step from there. */\n"
     "  function stepTo(d) {\n"
     "    if (QI < 0 || !QUEUE.length) {\n"
     "      var list = currentClips(), cur = (au.src || '').split('/').pop().replace(/\\.[a-z0-9]+$/, '');\n"
     "      var at = -1;\n"
     "      for (var i = 0; i < list.length; i++) if (list[i].aid === cur) { at = i; break; }\n"
     "      if (at < 0) { if (!list.length) { toast('本章没有可朗读的法语'); return; } startQueue(list, 0); return; }\n"
     "      QUEUE = list; QI = at;\n"
     "    }\n"
     "    var n = QI + d;\n"
     "    if (n < 0) { toast('已经是第一句'); return; }\n"
     "    if (n > QUEUE.length - 1) { toast('已经是最后一句'); return; }\n"
     "    QI = n; playQueueItem();\n"
     "  }\n"
     "  $('pNext').onclick = function () { stepTo(1); };\n"
     "  $('pPrev').onclick = function () { stepTo(-1); };"),

    # ---- 6. search folded to plain lowercase substring matching -----------------
    ("  function search(q) {\n"
     "    q = q.trim().toLowerCase();\n"
     "    if (q.length < 2) { if (VIEW === 'search') renderChapter(CUR); return; }\n"
     "    stopAll();\n"
     "    VIEW = 'search';",
     "  var SCROLL0 = 0;\n"
     "  function search(q) {\n"
     "    q = fold(q.trim());\n"
     "    if (q.length < 2) {\n"
     "      // coming back from a search used to dump her at the top of a chapter that can\n"
     "      // be eighty screens long\n"
     "      if (VIEW === 'search') { var back = SCROLL0; renderChapter(CUR); $('main').scrollTop = back; }\n"
     "      return;\n"
     "    }\n"
     "    if (VIEW !== 'search') SCROLL0 = $('main').scrollTop;\n"
     "    stopAll();\n"
     "    VIEW = 'search';"),

    ("      if ((fr + ' ' + (zh || '')).toLowerCase().indexOf(q) < 0) return;",
     "      if (fold(fr + ' ' + (zh || '')).indexOf(q) < 0) return;"),

    ("      var hay = [x.title, x.platform, x.kind, x.why, x.how, x.accent, x.level].join(' ').toLowerCase();",
     "      var hay = fold([x.title, x.platform, x.kind, x.why, x.how, x.accent, x.level].join(' '));"),

    # ---- 7. 背诵 from search results: 46% of the searchable French carries no
    # translation (prose lines and model sentences index with zh:''), so 看答案
    # revealed an empty box. Drill only what has an answer.
    ("    if (VIEW === 'search') {          //背诵搜索结果，而不是上一次浏览的章节\n"
     "      return HITS.filter(function (h) { return h.aid; })\n"
     "                 .map(function (h) { return { fr: h.fr, zh: h.zh, aid: h.aid }; });\n"
     "    }",
     "    if (VIEW === 'search') {          //背诵搜索结果，而不是上一次浏览的章节\n"
     "      return HITS.filter(function (h) { return h.aid && h.zh; })\n"
     "                 .map(function (h) { return { fr: h.fr, zh: h.zh, aid: h.aid }; });\n"
     "    }"),

    ("    if (!FC.list.length) { toast(VIEW === 'search' ? '搜索结果里没有可背诵的词卡' : '本章没有可背诵的词卡'); return; }",
     "    if (!FC.list.length) { toast(VIEW === 'search' ? '这些结果里没有带中文的句子，背不了' : '本章没有可背诵的词卡'); return; }"),

    ("    $('fcFr').textContent = it.fr;",
     "    $('fcFr').textContent = plain(it.fr);   // some table cells carry <b>, and this is plain text"),

    # ---- 8. just launching the app marked the restored chapter as read: a brand-new
    # install showed 「1 / 56 章」 and the daily plan opened on 第 2 章.
    ("    store.set('last', i);\n"
     "    if (window.tcfStats) window.tcfStats.view(c);\n"
     "    var done = store.get('done', {});\n"
     "    if (!done[c.key || i]) { done[c.key || i] = 1; store.set('done', done); }\n"
     "    markVisited();",
     "    store.set('last', i);\n"
     "    if (window.tcfStats) window.tcfStats.view(c);\n"
     "    /* Restoring where she left off is not the same as reading it. Marking the\n"
     "       restored chapter read made a fresh install claim 1 / 56 before she had seen\n"
     "       the welcome screen, and pushed the plan's 新课 slot to 第 2 章 on day one.\n"
     "       Deliberate navigation counts immediately; a restore has to earn it. */\n"
     "    clearTimeout(markTimer);\n"
     "    if (restoring) markTimer = setTimeout(function () { markRead(c, i); }, 45000);\n"
     "    else markRead(c, i);\n"
     "    markVisited();"),

    ("  function renderChapter(i) {\n"
     "    stopAll();               // otherwise the previous chapter keeps reading itself aloud",
     "  var markTimer = null;\n"
     "  function markRead(c, i) {\n"
     "    var done = store.get('done', {});\n"
     "    if (!done[c.key || i]) { done[c.key || i] = 1; store.set('done', done); markVisited(); }\n"
     "  }\n"
     "  function renderChapter(i, restoring) {\n"
     "    stopAll();               // otherwise the previous chapter keeps reading itself aloud"),

    ("    var last = Math.min(store.get('last', 0), d.chapters.length - 1);\n"
     "    renderChapter(last);",
     "    var last = Math.min(store.get('last', 0), d.chapters.length - 1);\n"
     "    renderChapter(last, true);"),
])
print("ok")
