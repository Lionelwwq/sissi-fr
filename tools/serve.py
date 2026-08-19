# -*- coding: utf-8 -*-
"""TCF 法语学习助手 —— 本地服务端（教材 + 发音 + 点词查词 + 动词变位）。

做题与模考模块已移除，所以这一版不再需要 SQLite 题库、复习队列和作文批改引擎；
剩下要做的事只有三件：把 JSON 发出去、从 zip 里取音频、把生词本存到用户目录。
"""
import io
import json
import os
import socket
import sys
import threading
import urllib.request
import webbrowser
import zipfile

from flask import Flask, Response, jsonify, request, send_from_directory

APP_NAME = "TCFCoach"
IDENT = "tcf-coach-reader"

# ---------------------------------------------------------------- paths
def base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # PyInstaller unpacks --add-data here
    return os.path.dirname(os.path.abspath(__file__))

BASE = base_dir()
DATA = os.path.join(BASE, "data")
if not os.path.isdir(DATA):
    DATA = BASE                      # frozen build keeps the packs flat
STATIC = os.path.join(BASE, "static")

def user_dir():
    """Writable per-user folder. Never next to the exe: it may sit on a read-only stick."""
    for root in (os.environ.get("APPDATA"), os.path.expanduser("~")):
        if not root:
            continue
        d = os.path.join(root, APP_NAME)
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".w")
            with open(probe, "w") as f:
                f.write("1")
            os.remove(probe)
            return d
        except Exception:
            continue
    return os.path.abspath(".")

UDIR = user_dir()
VOCAB = os.path.join(UDIR, "vocab.json")
PORTFILE = os.path.join(UDIR, "port.txt")

# ---------------------------------------------------------------- data
def load_json(name, default=None):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)

CONTENT = load_json("content.json", {"chapters": [], "topics": [], "parts": []})
DICT = load_json("bank_dict.json", {})
WORD_INDEX = load_json("word_index.json", {})
CONJ = load_json("conj_index.json", {})

# zipfile objects are not thread-safe and waitress serves audio concurrently;
# RLock (not Lock) because a handler may take the pack twice in one request
_ZLOCK = threading.RLock()
_ZIPS = {}

def pack(name):
    with _ZLOCK:
        z = _ZIPS.get(name)
        if z is None:
            p = os.path.join(DATA, name)
            if not os.path.exists(p):
                return None
            z = _ZIPS[name] = zipfile.ZipFile(p)
        return z

MIME = {".opus": "audio/ogg", ".mp3": "audio/mpeg", ".m4a": "audio/mp4"}

def send_clip(names, member_base):
    """Look for <base>.<ext> across the given packs and stream the first hit."""
    for name in names:
        z = pack(name)
        if not z:
            continue
        for ext in (".opus", ".mp3"):
            try:
                with _ZLOCK:
                    blob = z.read(member_base + ext)
            except KeyError:
                continue
            r = Response(blob, mimetype=MIME[ext])
            r.headers["Cache-Control"] = "public, max-age=604800"
            r.headers["Content-Length"] = str(len(blob))
            return r
    return ("not found", 404)

# ---------------------------------------------------------------- app
app = Flask(__name__, static_folder=None)

@app.after_request
def no_store_html(resp):
    if resp.mimetype in ("text/html", "application/javascript", "text/css", "application/json"):
        resp.headers["Cache-Control"] = "no-store"
    return resp

@app.route("/")
def home():
    return send_from_directory(STATIC, "index.html")

@app.route("/static/<path:p>")
def static_file(p):
    return send_from_directory(STATIC, p)

@app.route("/api/content")
def api_content():
    return jsonify(CONTENT)

@app.route("/api/dict")
def api_dict():
    return jsonify(DICT)

@app.route("/api/dict/audio-index")
def api_dict_audio():
    return jsonify(WORD_INDEX)

@app.route("/api/conj")
def api_conj():
    """form -> [{v,t,p}] so clicking « serions » can say what it is."""
    return jsonify(CONJ)

@app.route("/audio/<aid>")
def audio(aid):
    if not aid.replace("-", "").replace("_", "").isalnum():
        return ("bad id", 400)
    return send_clip(("audio.zip", "conj.zip"), aid)

@app.route("/word/<wid>")
def word(wid):
    if not wid.replace("-", "").replace("_", "").isalnum():
        return ("bad id", 400)
    return send_clip(("words.zip", "conj.zip"), wid)

# ---------------------------------------------------------------- vocab
_VLOCK = threading.Lock()

def read_vocab():
    try:
        with open(VOCAB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

@app.route("/api/vocab/list")
def vocab_list():
    return jsonify(read_vocab())

@app.route("/api/vocab/add", methods=["POST"])
def vocab_add():
    d = request.get_json(silent=True) or {}
    w = (d.get("word") or "").strip()
    if not w:
        return jsonify({"ok": False})
    with _VLOCK:
        items = read_vocab()
        if not any(x.get("word", "").lower() == w.lower() for x in items):
            items.append({
                "word": w,
                "lemma": d.get("lemma") or w,
                "gloss": d.get("gloss") or "",
                "sentence": d.get("sentence") or "",
            })
            tmp = VOCAB + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=1)
            os.replace(tmp, VOCAB)   # never leave a half-written vocab file behind
    return jsonify({"ok": True, "n": len(read_vocab())})

@app.route("/api/vocab/remove", methods=["POST"])
def vocab_remove():
    w = ((request.get_json(silent=True) or {}).get("word") or "").strip().lower()
    with _VLOCK:
        items = [x for x in read_vocab() if x.get("word", "").lower() != w]
        with open(VOCAB, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
    return jsonify({"ok": True, "n": len(items)})

# ---------------------------------------------------------------- lifecycle
@app.route("/api/ping")
def ping():
    return jsonify({"ok": True, "app": IDENT})

@app.route("/api/quit", methods=["POST"])
def quit_app():
    threading.Timer(0.4, lambda: os._exit(0)).start()
    return jsonify({"ok": True})

def existing_instance():
    """Return the port of a live instance, or None.

    A raw socket check first: probing 20 closed ports over HTTP used to burn the
    full timeout on each one and cost 12 seconds of startup.
    """
    ports = []
    try:
        with open(PORTFILE) as f:
            ports.append(int(f.read().strip()))
    except Exception:
        pass
    ports += [p for p in range(8712, 8722) if p not in ports]
    for p in ports:
        s = socket.socket()
        s.settimeout(0.08)
        try:
            s.connect(("127.0.0.1", p))
        except Exception:
            continue
        finally:
            s.close()
        try:
            # bypass any system proxy: 127.0.0.1 through a corporate proxy fails
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open("http://127.0.0.1:%d/api/ping" % p, timeout=0.6) as r:
                if json.loads(r.read().decode()).get("app") == IDENT:
                    return p
        except Exception:
            continue
    return None

def free_port():
    for p in range(8712, 8722):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except Exception:
            continue
        finally:
            s.close()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p

def main():
    quiet = bool(os.environ.get("NO_BROWSER"))     # automated checks drive their own browser
    old = existing_instance()
    if old:
        if not quiet:
            webbrowser.open("http://127.0.0.1:%d/" % old)
        return
    port = int(os.environ.get("TCF_PORT") or 0) or free_port()
    try:
        with open(PORTFILE, "w") as f:
            f.write(str(port))
    except Exception:
        pass
    url = "http://127.0.0.1:%d/" % port
    if not quiet:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    from waitress import serve
    serve(app, host="127.0.0.1", port=port, threads=8, _quiet=True)

if __name__ == "__main__":
    main()
