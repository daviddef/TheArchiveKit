#!/usr/bin/env python3
"""One board for the whole estate, built from the archives rather than typed.

The reason there were seven documents is that each was written by hand to answer
one question on one day, and a hand-written board is out of date the moment
somebody else commits. This reads every archive's worklist.json and emits the
single page — so the board cannot disagree with the archives, because it IS the
archives.

  python3 worklist_rollup.py --root /path/to/Projects --out board.html
  open board.html

Emits a COMPLETE page, not a fragment. It used to emit a fragment that somebody
then wrapped by hand, which meant the board only existed when two steps were run
in the right order by the one person who knew about them — the same failure it
was written to end.
"""
import os, re, sys, json, glob, html, argparse, datetime

STATE = {
    "running": ("Running", "#1E5F8C", "a machine or a person is at it now"),
    "next":    ("Next",    "#E9A020", "ready to start"),
    "blocked": ("Blocked", "#B04A16", "waiting on a person or an institution"),
    "done":    ("Done",    "#12703F", "finished and published"),
    "struck":  ("Struck",  "#7A7A7A", "founded on a mistake, kept rather than deleted"),
}
ORDER = ["blocked", "running", "next", "done", "struck"]
E = lambda s: html.escape(str(s or ""))

PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Estate Board</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Libre+Franklin:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{--paper:#FAF8F3;--panel:#FFF;--panel-2:#F2EDE2;--ink:#1D1B16;--ink-2:#514A3E;--ink-3:#857C6C;
--rule:#DED6C6;--accent:#1F5C6B;--bad:#9B3319;
--serif:"EB Garamond",Georgia,serif;--sans:"Libre Franklin",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#171613;--panel:#1F1D19;--panel-2:#26241F;
--ink:#F0EADF;--ink-2:#C3BAAA;--ink-3:#8E8474;--rule:#36322B;--accent:#6FB3C0;--bad:#E0755A}}
:root[data-theme="dark"]{--paper:#171613;--panel:#1F1D19;--panel-2:#26241F;--ink:#F0EADF;--ink-2:#C3BAAA;
--ink-3:#8E8474;--rule:#36322B;--accent:#6FB3C0;--bad:#E0755A}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.56;margin:0}
.wrap{max-width:900px;margin:0 auto;padding:0 24px}
header.top{border-bottom:2px solid var(--ink);padding:46px 0 22px}
.eyebrow{font-size:11.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-3);margin:0 0 14px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(34px,6vw,54px);line-height:1.05;margin:0 0 14px}
h1 em{font-style:italic;color:var(--accent)}
.standfirst{font-size:18.5px;color:var(--ink-2);margin:0;max-width:64ch}
h2{font-family:var(--serif);font-weight:600;font-size:clamp(23px,3.2vw,30px);margin:44px 0 6px;
padding-bottom:9px;border-bottom:1.5px solid var(--ink)}
h3{font-family:var(--mono);font-size:11.5px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;
color:var(--ink-2);margin:26px 0 10px}
h3 .c{color:var(--ink-3);font-weight:400;margin-left:6px}
p{margin:0 0 13px;max-width:70ch}
strong,b{font-weight:600;color:var(--ink)}
.tally{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));border:1px solid var(--rule);
border-radius:5px;overflow:hidden;margin:24px 0}
.tal{padding:13px 15px;border-right:1px solid var(--rule);background:var(--panel)}
.tal:last-child{border-right:0}
.tal .n{font-family:var(--serif);font-size:30px;font-weight:600;line-height:1}
.tal .l{font-size:12px;color:var(--ink-3);margin-top:5px;display:block}
.one{border-left:3px solid var(--rule);background:var(--panel);padding:11px 15px;margin-bottom:11px;border-radius:0 3px 3px 0}
.lab{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)}
.what{margin:7px 0 0;font-size:16.5px;font-weight:600;line-height:1.35}
.note-p{margin-top:5px;font-size:14.5px;color:var(--ink-2);line-height:1.6;max-width:70ch}
.note{border-left:3px solid var(--accent);background:var(--panel);padding:13px 17px;margin:20px 0;max-width:70ch}
.note.bad{border-left-color:var(--bad)}
ul.done{margin:0 0 18px;padding-left:20px;max-width:70ch}
ul.done li{font-size:14.5px;color:var(--ink-2);margin-bottom:5px}
ul.done li.struck{text-decoration:line-through;color:var(--ink-3)}
.m{font-family:var(--mono);font-size:.85em;background:var(--panel-2);padding:1px 5px;border-radius:3px}
footer{margin-top:50px;border-top:2px solid var(--ink);padding:18px 0 54px;font-family:var(--mono);font-size:12px;color:var(--ink-3)}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style></head><body>
<header class="top"><div class="wrap">
<h1>The estate board,<br><em>and nothing else</em></h1>
<p class="standfirst">Every archive keeps one work list. This reads all of them and is generated, so
it cannot disagree with the archives &mdash; it is the archives. Edit the lists, not this page.</p>
</div></header>
<section><div class="wrap">
"""
PAGE_FOOT = """</div></section>
<footer><div class="wrap"><p>Rebuild with
<span class="m">python3 kit/tools/worklist_rollup.py --root . --out board.html</span></p></div></footer>
</body></html>
"""



def md(s):
    s = E(s)
    s = re.sub(r'\[([^\]]+)\]\(([^)]*)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    return re.sub(r'«([^»]+)»', r'<em>«\1»</em>', s)


def load(root):
    out = []
    # the kit carries the estate's own list: gates, shared components, and the
    # items that are nobody's archive but everybody's problem
    kp = os.path.join(root, "Archive Kit", "worklist.json")
    if os.path.exists(kp):
        try:
            out.append(("the kit & estate", (json.load(open(kp, encoding="utf-8")) or {}).get("rows") or [], None))
        except Exception as e:
            out.append(("the kit & estate", None, str(e)))
    for p in sorted(glob.glob(os.path.join(root, "*", "site", "src", "data", "worklist.json"))):
        name = os.path.relpath(p, root).split(os.sep)[0].replace(" Family", "")
        try:
            w = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            out.append((name, None, str(e))); continue
        out.append((name, w.get("rows") or [], None))
    missing = []
    for d in sorted(glob.glob(os.path.join(root, "*", "site"))):
        name = os.path.relpath(d, root).split(os.sep)[0]
        if not os.path.exists(os.path.join(d, "src", "data", "worklist.json")):
            missing.append(name.replace(" Family", ""))
    return out, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="board.html")
    a = ap.parse_args()
    archives, missing = load(a.root)

    rows = []
    for name, rs, err in archives:
        for r in (rs or []):
            rows.append({**r, "archive": name})

    def key(r):
        return (ORDER.index(r.get("state")) if r.get("state") in ORDER else 9,
                r.get("archive", ""), r.get("n") or 0)
    rows.sort(key=key)
    openrows = [r for r in rows if r.get("state") in ("blocked", "running", "next")]

    who = {}
    for r in openrows:
        who.setdefault((r.get("owner") or "nobody named").strip(), []).append(r)

    P = []
    P.append("<!-- generated by worklist_rollup.py — edit the archives, not this -->")
    P.append('<p class="eyebrow">The estate board · generated %s</p>'
             % datetime.date.today().isoformat())
    P.append("<div class='tally'>")
    for k in ORDER:
        n = sum(1 for r in rows if r.get("state") == k)
        if n:
            P.append("<div class='tal'><div class='n' style='color:%s'>%d</div>"
                     "<span class='l'>%s</span></div>" % (STATE[k][1], n, STATE[k][0].lower()))
    P.append("</div>")

    if missing:
        P.append("<div class='note bad'><b>%d of %d archives keep no work list yet.</b> %s. "
                 "Until they do, this board cannot show what they are carrying — and that is the "
                 "whole failure it exists to end.</div>"
                 % (len(missing), len(missing) + len(archives), E(", ".join(missing))))

    P.append("<h2>Open, by who has to move it</h2>")
    for owner in sorted(who, key=lambda o: (-len(who[o]), o)):
        P.append("<h3>%s <span class='c'>%d</span></h3>" % (E(owner), len(who[owner])))
        for r in who[owner]:
            lab, col, mean = STATE.get(r.get("state"), STATE["next"])
            P.append("<div class='one' style='border-left-color:%s'>"
                     "<div class='lab'><b style='color:%s'>%s</b> · %s%s</div>"
                     "<p class='what'>%s</p>%s</div>"
                     % (col, col, lab, E(r["archive"]),
                        " · raised " + E(r["since"]) if r.get("since") else "",
                        E(r.get("what")),
                        "<div class='note-p'>%s</div>" % md(r.get("note")) if r.get("note") else ""))

    P.append("<h2>Appendix — what is finished</h2>")
    for name, rs, err in archives:
        fin = [r for r in (rs or []) if r.get("state") in ("done", "struck")]
        if not fin:
            continue
        P.append("<h3>%s <span class='c'>%d</span></h3><ul class='done'>" % (E(name), len(fin)))
        for r in fin:
            P.append("<li%s>%s</li>" % (" class='struck'" if r.get("state") == "struck" else "",
                                        E(r.get("what"))))
        P.append("</ul>")
    open(a.out, "w", encoding="utf-8").write(PAGE_HEAD + "\n".join(P) + PAGE_FOOT)
    print("  %d archives, %d rows, %d open, %d without a list → %s"
          % (len(archives), len(rows), len(openrows), len(missing), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
