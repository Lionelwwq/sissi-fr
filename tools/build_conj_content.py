# -*- coding: utf-8 -*-
"""Turn the verified tables + teaching files into three Part IV chapters.

Emits content_v2.json and tts_manifest.json (id -> text to synthesize) so the audio
step can be re-run on its own.
"""
import hashlib, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
REF = json.load(open(os.path.join(HERE, "conj_ref.json"), encoding="utf-8"))
SAY = REF["say"]
VERBS = ["etre", "avoir", "aller", "faire", "pouvoir", "vouloir", "devoir", "venir", "prendre"]
TKEY = ["Present", "PasseCompose", "Imparfait", "FuturSimple", "Conditionnel", "Subjonctif"]
TFR = ["Présent", "Passé composé", "Imparfait", "Futur simple", "Conditionnel présent", "Subjonctif présent"]
TZH = ["现在时", "复合过去时", "未完成过去时", "简单将来时", "条件式现在时", "虚拟式现在时"]
COLOR = "#7c3aed"           # Part IV purple
CIRC = "①②③④⑤⑥⑦⑧⑨"
ZH = {"etre": "是 / 在（万能助动词）", "avoir": "有（也是最常用的助动词）", "aller": "去（也是最快的将来时）",
      "faire": "做 / 干（万能动词）", "pouvoir": "能 / 可以", "vouloir": "想要",
      "devoir": "应该 / 必须（也表推测）", "venir": "来（venir de = 刚刚）", "prendre": "拿 / 乘坐 / 花时间"}

MANIFEST = {}


def aid_for(text, slow=False):
    """Stable id so re-running never regenerates audio that already exists."""
    say = re.sub(r"\s+", " ", text).strip()
    key = ("S|" if slow else "N|") + say
    h = hashlib.md5(key.encode("utf-8")).hexdigest()[:16]
    MANIFEST[h] = {"text": say, "slow": slow}
    return h


def display(cell):
    return (cell.replace("il/elle ", "il ").replace("ils/elles ", "ils ")
                .replace("qu'il/elle ", "qu'il ").replace("qu'ils/elles ", "qu'ils "))


def spoken(cell):
    s = SAY.get(cell, cell)
    s = s.split(" / ")[0] if " / " in s and "," not in s else s
    return display(s)


def teach(v):
    return json.load(open(os.path.join(HERE, "gen", "teach_%s.json" % v), encoding="utf-8"))


# ---------------------------------------------------------------- chapter 1
def chapter_tables():
    b = [
        {"kind": "para", "text": "这一章只有一件事：把 9 个最常用的不规则动词，在 6 个时态、6 个人称下的形式，"
                                 "一次性摆在你眼前。<b>点任意一格就能听到发音</b>，点表格下面的「连读」卡片能听到整行六个形式连着念——"
                                 "这就是法国小学生背变位的方式，比默写有效得多。"},
        {"kind": "bullets", "title": "为什么偏偏是这 9 个", "items": [
            "<b>être / avoir</b>：它们自己是动词，同时又是所有复合时态的助动词。这两个不熟，passé composé 全线崩。",
            "<b>aller</b>：除了「去」，还负责最省事的将来表达 <b>aller + 原形</b>（je vais chercher un appartement）。",
            "<b>faire</b>：法语里「做什么」的万能动词，天气、家务、学科、运动全靠它。",
            "<b>pouvoir / vouloir / devoir</b>：三个情态动词，后面直接跟原形，是你在口语 Tâche 2 里提要求、谈条件的主力。",
            "<b>venir</b>：venir de + 原形 = 刚刚做完某事，一句话就能体现时间层次。",
            "<b>prendre</b>：拿、乘车、花时间、点菜——一个词覆盖大量生活场景，而且 comprendre / apprendre 跟它同型。",
        ]},
        {"kind": "warn", "title": "看表之前先记住这条：你是女生",
         "text": "<b>aller</b> 和 <b>venir</b> 的复合过去时用 <b>être</b> 作助动词，过去分词必须跟主语配合。"
                 "所以凡是你自己说的，一律带 <b>-e</b>：<b>je suis allée</b> / <b>je suis venue</b> / je suis arrivée / je suis restée。"
                 "表里 <i>je</i> 那一格我已经直接给你写成阴性形式了。男性说 allé，"
                 "读音完全一样，但<b>写</b>出来漏掉 e 就是考官一眼能抓的低级错。"},
    ]

    for i, v in enumerate(VERBS):
        tb = REF["verbs"][v]
        t = teach(v)
        b.append({"kind": "h4", "title": "%s « %s » —— %s" % (CIRC[i], tb["inf"], ZH[v])})
        b.append({"kind": "para", "text": t["why"]})

        rows, aids = [], []
        for ti, tk in enumerate(TKEY):
            row = ["<b>%s</b><br>%s" % (TFR[ti], TZH[ti])]
            arow = [None]
            for cell in tb[tk]:
                row.append(display(cell))
                arow.append(aid_for(spoken(cell), slow=True))
            rows.append(row)
            aids.append(arow)
        b.append({"kind": "table",
                  "title": "« %s » 六时态 × 六人称（点格子听发音）" % tb["inf"],
                  "columns": ["时态", "je", "tu", "il · elle", "nous", "vous", "ils · elles"],
                  "rows": rows, "aids": aids})

        cards = []
        for ti, tk in enumerate(TKEY):
            chant = " · ".join(display(c) for c in tb[tk])
            say = ", ".join(spoken(c) for c in tb[tk])
            cards.append({"fr": chant, "zh": "%s（%s）" % (TFR[ti], TZH[ti]),
                          "note": "整行连着念三遍，比单格默写快得多。", "aid": aid_for(say, slow=True)})
        b.append({"kind": "cards", "title": "连读记忆 —— « %s » 六行，每行一口气念完" % tb["inf"], "cards": cards})

    b.append({"kind": "tip", "title": "怎么用这一章（别从头背到尾）",
              "text": "① 先只背 <b>être / avoir</b> 的 6 行——它们撑起所有复合时态。<br>"
                      "② 再背 <b>Présent + Passé composé</b> 两列的全部 9 个动词，这两个时态占口语实际用量的七成以上。<br>"
                      "③ <b>Conditionnel</b> 只要背熟 je 那一格：je serais / j'aurais / je voudrais / je pourrais / je devrais，"
                      "这五个是你全场最礼貌、最像 B2 的表达。<br>"
                      "④ <b>Subjonctif</b> 先背 que je sois / que j'aie / que je puisse / que je fasse 四个，"
                      "配合 il faut que…、je voudrais que… 就够用了。<br>"
                      "⑤ 每天开 <b>🎴 背诵模式</b> 过一遍「连读」卡片，10 分钟。"})
    return b


# ---------------------------------------------------------------- chapter 2
def chapter_when():
    b = [{"kind": "para",
          "text": "变位背下来只是第一步。考官真正在听的是<b>你有没有选对时态</b>——同一个动词换个时态，"
                  "整句话的意思和你给人的水平印象都会变。这一章把每个动词的 6 个时态各配一句"
                  "<b>你真的会说的话</b>：面试、租房、办卡、跟同事解释工作。点例句可以听发音。"}]
    for i, v in enumerate(VERBS):
        tb = REF["verbs"][v]
        t = teach(v)
        b.append({"kind": "h4", "title": "%s « %s » 六个时态分别什么时候用" % (CIRC[i], tb["inf"])})
        rows, aids = [], []
        for x in t["tense_use"]:
            rows.append(["<b>%s</b>" % x["tense"], x["when"],
                         "<b>%s</b><br>%s" % (x["example_fr"], x["example_zh"])])
            aids.append([None, None, aid_for(x["example_fr"])])
        b.append({"kind": "table", "title": "« %s » 时态选择对照" % tb["inf"],
                  "columns": ["时态", "什么时候用它", "例句（点这一列听发音）"],
                  "rows": rows, "aids": aids})
        b.append({"kind": "tip", "title": "« %s » 的发音陷阱" % tb["inf"],
                  "text": "<br>".join("<b>%s</b> —— %s" % (p["form"], p["tip"]) for p in t["pron"])})
    return b


# ---------------------------------------------------------------- chapter 3
def chapter_traps():
    b = [{"kind": "para",
          "text": "下面每一条「错」都不是我编的极端例子，而是中文母语者<b>真的会写出来</b>的句子——"
                  "多数来自中文和英语的双重干扰。先遮住右边自己判断错在哪，再看解释。"
                  "后半部分是可以整句搬进考场的句子，点一下就能听。"}]
    for i, v in enumerate(VERBS):
        tb = REF["verbs"][v]
        t = teach(v)
        b.append({"kind": "h4", "title": "%s « %s » 高频错误" % (CIRC[i], tb["inf"])})
        rows, aids = [], []
        for x in t["traps"]:
            rows.append(["<b>✗</b> %s" % x["wrong"], "<b>✓</b> %s" % x["right"], x["why"]])
            aids.append([None, aid_for(x["right"]), None])
        b.append({"kind": "table", "title": "« %s » 改错对照（点 ✓ 那一列听正确读法）" % tb["inf"],
                  "columns": ["常见错句", "改对", "错在哪"], "rows": rows, "aids": aids})
        b.append({"kind": "cards", "title": "« %s » 考场整句（背下来直接用）" % tb["inf"],
                  "cards": [{"fr": c["fr"], "zh": c["zh"], "note": c["note"],
                             "aid": aid_for(c["fr"])} for c in t["chunks"]]})
    return b


def main():
    content = json.load(open(os.path.join(HERE, "data", "content.json"), encoding="utf-8"))
    chapters = content["chapters"]
    if any(c.get("key", "").startswith("conj_") for c in chapters):
        raise SystemExit("conjugation chapters already present — rebuild from a clean content.json")

    new = [
        {"key": "conj_tables", "zh": "九大核心动词 · 六时态变位总表",
         "fr": "Les 9 verbes indispensables — tableaux de conjugaison",
         "intro": "être / avoir / aller / faire / pouvoir / vouloir / devoir / venir / prendre，"
                  "9 个动词 × 6 时态 × 6 人称 = 324 个形式，每一格都能点开听。这是全书唯一需要"
                  "「死记」的一章，但也是投入产出比最高的一章。",
         "blocks": chapter_tables()},
        {"key": "conj_when", "zh": "九大核心动词 · 什么时候用哪个时态",
         "fr": "Quel temps choisir — 9 verbes en situation",
         "intro": "同一个动词，选错时态就等于说错话。这一章给每个动词的 6 个时态各配一句你真的用得上的例句，"
                  "外加最容易读错的几个形式。",
         "blocks": chapter_when()},
        {"key": "conj_traps", "zh": "九大核心动词 · 高频错误与考场整句",
         "fr": "Erreurs typiques et phrases prêtes à l'emploi",
         "intro": "中文母语者在这 9 个动词上会犯的错高度重复。先把错认出来，再把 72 句考场可以直接搬用的"
                  "整句背熟。",
         "blocks": chapter_traps()},
    ]
    for c in new:
        c["part"] = "IV"
        c["partzh"] = "语言基础"
        c["color"] = COLOR

    at = max(i for i, c in enumerate(chapters) if c["part"] == "IV") + 1
    chapters[at:at] = new
    for i, c in enumerate(chapters):
        c["no"] = i + 1

    json.dump(content, open(os.path.join(HERE, "data", "content_v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    json.dump(MANIFEST, open(os.path.join(HERE, "tts_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("chapters:", len(chapters), "inserted at", at + 1)
    print("new chapter numbers:", [c["no"] for c in chapters if c["key"].startswith("conj_")])
    print("blocks:", [len(c["blocks"]) for c in new])
    print("clips to synthesize:", len(MANIFEST))


if __name__ == "__main__":
    main()
