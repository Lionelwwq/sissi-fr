# -*- coding: utf-8 -*-
"""app.css. Two of these only show up on an older iPhone, which is exactly the phone
the whole opus→mp3 conversion was done for."""
import io, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
p = os.path.join(SRC, "app.css")
t = io.open(p, encoding="utf-8").read()

PAIRS = [
    # ---- color-mix() with no fallback ---------------------------------------
    # color-mix landed in Safari 16.2. Before that the whole `background` declaration
    # is invalid and dropped, so the sticky toolbar and the floating player bar are
    # FULLY TRANSPARENT and the chapter scrolls underneath them, text over text.
    # Also: Safari only understood -webkit-backdrop-filter until Safari 18, so the
    # frosted glass these rules assume has never actually rendered on her phone.
    (".topbar{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--card) 88%,transparent);\n"
     "        backdrop-filter:saturate(150%) blur(10px);border-bottom:1px solid var(--line);",
     ".topbar{position:sticky;top:0;z-index:20;background:var(--card);\n"
     "        background:color-mix(in srgb,var(--card) 88%,transparent);\n"
     "        -webkit-backdrop-filter:saturate(150%) blur(10px);\n"
     "        backdrop-filter:saturate(150%) blur(10px);border-bottom:1px solid var(--line);"),

    ("table.b-tab tbody tr:nth-child(even) td{background:color-mix(in srgb,var(--bg) 55%,transparent)}",
     "table.b-tab tbody tr:nth-child(even) td{background:var(--bg);\n"
     "  background:color-mix(in srgb,var(--bg) 55%,transparent)}"),

    ("        background:color-mix(in srgb,var(--card) 90%,transparent);\n"
     "        backdrop-filter:saturate(160%) blur(14px);",
     "        background:var(--card);\n"
     "        background:color-mix(in srgb,var(--card) 90%,transparent);\n"
     "        -webkit-backdrop-filter:saturate(160%) blur(14px);\n"
     "        backdrop-filter:saturate(160%) blur(14px);"),

    ("         background:var(--card);backdrop-filter:saturate(140%) blur(6px)}",
     "         background:var(--card);-webkit-backdrop-filter:saturate(140%) blur(6px);\n"
     "         backdrop-filter:saturate(140%) blur(6px)}"),

    # ---- the chapter she is reading was unreadable in the table of contents ----
    # .navitem.seen .t (0,2,1) beats the colour .navitem.on gives its children by
    # inheritance, so the current row was --muted on --accent: 1.35:1. And every
    # chapter she is on is also 'seen', so this was the normal state, not an edge case.
    (".navitem.seen .t{color:var(--muted)}",
     ".navitem.seen .t{color:var(--muted)}\n"
     "/* …but the row she is on is highlighted, and inheritance loses to the rule above */\n"
     ".navitem.on .t,.navitem.on.seen .t{color:#fff}\n"
     "body.dark .navitem.on .t,body.dark .navitem.on.seen .t{color:#0e1420}"),

    # ---- 背诵模式 could not be scrolled and overflowed short phones -------------
    # Measured at 375x600 (an iPhone 8 with Safari's bars): 13 of the cards stepped
    # through ran off both ends — the French she is meant to read was cut off above
    # the viewport and 会了 / 退出 sat below it, with nothing to scroll.
    (".fc{background:var(--card);border-radius:16px;max-width:660px;width:100%;padding:30px 32px;text-align:center;\n"
     "    box-shadow:0 20px 60px rgba(0,0,0,.4)}",
     ".fc{background:var(--card);border-radius:16px;max-width:660px;width:100%;padding:30px 32px;text-align:center;\n"
     "    box-shadow:0 20px 60px rgba(0,0,0,.4);\n"
     "    max-height:calc(100vh - 48px);max-height:calc(100dvh - 48px);overflow-y:auto;\n"
     "    -webkit-overflow-scrolling:touch}"),
    ("#fcwrap{position:fixed;inset:0;background:rgba(10,16,26,.86);z-index:200;display:flex;\n"
     "        align-items:center;justify-content:center;padding:24px}",
     "#fcwrap{position:fixed;top:0;right:0;bottom:0;left:0;inset:0;\n"
     "        background:rgba(10,16,26,.86);z-index:200;display:flex;\n"
     "        align-items:center;justify-content:center;padding:24px}"),

    # ---- a toast that explains a failure was painted under the card that caused it
    ("#toast{position:fixed;bottom:88px;left:50%;transform:translateX(-50%);background:#18202e;color:#fff;\n"
     "       padding:10px 20px;border-radius:11px;font-size:13.5px;z-index:300;opacity:0;",
     "#toast{position:fixed;bottom:88px;left:50%;transform:translateX(-50%);background:#18202e;color:#fff;\n"
     "       padding:10px 20px;border-radius:11px;font-size:13.5px;z-index:700;opacity:0;"),

    # ---- tap targets on the plan ---------------------------------------------
    (".dpck{flex:0 0 auto;width:26px;height:26px;border-radius:7px;border:1.5px solid var(--line);",
     ".dpck{flex:0 0 auto;width:38px;height:38px;border-radius:9px;border:1.5px solid var(--line);"),
]

for a, b in PAIRS:
    n = t.count(a)
    assert n == 1, ("expected 1 occurrence, found %d" % n, a[:90])
    t = t.replace(a, b)

# ---- rich() may now emit <s> <code> <sup> <sub>: give them somewhere to land ----
t += """
/* rich() now passes these through instead of printing the angle brackets at her.
   <code> is punctuation being talked about, <s> is a wrong form being crossed out —
   both carry the meaning of the sentence, so they have to actually look like that. */
.b-para code,.b-card code,li code,td code,.dl code,.pcard code,.wp-zh code{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.92em;
  background:var(--accent-soft);color:var(--ink);border:1px solid var(--line);
  border-radius:5px;padding:1px 5px;margin:0 1px}
s{text-decoration:line-through;text-decoration-color:#c2410c;text-decoration-thickness:2px;
  opacity:.8}
sup,sub{font-size:.7em;line-height:0}
"""

io.open(p, "w", encoding="utf-8", newline="\n").write(t)
print("patched app.css -", len(PAIRS), "edits + tag styles")
