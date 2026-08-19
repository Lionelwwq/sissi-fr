# -*- coding: utf-8 -*-
"""Probe the second video batch, drop dead/duplicate entries, keep what plays inline."""
import concurrent.futures as cf, glob, json, os, re, sys, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "zh-CN,zh;q=0.9,fr;q=0.8,en;q=0.7",
      "Accept-Encoding": "identity"}


def probe(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            body = r.read(6000).decode("utf-8", "replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, type(e).__name__


existing = set()
c = json.load(open(os.path.join("data", "content.json"), encoding="utf-8"))
for ch in c["chapters"]:
    for b in ch["blocks"]:
        for x in b.get("links") or []:
            existing.add(x["url"].rstrip("/").lower())

items, seen = [], set()
for f in sorted(glob.glob(os.path.join("gen4", "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    for it in d.get("items", []):
        u = (it.get("url") or "").strip().rstrip("/")
        if not u or u.lower() in seen or u.lower() in existing:
            continue
        seen.add(u.lower())
        it["_group"] = os.path.basename(f)[3:-5]
        items.append(it)
print("new & unique:", len(items))

with cf.ThreadPoolExecutor(max_workers=10) as ex:
    res = list(ex.map(lambda i: probe(i["url"]), items))

alive, dead = [], []
for it, (code, body) in zip(items, res):
    ok = bool(code) and code < 400
    # a bilibili video page for a removed upload still returns 200
    if ok and "bilibili.com/video/" in it["url"]:
        if re.search(r"(视频|稿件)不存在|已失效|已被删除|该视频已下架", body):
            ok = False
    (alive if ok else dead).append((it, code))

print("alive: %d   dead: %d" % (len(alive), len(dead)))
for it, code in dead:
    print("   [%s] %s" % (code, it["title"][:60]))

out = []
for it, _ in alive:
    m = re.search(r"bilibili\.com/video/(BV[0-9A-Za-z]+)", it["url"])
    a = re.search(r"bilibili\.com/video/av(\d+)", it["url"])
    if m:
        it["embed"] = "https://player.bilibili.com/player.html?bvid=%s&autoplay=0&high_quality=1" % m.group(1)
    elif a:
        it["embed"] = "https://player.bilibili.com/player.html?aid=%s&autoplay=0&high_quality=1" % a.group(1)
    else:
        it.pop("embed", None)
    host = re.sub(r"^https?://", "", it["url"]).split("/")[0].lower()
    if "bilibili.com" in host:
        it["cn_ok"] = "yes"
    elif any(t in host for t in ("youtube.com", "google.com", "netflix.com", "rfi.fr")):
        it["cn_ok"] = "vpn"
    else:
        it["cn_ok"] = "likely"
    out.append(it)
json.dump(out, open("links_new.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("embeddable after merge:", sum(1 for x in out if x.get("embed")))
