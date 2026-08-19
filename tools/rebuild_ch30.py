# -*- coding: utf-8 -*-
"""Rebuild the resource chapter from all verified items, grouped by what she wants to do."""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "data", "content.json"), encoding="utf-8"))
NEW = json.load(open(os.path.join(HERE, "links_new.json"), encoding="utf-8"))

# the 91 already in the book carry their final cn_ok/embed, so reuse them as-is
old = []
for ch in C["chapters"]:
    if ch.get("key") != "res_library":
        continue
    for b in ch["blocks"]:
        for x in b.get("links") or []:
            old.append(x)
print("existing:", len(old), " new:", len(NEW))

FIELDS = ("title", "url", "platform", "kind", "level", "level_why", "accent",
          "length", "free", "cn_ok", "embed", "why", "how")


def norm(x):
    d = {k: x[k] for k in FIELDS if k in x and x[k] not in (None, "")}
    d.setdefault("level", "B1")
    return d


ALL = [norm(x) for x in old] + [norm(x) for x in NEW]
seen, items = set(), []
for x in ALL:
    k = x["url"].rstrip("/").lower()
    if k in seen:
        continue
    seen.add(k)
    items.append(x)
print("total unique:", len(items), " embeddable:", sum(1 for x in items if x.get("embed")))

OFFICIAL = ("TV5MONDE", "France Éducation", "France Education", "français facile", "RFI")


def group_of(x):
    p, k, t = x.get("platform", ""), x.get("kind", ""), x.get("title", "")
    acc = x.get("accent", "")
    if any(o in p for o in OFFICIAL) or "TCF" in t and "官方" in t:
        return "official"
    if k == "演讲" or "TED" in t or "TED" in p:
        return "ted"
    if re.search(r"听力|听辨|精听|真题|Section", t):
        return "listen"
    if re.search(r"口语|发音|连诵|语音|跟读|口音", t) and "加拿大" not in acc:
        return "speak"
    if "加拿大" in acc or "魁北克" in t or "魁北克" in acc:
        return "canada"
    if k in ("音频",) or "播客" in k or "播客" in p:
        return "podcast"
    if k in ("影视剧", "纪录片") or "电影" in t:
        return "film"
    return "topic"


LVL = {"A2": 0, "B1": 1, "B2": 2}


def order(x):
    # what she can actually press play on, in her own country, easiest first
    return (0 if x.get("embed") else 1,
            0 if x.get("cn_ok") == "yes" else 1 if x.get("cn_ok") == "likely" else 2,
            LVL.get(x.get("level"), 1))


G = {}
for x in items:
    G.setdefault(group_of(x), []).append(x)
for k in G:
    G[k].sort(key=order)

SECTIONS = [
    ("official", "① 先用这个 —— 出题方认可的官方备考材料",
     "TCF 的出题方是 France Éducation international，TV5MONDE 是它认可的备考平台："
     "<b>600 道免费练习题 + 全真模拟器</b>，题型和真考一致。"
     "任何影视剧、TED 都比不上先把这个刷完。"),
    ("ted", "② TED 与演讲 —— 直接对口语 Tâche 3",
     "Tâche 3 要你就一个观点讲 4 分 30。演讲者怎么开头、怎么举例、怎么收尾，就是你要抄的结构。"
     "<b>不必听完</b>：听前两分钟，把他亮观点的那一句记下来。"
     "带 <b>▶ 能直接播</b> 的可以在这一页里看完，不用跳走。"),
    ("listen", "③ 听力训练 —— 真题课与分级练习",
     "这一组是提分主力。<b>先做题再看讲解</b>，只看错的那几道；"
     "直接看讲解等于看别人做题，没有用。"),
    ("speak", "④ 口语与发音",
     "发音问题自己听不出来，一定要<b>录下来回放</b>。"
     "重点听三件事：阴性配合有没有漏、连诵有没有做、句尾语调有没有往下压。"),
    ("topic", "⑤ 主题输入 —— 配合第 53-54 章的十大主题",
     "学完一个主题的论点之后，用这一组做输入。"
     "看的时候只做一件事：<b>把你在第 53-54 章背过的说法，在视频里听到了哪几个</b>。"),
    ("canada", "⑥ 加拿大 / 魁北克口音 —— 你考的是 TCF Canada",
     "考场录音里有魁北克口音，元音更松、语调更平，只听惯法国法语的人第一次会明显吃力。"
     "<b>每周至少听一次</b>，比临考前突击有用得多。"),
    ("podcast", "⑦ 播客 —— 地铁上、走路时听",
     "音频最省流量，也最适合通勤。<b>优先选带文字稿的</b>——"
     "没有文字稿的听力材料，听不懂的地方永远听不懂。"),
    ("film", "⑧ 影视 —— 放松用，别当主力",
     "语速快、俚语多、剧情占掉注意力，一小时里真正练到听力的可能只有几分钟。"
     "<b>它的作用是让你不讨厌法语</b>，不是提分。考前三个月每周最多留一次。"),
]


def build():
    playable = sum(1 for x in items if x.get("embed"))
    b = [
        {"kind": "para",
         "text": "共 <b>%d 条</b>，每一条都逐条打开验证过。其中 <b>%d 条能直接在这一页里播放</b>——"
                 "卡片上有 <b>▶ 在这里看</b> 就是。<br>"
                 "每组上方有筛选条：按 <b>A2 / B1 / B2</b> 挑难度，或者只看能直接播的、国内能开的。"
                 % (len(items), playable)},
        {"kind": "warn", "title": "先看这个：哪些国内点得开",
         "text": "<b>需要梯子</b>：YouTube、Netflix，以及 <b>RFI（francaisfacile.rfi.fr）</b>——"
                 "RFI 在中国大陆是被墙的，很多备考清单不会告诉你，但它偏偏是最好的慢速新闻源。"
                 "有梯子就用，没有就用 TV5MONDE 顶上。<br>"
                 "<b>国内可看</b>：B 站、小宇宙、喜马拉雅，确定能开。"
                 "<b>能直接播的全部是 B 站的</b>，所以不用担心。<br>"
                 "<b>大概率能开 · 点一下试试</b>：法国和加拿大的官方教育网站。"
                 "<b>我没法替你测</b>——网络不在国内，测出来不算数。点开试一下就知道。"},
        {"kind": "tip", "title": "怎么挑",
         "text": "① 时间少就只看 <b>▶ 能直接播</b> 的，省掉跳转和找入口。<br>"
                 "② 难度先选 <b>A2</b> 和 <b>B1</b>；B2 那些等你听力稳了再回来，"
                 "现在硬啃只会打击信心。<br>"
                 "③ 每个卡片下面写了「怎么练」，照做就行，别只是看完。<br>"
                 "④ 具体的练法在<b>下一章</b>（精听五遍法 + 周计划）。"},
    ]
    for key, title, blurb in SECTIONS:
        lst = G.get(key) or []
        if not lst:
            continue
        n_emb = sum(1 for x in lst if x.get("embed"))
        b.append({"kind": "h4", "title": title})
        b.append({"kind": "para", "text": blurb})
        b.append({"kind": "links",
                  "title": "%d 条%s" % (len(lst), ("，其中 %d 条能直接播" % n_emb) if n_emb else ""),
                  "links": lst})
    return b


for ch in C["chapters"]:
    if ch.get("key") == "res_library":
        ch["blocks"] = build()
        ch["zh"] = "视频与听力资源库（%d 条，%d 条能直接播）" % (
            len(items), sum(1 for x in items if x.get("embed")))
        ch["intro"] = ("官方备考题库、TED 演讲、听力真题课、口语发音、十大主题输入、"
                       "加拿大口音、播客、影视，全部逐条验证。带 ▶ 的可以直接在页面里播放。")
json.dump(C, open(os.path.join(HERE, "data", "content.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("groups:", {k: len(v) for k, v in sorted(G.items())})
print("placed:", sum(len(v) for v in G.values()))
