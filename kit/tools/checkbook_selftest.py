#!/usr/bin/env python3
"""Prove checkbook.py can fail, and that it holds the same cases as kit/lib/book.js. Invented fixtures only.
    python3 kit/tools/checkbook_selftest.py"""
import os, sys, json, shutil, tempfile, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checkbook as cb
FIX = json.load(open(os.path.join(os.path.dirname(HERE), "data", "book-cases.json"), encoding="utf-8"))
BOOK = FIX["book"]
res = []
def case(label, ok, detail=""):
    res.append(bool(ok)); print("  %s  %s%s" % ("ok  " if ok else "FAIL", label, ("  [" + str(detail)[:150] + "]") if detail and not ok else ""))

def page(url, loc, drop=None):
    """A built page as the kit components emit it for `url`."""
    if loc is None or loc.get("outside"):
        return "<html><body>%s</body></html>" % url
    h = 'data-book-part="%s" data-book-n="%d" data-book-total="%d" data-book-ref="%s"' % (loc["part"]["id"] if loc["part"] else "front", loc["n"], loc["total"], loc["entry"]["ref"])
    if loc["inherited"]:
        h += ' data-book-inherited="%s"' % loc["entry"]["path"]
    f = ""
    if loc["prev"]: f += ' data-book-prev="%s"' % loc["prev"]["path"]
    if loc["next"]: f += ' data-book-next="%s"' % loc["next"]["path"]
    if loc["prev"]: h += ' data-book-hprev="%s"' % loc["prev"]["path"]
    if loc["next"]: h += ' data-book-hnext="%s"' % loc["next"]["path"]
    if loc["inherited"]: f += ' data-book-back="%s"' % loc["entry"]["path"]
    s = '<html><body><div class="bk-head" %s></div><nav class="bk-foot"%s></nav></body></html>' % (h, f)
    return drop(s) if drop else s

def build(root, book, urls, mutate=None):
    for u in urls:
        loc = cb.locate(book, u)
        html = page(u, loc)
        if mutate and u in mutate:
            html = mutate[u](html)
        d = os.path.join(root, u.strip("/")); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(html)

URLS = ["/", "/about/", "/part/one/", "/a/", "/b/", "/part/two/", "/c/", "/people/", "/people/x/", "/who/y/", "/search/", "/contents/"]
def run(book=None, urls=None, mutate=None):
    t = tempfile.mkdtemp(prefix="cbook-")
    try:
        b = book or BOOK
        build(t, b, urls if urls is not None else URLS, mutate)
        return cb.check(b, t)
    finally:
        shutil.rmtree(t, ignore_errors=True)

print("the shared cases (the same file kit/tools/book_logic.mjs holds book.js to)")
bad = []
for c in FIX["cases"]:
    r = cb.locate(BOOK, c["path"]); w = c["want"]
    if w.get("nowhere"): ok = r is None
    elif w.get("outside"): ok = bool(r and r.get("outside"))
    else:
        ok = bool(r and not r.get("outside") and r["entry"]["kind"] == w.get("kind", r["entry"]["kind"]) and r["n"] == w.get("n", r["n"])
                  and ("prev" not in w or (r["prev"]["path"] if r["prev"] else None) == w["prev"])
                  and ("next" not in w or (r["next"]["path"] if r["next"] else None) == w["next"])
                  and ("part" not in w or (r["part"]["id"] if r["part"] else None) == w["part"])
                  and ("ref" not in w or r["entry"]["ref"] == w["ref"])
                  and ("inherited" not in w or r["inherited"] == w["inherited"]) and ("via" not in w or r.get("via") == w["via"]))
    if not ok: bad.append(c["id"])
case("the Python placement agrees with the %d shared cases" % len(FIX["cases"]), not bad, bad)

print("a clean build")
f, s = run(); case("a book whose pages all carry the right head and foot passes", not f and s["checked"] == 10 and s["inherited"] == 2 and s["outside"] == 2 and s["stubs"] == 0, f)
STUB = '<html><head><meta http-equiv="refresh" content="0; url=%s"></head></html>'
print("redirect stubs and the outside list")
def with_stubs(stubs, urls=None):
    t = tempfile.mkdtemp(prefix="cbook-")
    try:
        build(t, BOOK, urls if urls is not None else URLS)
        for u, target in stubs.items():
            d = os.path.join(t, u.strip("/")); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "index.html"), "w").write(STUB % target)
        return cb.check(BOOK, t)
    finally:
        shutil.rmtree(t, ignore_errors=True)
f, s = with_stubs({"/old/": "/a/", "/people/gone/": "/people/"}); case("redirect stubs are set aside, not unplaced, even under an inherited prefix", not f and s["stubs"] == 2, f)
f, s = with_stubs({"/old/": "/nowhere-built/"}); case("a stub that leads to nothing built fails", any("stub: /old/" in x for x in f), f)
f, s = with_stubs({"/old/": "https://elsewhere.example/x/"}); case("a stub that leads to another site is set aside", not f, f)
f, s = run(urls=URLS + ["/people/private/"]); case("a page listed as outside stays outside under an inherited prefix", not f and s["outside"] == 3, f)
f, s = run(mutate={"/a/": lambda h: h.replace('data-book-hnext="/b/"', 'data-book-hnext="/c/"')}); case("a running head whose Next differs from the book fails", any("running head" in x and "/a/" in x for x in f), f)
f, s = run(mutate={"/a/": lambda h: h.replace(' data-book-hprev="/part/one/"', "")}); case("a running head with no Previous fails", any("running head" in x and "Previous" in x for x in f), f)
f, s = run(mutate={"/a/": lambda h: h.replace('data-book-ref="I.1"', 'data-book-ref="I.9"')}); case("a head with the wrong reference fails", any("reference" in x and "/a/" in x for x in f), f)
print("planted faults")
f, s = run(urls=URLS + ["/orphan/"]); case("a built page nobody placed fails", any("unplaced" in x and "/orphan/" in x for x in f), f)
f, s = run(urls=[u for u in URLS if u != "/b/"]); case("a chapter with no built page fails", any("dead: /b/" in x for x in f), f)
f, s = run(urls=[u for u in URLS if u != "/part/two/"]); case("a part opener with no built page fails", any("dead: /part/two/" in x for x in f), f)
f, s = run(urls=[u for u in URLS if u != "/contents/"]); case("a missing Contents page fails", any("dead: /contents/" in x for x in f), f)
f, s = run(mutate={"/a/": lambda h: h.replace('data-book-part="one" data-book-n="4" data-book-total="8"', "")}); case("a page with no running head fails", any("head: /a/" in x and "no running head" in x for x in f), f)
f, s = run(mutate={"/a/": lambda h: h.replace('data-book-part="one"', 'data-book-part="two"')}); case("a head naming the wrong part fails", any("head: /a/ says part" in x for x in f), f)
f, s = run(mutate={"/a/": lambda h: h.replace('data-book-n="4"', 'data-book-n="9"')}); case("a head with the wrong position fails", any("position" in x for x in f), f)
f, s = run(mutate={"/a/": lambda h: h.replace('data-book-next="/b/"', 'data-book-next="/c/"')}); case("a Next that skips a chapter fails", any("foot: /a/ links Next" in x for x in f), f)
f, s = run(mutate={"/a/": lambda h: h.replace(' data-book-prev="/part/one/"', "")}); case("a missing Previous fails", any("foot: /a/ links Previous" in x for x in f), f)
f, s = run(mutate={"/people/x/": lambda h: h.replace(' data-book-back="/people/"', "")}); case("an inherited page that does not link back fails", any("link back" in x or "does not link back" in x for x in f), f)
f, s = run(mutate={"/people/x/": lambda h: h.replace(' data-book-next="', ' data-book-next="/zzz/') if 'data-book-next' in h else h.replace('<nav class="bk-foot"', '<nav class="bk-foot" data-book-next="/zzz/"')}); case("an inherited page that gets a Next fails", any("people/x/" in x and "foot" in x for x in f), f)
dup = copy.deepcopy(BOOK); dup["parts"][1]["chapters"].append({"path": "/a/", "title": "A again"})
f, s = run(book=dup); case("the same path twice in the book fails", any("twice: /a/" in x for x in f), f)
dup = copy.deepcopy(BOOK); dup["parts"][1]["id"] = "one"
f, s = run(book=dup); case("two parts with one id fail", any("part id 'one'" in x for x in f), f)
dup = copy.deepcopy(BOOK); dup["parts"][1]["chapters"] = []
f, s = run(book=dup); case("a part with no chapters fails", any("no chapters" in x for x in f), f)
one = copy.deepcopy(BOOK); one["parts"] = one["parts"][:1]
f, s = run(book=one); case("a book with one part is refused", any("refusing" in x for x in f), f)
f, s = run(urls=[]); case("an empty build is refused, not passed", any("nothing was examined" in x for x in f), f)
f, s = run(book=BOOK, urls=URLS + ["/people/another/"]); case("a new person page is covered by its index with no edit to the book", not f, f)
bad = res.count(False)
print("\nall %d cases behave" % len(res) if not bad else "\n%d FAILED" % bad)
sys.exit(1 if bad else 0)
