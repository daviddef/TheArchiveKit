#!/usr/bin/env python3
"""The end-to-end test all seven archives share.

Every check here exists because the thing it tests actually broke on a LIVE
site at least once. None of them reads the source: they read site/dist, which
is the only thing a visitor ever sees, and which is where all three of the
worst failures were invisible from the source.

  links        a hand-written href rotted when a slug changed          (73 dead on Defranceski)
  anchors      a #fragment pointed at a section that had been renamed
  contents     a page promising a contents list quietly grew a section it did not list
  searchindex  search shipped broken on THREE archives at once: the index
               lived in src/data and the shared component fetches
               /searchindex.json, so the page loaded and found nothing
  ring         an archive linked to itself, or dropped a sibling
  evidence     the five confidence words drifted to nine across the seven sites
  counter      the visit counter rendered "0times read" — Astro strips the
               whitespace between two adjacent spans
  titles       a page shipped with no <title> and was unfindable
  images       an <img src> pointed at nothing

Usage:  python3 checkarchive.py [--dist site/dist] [--base /TheX] [--strict]
Exit 1 on any failure, so it can gate a deploy.
"""
import os, re, sys, json, html, argparse, collections

CANON = {"documented", "probable", "inferred", "family", "disputed"}
RING = ["TheDefranceski", "TheFalco", "TheBooyzen", "TheDArcy",
        "TheBlazevic", "TheMazza", "TheLerena"]
ASSET = (".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".svg", ".xml", ".ico",
         ".webp", ".json", ".pdf", ".txt", ".gif", ".avif", ".woff", ".woff2", ".mp4")


def fingerprint(dist):
    """Cheap signature of the whole tree: name and size of every file.

    These repositories are worked on by several sessions at once, and
    `astro build` empties dist/ before it refills it. A check that reads a
    half-written dist reports hundreds of missing images that are simply not
    copied yet — which is how this harness first lied to its author. So the
    tree is fingerprinted before and after, and a run that straddles a build
    is thrown away rather than reported.
    """
    out = []
    for root, _, files in os.walk(dist):
        for f in files:
            try:
                out.append((os.path.join(root, f), os.path.getsize(os.path.join(root, f))))
            except OSError:
                out.append((os.path.join(root, f), -1))
    return sorted(out)


def load(dist):
    """Every built page, as (url-path, raw html)."""
    out = {}
    for root, _, files in os.walk(dist):
        for f in files:
            if not f.endswith(".html"):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, dist).replace(os.sep, "/")
            url = "/" + rel[:-len("index.html")] if rel.endswith("index.html") else "/" + rel
            out[url.rstrip("/") or "/"] = open(p, encoding="utf-8", errors="replace").read()
    return out


def text_of(src):
    src = re.sub(r"<script.*?</script>|<style.*?</style>", " ", src, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", src))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="site/dist")
    ap.add_argument("--base", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="treat advisory checks as failures too")
    a = ap.parse_args()

    if not os.path.isdir(a.dist):
        print(f"checkarchive: no {a.dist} — build first")
        return 1

    base = a.base
    if base is None:
        cfg = os.path.join(os.path.dirname(os.path.abspath(a.dist.rstrip("/"))),
                           "astro.config.mjs")
        m = re.search(r"base:\s*['\"]([^'\"]+)", open(cfg, encoding="utf-8").read()) \
            if os.path.exists(cfg) else None
        base = m.group(1) if m else ""
    base = "/" + base.strip("/") if base.strip("/") else ""

    before = fingerprint(a.dist)
    pages = load(a.dist)
    # A test that passes on an empty directory is worse than no test.
    if len(pages) < 5:
        print(f"checkarchive: only {len(pages)} page(s) under {a.dist} — "
              f"the build is either unfinished or in progress. Refusing to pass.")
        return 1

    fail, warn = [], []
    F = lambda c, w, d: fail.append((c, w, d))
    W = lambda c, w, d: warn.append((c, w, d))

    # every id on every page, for anchor resolution
    ids = {u: set(re.findall(r'\bid="([^"]+)"', s)) for u, s in pages.items()}

    def exists(path):
        p = path.rstrip("/") or "/"
        if p in pages:
            return True
        fs = os.path.join(a.dist, path.lstrip("/"))
        return os.path.exists(fs) or os.path.exists(fs.rstrip("/") + "/index.html")

    # ---- links, anchors, images -------------------------------------------
    for url, src in pages.items():
        body = re.sub(r"<script.*?</script>", " ", src, flags=re.S | re.I)
        for href in re.findall(r'href="([^"]*)"', body):
            if not href or href[0] in "#?" or "${" in href or "'" in href:
                continue
            if re.match(r"^(https?:|mailto:|tel:|data:|//)", href):
                continue
            if not href.startswith("/"):
                continue
            path, _, frag = href.partition("#")
            path = path.partition("?")[0]          # /register/?q=X is a real page
            if not path:
                continue
            if base and not path.startswith(base + "/") and path.rstrip("/") != base:
                F("links", url, f"{href} — outside the base {base}")
                continue
            rel = path[len(base):] or "/"
            if rel.lower().rstrip("/").endswith(ASSET):
                if not os.path.exists(os.path.join(a.dist, rel.strip("/"))):
                    F("links", url, f"{href} — asset not built")
                continue
            if not exists(rel):
                F("links", url, f"{href} — no such page")
            elif frag:
                tgt = (rel.rstrip("/") or "/")
                if tgt in ids and frag not in ids[tgt]:
                    F("anchors", url, f"{href} — #{frag} not on that page")
        for s in re.findall(r'<img[^>]+src="([^"]+)"', body):
            if s.startswith("data:") or re.match(r"^(https?:)?//", s) or not s.startswith("/"):
                continue
            q = s.partition("?")[0][len(base):].strip("/")
            if not os.path.exists(os.path.join(a.dist, q)):
                F("images", url, f"{s} — not built")

    # ---- contents-list guard ----------------------------------------------
    for url, src in pages.items():
        if 'id="contents"' not in src:
            continue
        listed = set(re.findall(r'href="#([^"]+)"', src))
        for h in re.findall(r'<h2[^>]*\bid="([^"]+)"', src):
            if h != "contents" and h not in listed:
                F("contents", url, f'section #{h} is not in the contents list')

    # ---- the search index --------------------------------------------------
    sidx = os.path.join(a.dist, "searchindex.json")
    uses_search = any("searchindex.json" in s for s in pages.values())
    if uses_search:
        if not os.path.exists(sidx):
            F("searchindex", "/search/", "the page fetches /searchindex.json and it was not published")
        else:
            try:
                rows = json.load(open(sidx, encoding="utf-8"))
                rows = rows if isinstance(rows, list) else rows.get("rows", [])
                if not rows:
                    F("searchindex", "/searchindex.json", "published but empty")
                else:
                    bad, sample = 0, None
                    for r in rows:
                        h = (r.get("h") or r.get("href") or "") if isinstance(r, dict) else ""
                        # /register/?q=Aaron+Wakefield is the register page with a
                        # filter, not a page of its own. Strip the query first.
                        h = h.partition("#")[0].partition("?")[0]
                        if not h.startswith("/"):
                            continue
                        if not exists(h[len(base):] if h.startswith(base) else h):
                            bad += 1
                            sample = sample or (r.get("h") or h)
                    if bad:
                        F("searchindex", "/searchindex.json",
                          f"{bad} of {len(rows)} rows point at pages that were not built, "
                          f"e.g. {sample}")
            except Exception as e:
                F("searchindex", "/searchindex.json", f"not valid JSON — {e}")

    # ---- the sibling ring --------------------------------------------------
    # Only <a href> counts. A canonical tag, an og:url and the sitemap all name
    # the site's own address quite properly, and counting those reported every
    # archive as "linking to itself".
    me = base.strip("/")
    linked = set()
    for src in pages.values():
        for m in re.findall(r'<a\b[^>]*href="https://daviddef\.github\.io/(The\w+)', src):
            linked.add(m)
    if me in RING:
        missing = [x for x in RING if x != me and x not in linked]
        if missing:
            W("ring", "(site)", "never links to " + ", ".join(missing))
        if me in linked:
            W("ring", "(site)", f"links to itself ({me})")

    # ---- the confidence vocabulary ----------------------------------------
    words = collections.Counter()
    for src in pages.values():
        for m in re.findall(r'class="[^"]*\bev\b[^"]*"[^>]*>\s*([A-Za-z ]{3,20}?)\s*<', src):
            words[m.strip().lower()] += 1
        for m in re.findall(r'data-(?:ev|level)="([^"]+)"', src):
            words[m.strip().lower()] += 1
    off = {w: n for w, n in words.items() if w and w not in CANON}
    if off:
        W("evidence", "(site)", "non-canonical confidence words: " +
          ", ".join(f"{w}×{n}" for w, n in sorted(off.items(), key=lambda x: -x[1])[:8]))

    # ---- the visit counter -------------------------------------------------
    # This check was wrong the first time and could never have fired: it looked
    # for a NUMBER welded to its label, and at build time the number is still a
    # placeholder — the real one arrives over fetch. So it passed on all seven
    # while every one of them shipped "—times read". Check the MARKUP instead:
    # two adjacent spans with no whitespace and no CSS gap between them.
    for url, src in pages.items():
        for m in re.finditer(r'<span[^>]*\bvc-n\b[^>]*>.*?</span>(\s*)<span[^>]*\bvc-l\b', src):
            if m.group(1) == "":
                has_gap = re.search(r'\.vc-l[^{,]*\{[^}]*(?:margin-left|padding-left|gap)\s*:',
                                    src) is not None
                if not has_gap:
                    F("counter", url,
                      "the count and its label are adjacent spans with no whitespace and no CSS "
                      "gap — this renders as \"1,234times read\"")
            break

    # ---- titles ------------------------------------------------------------
    for url, src in pages.items():
        m = re.search(r"<title[^>]*>(.*?)</title>", src, re.S | re.I)
        if not m or not m.group(1).strip():
            F("titles", url, "no <title>")

    # ---- sitemap -----------------------------------------------------------
    sm = os.path.join(a.dist, "sitemap.xml")
    rb = os.path.join(a.dist, "robots.txt")
    # robots.txt names a sitemap. If it is not there, every crawler that reads
    # robots first asks for a file that 404s, and nothing else here would
    # notice: the old check simply skipped when the file was absent. It goes
    # absent easily — a bare `astro build` empties dist and does not run the
    # generator, so any build that is not `npm run build` ships without one.
    if os.path.exists(rb) and not os.path.exists(sm):
        if re.search(r"(?im)^\s*Sitemap:", open(rb, encoding="utf-8").read()):
            F("sitemap", "robots.txt",
              "robots.txt points at sitemap.xml and no sitemap.xml was built "
              "(a bare `astro build` skips the generator — run `npm run build`)")
    if os.path.exists(sm):
        urls = re.findall(r"<loc>([^<]+)</loc>", open(sm, encoding="utf-8").read())
        dead = [u for u in urls
                if not exists(re.sub(r"^https?://[^/]+", "", u)[len(base):] or "/")]
        if dead:
            F("sitemap", "sitemap.xml", f"{len(dead)} of {len(urls)} urls are not built, e.g. {dead[0]}")
        noidx = [u for u, s in pages.items() if re.search(r'name="robots"[^>]*noindex', s)]
        leaked = [u for u in noidx
                  if any(x.rstrip("/").endswith(base + u.rstrip("/")) for x in urls)]
        if leaked:
            F("sitemap", "sitemap.xml", f"{len(leaked)} noindex page(s) are listed, e.g. {leaked[0]}")

    # ---- did the build move under us? --------------------------------------
    if fingerprint(a.dist) != before:
        print(f"checkarchive: {a.dist} changed while this ran — another build is in "
              f"flight. Results would be noise, so nothing is reported. Re-run when "
              f"the build is finished.")
        return 1

    # ---- report ------------------------------------------------------------
    if a.strict:
        fail, warn = fail + warn, []
    by = collections.Counter(c for c, _, _ in fail)
    for cat in sorted(by):
        rows = [x for x in fail if x[0] == cat]
        print(f"  FAIL  {cat:<12} {len(rows)}")
        for _, w, d in rows[:6]:
            print(f"          {w}  →  {d}")
        if len(rows) > 6:
            print(f"          … and {len(rows) - 6} more")
    for c, w, d in warn:
        print(f"  warn  {c:<12} {w}  →  {d}")
    if not fail:
        print(f"  ok    {len(pages)} pages, {sum(len(v) for v in ids.values())} ids — "
              f"links, anchors, contents, search, titles, sitemap all clean"
              + (f" ({len(warn)} advisory)" if warn else ""))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
