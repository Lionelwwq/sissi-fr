# -*- coding: utf-8 -*-
"""Build the resource-library chapter and the "how to actually use it" chapter."""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = json.load(open(os.path.join(HERE, "links_probed.json"), encoding="utf-8"))
COLOR = "#0e7490"

LVL = {"A2": 0, "B1": 1, "B2": 2}


def clean(it):
    return {k: it[k] for k in ("title", "url", "platform", "kind", "level", "accent",
                               "length", "free", "cn_ok", "why", "how") if k in it}


def sort_key(it):
    # what she can open without a VPN comes first, then easiest first
    return (0 if it.get("cn_ok") == "yes" else 1 if it.get("cn_ok") == "likely" else 2,
            LVL.get(it.get("level"), 1))


def pick(pred):
    return [clean(x) for x in sorted([i for i in ITEMS if pred(i)], key=sort_key)]


def links_block(title, items):
    return {"kind": "links", "title": title, "links": items}


# ---------------------------------------------------------------- chapter A
def chapter_resources():
    b = [
        {"kind": "para", "text": "这一章的每一条我都<b>逐条打开验证过</b>（91 条全部在线），"
                                 "并且标了三件她最需要知道的事：<b>难度</b>、<b>口音</b>、"
                                 "以及<b>在国内点不点得开</b>。排序也按这个来——"
                                 "不用梯子的排前面，简单的排前面。"},
        {"kind": "warn", "title": "关于「国内可看」这个标签，说实话",
         "text": "带 <b>需要梯子</b> 的是确定的（YouTube、Netflix、Spotify 这些域名在国内确实打不开）。"
                 "带 <b>国内可看</b> 的也是确定的（B 站、小宇宙、喜马拉雅）。"
                 "剩下标 <b>大概率可以</b> 的（法国、加拿大的官方教育网站），"
                 "<b>我没法替你测</b>——我这边的网络不在国内，测出来不算数。"
                 "这类你点开试一下就知道，能开就是能开。"},
    ]

    official = pick(lambda i: any(k in (i.get("platform") or "")
                                  for k in ("TV5MONDE", "RFI", "France Éducation",
                                            "France Education", "français facile")))
    b.append({"kind": "h4", "title": "① 先用这些——出题方自己给的免费材料"})
    b.append({"kind": "tip", "title": "这一组的价值高于其他所有",
              "text": "TCF 的出题方是 France Éducation international，TV5MONDE 是它认可的备考平台。"
                      "<b>600 道免费练习题 + 全真模拟器</b>，题型和真考一致。"
                      "任何影视剧、TED 都比不上先把这个刷完。"})
    b.append(links_block("官方备考与分级练习（%d 条）" % len(official), official))

    canada = pick(lambda i: "加拿大" in (i.get("accent") or "")
                  and i not in [x for x in ITEMS if False])
    canada = [x for x in canada if x["url"] not in {o["url"] for o in official}]
    b.append({"kind": "h4", "title": "② 加拿大法语口音——你考的是 TCF Canada"})
    b.append({"kind": "para", "text": "考场录音里有魁北克口音，元音更松、语调更平，"
                                      "只听惯法国法语的人第一次听会明显吃力。"
                                      "<b>每周至少听一次加拿大口音</b>，比临考前突击有用得多。"})
    b.append(links_block("加拿大 / 魁北克法语（%d 条）" % len(canada), canada))

    used = {x["url"] for x in official} | {x["url"] for x in canada}
    bili = [x for x in pick(lambda i: i["_group"] == "bilibili") if x["url"] not in used]
    b.append({"kind": "h4", "title": "③ B 站——不用梯子，随时能看"})
    b.append(links_block("B 站课程与合集（%d 条）" % len(bili), bili))

    used |= {x["url"] for x in bili}
    pod = [x for x in pick(lambda i: i["_group"] == "podcast") if x["url"] not in used]
    b.append({"kind": "h4", "title": "④ 播客——地铁上、走路时听"})
    b.append({"kind": "para", "text": "音频最省流量，也最适合她的通勤场景。"
                                      "<b>优先选带文字稿（transcript）的</b>——没有文字稿的听力材料，"
                                      "听不懂的地方永远听不懂。"})
    b.append(links_block("播客与短音频（%d 条）" % len(pod), pod))

    used |= {x["url"] for x in pod}
    ted = [x for x in pick(lambda i: i["_group"] == "ted") if x["url"] not in used]
    b.append({"kind": "h4", "title": "⑤ 演讲——直接对口语 Tâche 3"})
    b.append({"kind": "para", "text": "Tâche 3 要你就一个观点讲 4 分 30。"
                                      "演讲者怎么开头、怎么举例、怎么收尾，就是你要抄的结构。"
                                      "<b>不必听完</b>——听前两分钟，把他亮观点的那句话记下来。"})
    b.append(links_block("TED 与公开讲座（%d 条）" % len(ted), ted))

    used |= {x["url"] for x in ted}
    film = [x for x in pick(lambda i: i["_group"] == "film") if x["url"] not in used]
    b.append({"kind": "h4", "title": "⑥ 影视——放松用，别当主力"})
    b.append({"kind": "warn", "title": "影视剧是性价比最低的备考材料",
              "text": "语速快、俚语多、剧情占掉注意力，一小时里真正练到听力的可能只有几分钟。"
                      "<b>它的作用是让你不讨厌法语</b>，不是提分。"
                      "考前三个月，每周最多留一次，其余时间给上面那几组。"})
    b.append(links_block("影视与纪录片（%d 条）" % len(film), film))
    return b


# ---------------------------------------------------------------- chapter B
def chapter_method():
    return [
        {"kind": "para", "text": "材料越多越容易变成收藏夹里的坟墓。这一章只讲两件事："
                                 "<b>一段音频到底怎么练</b>，和<b>到考试前每周做什么</b>。"},
        {"kind": "h4", "title": "一、精听：一段 3 分钟的音频，练 20 分钟"},
        {"kind": "steps", "title": "五遍法（别跳步，跳了就变成「听个响」）", "items": [
            "<b>第一遍：盲听，不看任何文字。</b>只问自己一个问题——这段在讲什么？答不上来也不要回放。",
            "<b>第二遍：还是盲听。</b>这次记 3 个关键词（人物 / 数字 / 地点）。TCF 听力题问的就是这些。",
            "<b>第三遍：边听边看文字稿。</b>把「听的时候没听出来、但看到就认识」的词划出来——"
            "<b>这类词才是你的真问题</b>：不是不认识，是听不出来。多半栽在连诵和哑音 e 上。",
            "<b>第四遍：只听划出来的那几句</b>，一句听三遍，跟着念出声。念到能跟上语速为止。",
            "<b>第五遍：合上文字稿再盲听一遍。</b>如果还有听不出来的，抄进生词本，明天再来。",
        ]},
        {"kind": "tip", "title": "为什么是「听得出来」而不是「认识」",
         "text": "中国学生的法语听力瓶颈几乎从来不是词汇量，而是<b>词在句子里被连起来读之后认不出</b>。"
                 "«Il y a un an» 听起来是 /i.ja.œ̃.nɑ̃/，四个词糊成一团。"
                 "所以精听要抓的不是生词，是<b>你明明认识却没听出来的词</b>——"
                 "这个清单通常出奇地短，练两周就有明显变化。"},
        {"kind": "h4", "title": "二、跟读：口语提分最快的一件事"},
        {"kind": "bullets", "title": "每天 10 分钟，只做这个", "items": [
            "挑一段 <b>30 秒</b>的音频（本书任意一段的「🔊 朗读本段法语」就行）。",
            "第一步<b>影子跟读</b>：音频不停，你落后半句跟着念，念不全也别停。",
            "第二步<b>逐句复述</b>：放一句，暂停，凭记忆重复一遍，再对照。",
            "第三步<b>录下来自己听</b>。第一次会很难受，但这是唯一能发现自己发音问题的方法。",
            "重点听三件事：<b>阴性配合有没有漏</b>、连诵有没有做、句尾语调有没有往下压。",
        ]},
        {"kind": "h4", "title": "三、到考试前，每周这样排"},
        {"kind": "table", "title": "一周五天，每天 45 分钟（周末休息）",
         "columns": ["", "做什么", "用哪里的材料", "多久"],
         "rows": [
             ["周一", "听力精听（五遍法）", "RFI 慢速新闻 / TV5MONDE 分级练习", "20 分钟"],
             ["", "变位复习", "第 24 章「连读」卡片，开背诵模式", "10 分钟"],
             ["", "跟读", "当天精听的那一段", "15 分钟"],
             ["周二", "阅读 + 生词", "TV5MONDE 官方练习", "25 分钟"],
             ["", "主题论点", "第 53-54 章，挑一个主题背 2 好处 1 坏处", "20 分钟"],
             ["周三", "口语 Tâche 2", "第 VII 部分场景问句，自己出声演一遍", "25 分钟"],
             ["", "加拿大口音", "Radio-Canada / «Ça bouge au Canada»", "20 分钟"],
             ["周四", "写作 Tâche 1 或 2", "第 III 部分范文，先写再对", "30 分钟"],
             ["", "错误复盘", "第 21 章 + 第 26 章高频错误", "15 分钟"],
             ["周五", "全真模拟一套", "TV5MONDE 模拟器（计时、不回放）", "45 分钟"],
         ]},
        {"kind": "warn", "title": "只记住一条的话，记这条",
         "text": "<b>宁可每天 30 分钟连续做 8 周，也不要周末一次 5 小时。</b>"
                 "语言是习惯，不是知识。断三天，听力辨音的手感就会掉回去——"
                 "这也是为什么上面的表把每天压到 45 分钟：能长期做下去的强度，才是有效强度。"},
        {"kind": "tip", "title": "考前两周",
         "text": "停止学新东西。只做三件事：① 每天一套 TV5MONDE 模拟题保持手感；"
                 "② 把第 26 章的 72 句考场整句和第 53-54 章的 40 句核心立场背到脱口而出；"
                 "③ 每天大声念 20 分钟法语，让嘴巴保持状态。"
                 "<b>考前一天什么都别做</b>，睡够。"},
    ]


def main():
    content = json.load(open(os.path.join(HERE, "data", "content.json"), encoding="utf-8"))
    ch = content["chapters"]
    if any(c.get("key", "").startswith("res_") for c in ch):
        raise SystemExit("resource chapters already present")

    new = [
        {"key": "res_library", "zh": "视频与听力资源库（91 条，逐条验证过）",
         "fr": "Ressources vidéo et audio — 91 liens vérifiés",
         "intro": "官方备考题库、加拿大口音材料、B 站课程、播客、TED、影视，按「国内点不点得开」"
                  "和难度排好序。每条都写清为什么有用、具体怎么练。",
         "blocks": chapter_resources()},
        {"key": "res_method", "zh": "怎么用这些材料练（精听五遍法 + 周计划）",
         "fr": "Méthode — écoute intensive et plan hebdomadaire",
         "intro": "材料多不等于练得好。这一章讲一段音频具体怎么练，以及到考试前每周排什么。",
         "blocks": chapter_method()},
    ]
    for c in new:
        c["part"] = "VI"
        c["partzh"] = "备考执行"
        c["color"] = COLOR

    at = max(i for i, c in enumerate(ch) if c["part"] == "VI") + 1
    ch[at:at] = new
    for i, c in enumerate(ch):
        c["no"] = i + 1

    json.dump(content, open(os.path.join(HERE, "data", "content.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    nlinks = sum(len(b["links"]) for c in new for b in c["blocks"] if b["kind"] == "links")
    print("chapters now:", len(ch))
    print("new:", [(c["no"], c["zh"][:26]) for c in ch if c["key"].startswith("res_")])
    print("link cards placed:", nlinks, "of", len(ITEMS))


if __name__ == "__main__":
    main()
