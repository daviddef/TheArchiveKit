#!/usr/bin/env python3
"""The whole site is one book: every page is placed, every page says where it sits and what comes next.

    python3 checkbook.py --dist dist --book src/data/book.json        (run from the site directory)

WHAT IT REFUSES (kit/lib/book.js holds the rules; this file reads the BUILT pages and holds them to the same cases):
  unplaced   a built page that is not a chapter, not covered by `inherit`, and not listed in `outside`
  dead       a chapter (or a part opener) in book.json that has no built page
  twice      the same path in book.json more than once, or two parts with one id, or a part with no chapters
  head       a built page without the running head, or whose head names a different part, position, reference, Previous or Next than the book
  foot       a built page whose Previous / Next differ from the book's order (an inherited page must link back instead)
  stub       a redirect stub (a tiny page that only sends the reader on) whose target is not built; stubs are otherwise set aside
  empty      nothing built, or a book with fewer than two parts: a check that examined nothing has not passed

A page that is outside the book on purpose is listed in book.json "outside", so a page nobody placed fails the build.
Prints what it examined, never a person's name or date.
"""
import os
import re
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(p):
    s = str(p if p is not None else "/").split("#")[0].split("?")[0]
    if not s.startswith("/"):
        s = "/" + s
    if not s.endswith("/") and not re.search(r"\.[a-z0-9]+$", s, re.I):
        s += "/"
    return s


def opener_path(part):
    return "/part/%s/" % part["id"]


def flatten(book):
    out = []
    for k, c in enumerate((book.get("front") or {}).get("chapters", []) or []):
        out.append({"path": norm(c["path"]), "title": c.get("title", ""), "kind": "front", "part": None, "ref": "F.%d" % (k + 1)})
    for i, part in enumerate(book.get("parts") or []):
        num = part.get("numeral") or str(i + 1)
        out.append({"path": opener_path(part), "title": part.get("title", ""), "kind": "opener", "part": i, "ref": num})
        for k, c in enumerate(part.get("chapters") or []):
            out.append({"path": norm(c["path"]), "title": c.get("title", ""), "kind": "chapter", "part": i, "ref": "%s.%d" % (num, k + 1)})
    return out


def locate(book, path):
    p = norm(path)
    entries = flatten(book)
    total = len(entries)
    parts = book.get("parts") or []
    idx = next((i for i, e in enumerate(entries) if e["path"] == p), -1)
    part_of = lambda e: parts[e["part"]] if e["part"] is not None else None
    if idx >= 0:
        e = entries[idx]
        return {"entry": e, "n": idx + 1, "total": total, "prev": entries[idx - 1] if idx > 0 else None,
                "next": entries[idx + 1] if idx + 1 < total else None, "part": part_of(e), "inherited": False}
    if p == "/contents/":
        return {"outside": True}
    if p in [norm(x) for x in (book.get("outside") or [])]:
        return {"outside": True}
    inh = book.get("inherit") or {}
    for pre in sorted((norm(k) for k in inh), key=len, reverse=True):
        if p.startswith(pre) and p != pre:
            key = next(k for k in inh if norm(k) == pre)
            target = norm(inh[key])
            j = next((i for i, e in enumerate(entries) if e["path"] == target), -1)
            if j >= 0:
                e = entries[j]
                return {"entry": e, "n": j + 1, "total": total, "prev": None, "next": None, "part": part_of(e), "inherited": True, "via": pre}
    return None


def pages_of(dist):
    out = {}
    for d, ds, fs in os.walk(dist):
        ds[:] = [x for x in ds if x not in ("node_modules", "_astro", ".git")]
        if "index.html" in fs:
            rel = os.path.relpath(d, dist).replace(os.sep, "/")
            url = "/" if rel == "." else "/" + rel + "/"
            out[url] = os.path.join(d, "index.html")
    return out


STUB_BYTES = 1500


def stub_target(html):
    """A redirect stub is a tiny page that does nothing but send the reader on: under STUB_BYTES with a meta refresh.
    Returns its target (possibly empty) or None when the page is not a stub."""
    if len(html) >= STUB_BYTES:
        return None
    m = re.search(r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]*>', html, re.I)
    if not m:
        return None
    u = re.search(r'url=([^"\'>\s]+)', m.group(0), re.I)
    return u.group(1) if u else ""


def attr(html, name):
    m = re.search(r'data-book-%s="([^"]*)"' % name, html)
    return m.group(1) if m else None


def check(book, dist):
    fails = []
    parts = book.get("parts") or []
    if len(parts) < 2:
        return ["the book has %d part(s): refusing to pass on a book with nothing in it" % len(parts)], {}
    pages = pages_of(dist)
    pages.pop("/404/", None)
    if not pages:
        return ["no built page under %s: nothing was examined" % dist], {}
    # Redirect stubs (a retired address that only sends the reader on) are not chapters: set them aside, but each must
    # lead somewhere that is built, so a dead stub still fails.
    stubs = {}
    for url in list(pages):
        if url == "/contents/":
            continue
        t = stub_target(open(pages[url], encoding="utf-8", errors="replace").read())
        if t is not None:
            stubs[url] = t
            del pages[url]
    for url, t in sorted(stubs.items()):
        if re.match(r"^[a-z][a-z0-9+.-]*:|^//", t, re.I):
            continue  # an absolute address (another site): out of this check's reach
        tp = norm(t) if t.startswith("/") else norm(os.path.normpath(os.path.join(url, t)).replace(os.sep, "/"))
        if tp not in pages and tp not in stubs and not os.path.exists(os.path.join(dist, tp.strip("/"))):
            fails.append("stub: %s redirects to %s, which is not built" % (url, tp))
    if not pages:
        return ["no built page under %s: nothing was examined" % dist], {}
    entries = flatten(book)
    seen = {}
    for e in entries:
        seen[e["path"]] = seen.get(e["path"], 0) + 1
    for p, n in seen.items():
        if n > 1:
            fails.append("twice: %s is in the book %d times" % (p, n))
    ids = [p["id"] for p in parts]
    for i in set(ids):
        if ids.count(i) > 1:
            fails.append("twice: part id '%s' is used more than once" % i)
    for p in parts:
        if not (p.get("chapters") or []):
            fails.append("twice: part '%s' has no chapters" % p["id"])
    if "/contents/" not in pages:
        fails.append("dead: /contents/ has no built page (the book's table of contents)")
    for e in entries:
        if e["path"] not in pages:
            fails.append("dead: %s (%s) is in the book and has no built page" % (e["path"], e["kind"]))
    unplaced, inherited, outside, checked = [], 0, 0, 0
    for url, f in sorted(pages.items()):
        loc = locate(book, url)
        if loc is None:
            unplaced.append(url)
            continue
        if loc.get("outside"):
            outside += 1
            continue
        checked += 1
        inherited += 1 if loc["inherited"] else 0
        html = open(f, encoding="utf-8", errors="replace").read()
        part = attr(html, "part")
        want_part = loc["part"]["id"] if loc["part"] else "front"
        if part is None:
            fails.append("head: %s has no running head" % url)
            continue
        if part != want_part:
            fails.append("head: %s says part '%s', the book says '%s'" % (url, part, want_part))
        if attr(html, "n") != str(loc["n"]):
            fails.append("head: %s says position %s, the book says %d" % (url, attr(html, "n"), loc["n"]))
        if attr(html, "ref") != loc["entry"]["ref"]:
            fails.append("head: %s says reference %s, the book says %s" % (url, attr(html, "ref"), loc["entry"]["ref"]))
        wp = loc["prev"]["path"] if loc["prev"] else None
        wn = loc["next"]["path"] if loc["next"] else None
        if attr(html, "hprev") != wp:
            fails.append("head: %s links Previous to %s in the running head, the book says %s" % (url, attr(html, "hprev"), wp))
        if attr(html, "hnext") != wn:
            fails.append("head: %s links Next to %s in the running head, the book says %s" % (url, attr(html, "hnext"), wn))
        if loc["inherited"]:
            if attr(html, "inherited") != loc["entry"]["path"]:
                fails.append("head: %s does not name its chapter %s" % (url, loc["entry"]["path"]))
        prev, nxt, back = (re.search(r'data-book-%s="([^"]*)"' % k, html) for k in ("prev", "next", "back"))
        got = lambda m: m.group(1) if m else None
        wp = loc["prev"]["path"] if loc["prev"] else None
        wn = loc["next"]["path"] if loc["next"] else None
        if got(prev) != wp:
            fails.append("foot: %s links Previous to %s, the book says %s" % (url, got(prev), wp))
        if got(nxt) != wn:
            fails.append("foot: %s links Next to %s, the book says %s" % (url, got(nxt), wn))
        if loc["inherited"] and got(back) != loc["entry"]["path"]:
            fails.append("foot: %s does not link back to its chapter %s" % (url, loc["entry"]["path"]))
    if unplaced:
        fails.append("unplaced: %d built page(s) are not in the book (add them to a part, to `inherit`, or to `outside`): %s%s"
                     % (len(unplaced), ", ".join(unplaced[:12]), " ..." if len(unplaced) > 12 else ""))
    summary = {"pages": len(pages), "chapters": sum(1 for e in entries if e["kind"] != "opener"), "openers": sum(1 for e in entries if e["kind"] == "opener"),
               "parts": len(parts), "inherited": inherited, "outside": outside, "checked": checked, "stubs": len(stubs)}
    return fails, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--book", default="src/data/book.json")
    a = ap.parse_args()
    out = os.environ.get("ARCHIVE_OUT")
    dist = os.path.join(os.path.dirname(a.dist) or ".", out) if out and a.dist == "dist" else a.dist
    if not os.path.exists(a.book):
        print("checkbook: not run (no %s)" % a.book)
        return 2
    book = json.load(open(a.book, encoding="utf-8"))
    fails, s = check(book, dist)
    if fails:
        print("checkbook: FAIL (%d)" % len(fails))
        for f in fails[:40]:
            print("  - " + f)
        if len(fails) > 40:
            print("  ... and %d more" % (len(fails) - 40))
        if s:
            print("  examined: %(pages)d built pages, %(parts)d parts, %(chapters)d chapters and %(openers)d openers in the book" % s)
        return 1
    print("checkbook: ok. %(pages)d built pages: %(checked)d in the book (%(inherited)d by their chapter), %(outside)d outside on purpose, %(stubs)d redirect stubs set aside; "
          "%(parts)d parts, %(chapters)d chapters, %(openers)d openers; every head and every Previous/Next matches the book's order." % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
