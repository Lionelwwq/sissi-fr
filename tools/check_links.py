# -*- coding: utf-8 -*-
"""Liveness-check every resource URL, dedupe, and classify China access honestly.

This machine is not in China, so "can she open it" is not testable here. Domain
family is the only thing that can be stated as fact; everything else is a guess and
is labelled as one.
"""
import concurrent.futures as cf, glob, json, os, re, sys, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "gen3")

BLOCKED = ("youtube.com", "youtu.be", "google.com", "googleusercontent", "facebook.com",
           "instagram.com", "twitter.com", "x.com", "netflix.com", "primevideo.com",
           "spotify.com", "apple.com/podcasts", "podcasts.apple.com")
CN_OK = ("bilibili.com", "xiaoyuzhoufm.com", "ximalaya.com", "qq.com", "iqiyi.com",
         "163.com", "zhihu.com", "douban.com", "weibo.com", "youku.com")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/148 Safari/537.36"}


def probe(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, url
    except Exception as e:
        return 0, type(e).__name__


items, seen = [], set()
for f in sorted(glob.glob(os.path.join(GEN, "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    for it in d.get("items", []):
        u = (it.get("url") or "").strip()
        if not u or u.lower() in seen:
            continue
        seen.add(u.lower())
        it["_group"] = os.path.basename(f).replace("video_", "").replace(".json", "")
        items.append(it)

print("unique items:", len(items))
with cf.ThreadPoolExecutor(max_workers=12) as ex:
    results = list(ex.map(lambda i: probe(i["url"]), items))

alive, dead = [], []
for it, (code, final) in zip(items, results):
    it["_http"] = code
    host = re.sub(r"^https?://", "", it["url"]).split("/")[0].lower()
    if any(b in host or b in it["url"] for b in BLOCKED):
        it["cn_ok"] = "vpn"
    elif any(c in host for c in CN_OK):
        it["cn_ok"] = "yes"
    else:
        it["cn_ok"] = "likely"          # honest: not testable from here
    (alive if code and code < 400 else dead).append(it)

print("alive: %d   dead/blocked: %d" % (len(alive), len(dead)))
for it in dead:
    print("   [%s] %s  %s" % (it["_http"], it["title"][:44], it["url"][:70]))
json.dump(alive, open(os.path.join(HERE, "links_alive.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
