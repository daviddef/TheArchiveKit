#!/usr/bin/env python3
"""Write sitemap.xml and robots.txt from what was actually built.

Generated from the HTML rather than from the route list on purpose: several of
these archives publish person pages for living relatives with
<meta name="robots" content="noindex">, and a sitemap built from routes would
hand exactly those pages to search engines. This reads each built file and
skips anything that noindexes itself, so the sitemap can never disagree with
the privacy rule the pages already state.
"""
import os, re, sys, json, datetime, subprocess, functools, argparse
import os.path as _p, sys as _sys
_sys.path.insert(0, _p.dirname(_p.abspath(__file__)))
import outdir as _outdir  # ARCHIVE_OUT beats --dist; see kit/tools/outdir.py


_ap = argparse.ArgumentParser()
# THE ODD ONE OUT UNTIL NOW. checkarchive, checkliving and checksources all
# take --dist; this computed site/dist and took no arguments at all, so an
# archive building into a directory of its own got its pages in one place and
# its sitemap in another — and then check:kit refused, correctly, with
# "robots.txt points at sitemap.xml and no sitemap.xml was built".
#
# Asked for by the Booyzen session, which had measured it before asking and
# was straight about the weight: seven archives use this tool, only one sets
# outDir, so nothing is broken in the field today. It is a capability none of
# the seven has, and the first to want it hits a wall in a shared file.
# Default "dist" leaves the other six byte-identical, because none passes it.
_ap.add_argument("--dist", default="dist",
                 help="where the pages were built, relative to the site directory")
_args = _ap.parse_args()

_args.dist = _outdir.resolve(_args.dist)
here = os.getcwd()                      # run from the site directory
site = here if os.path.basename(here) == "site" else os.path.join(here, "site")
dist = _args.dist if os.path.isabs(_args.dist) else os.path.join(site, _args.dist)
cfg = open(os.path.join(site, "astro.config.mjs"), encoding="utf-8").read()

origin = re.search(r"site:\s*['\"]([^'\"]+)", cfg).group(1).rstrip("/")
base = re.search(r"base:\s*['\"]([^'\"]+)", cfg)
base = base.group(1).rstrip("/") if base else ""

NOINDEX = re.compile(r'name=["\']robots["\'][^>]*noindex', re.I)
urls, skipped = [], 0
for dp, _, fns in os.walk(dist):
    for fn in fns:
        if fn != "index.html":
            continue
        p = os.path.join(dp, fn)
        html = open(p, encoding="utf-8", errors="ignore").read()
        if NOINDEX.search(html[:4000]):
            skipped += 1
            continue
        if "http-equiv=\"refresh\"" in html[:400]:   # redirect stubs
            skipped += 1
            continue
        rel = os.path.relpath(dp, dist).replace(os.sep, "/")
        path = "" if rel == "." else rel + "/"
        urls.append((f"{origin}{base}/{path}", path))

urls.sort()

# ---- lastmod ---------------------------------------------------------------
# It used to be today's date on every URL, every build — which tells a crawler
# that all 10,000 pages changed this morning and, after a week of that, teaches
# it to ignore the field. The truth is in git: when the page's own source last
# changed. Pages with no single source file (the dynamic routes) fall back to
# the last commit that touched the archive at all.
def _git(args, default=""):
    try:
        return subprocess.run(["git"] + args, cwd=site, capture_output=True,
                              text=True, timeout=20).stdout.strip() or default
    except Exception:
        return default

REPO_DATE = _git(["log", "-1", "--format=%cs"], datetime.date.today().isoformat())

@functools.lru_cache(maxsize=None)
def _date_for(src):
    return _git(["log", "-1", "--format=%cs", "--", src], REPO_DATE)

def lastmod(path):
    """path is the url path under the base, e.g. "people/x/" or "" for home."""
    stem = (path or "").strip("/")
    for cand in ([ "src/pages/index.astro" ] if not stem else
                 [f"src/pages/{stem}.astro", f"src/pages/{stem}/index.astro"]):
        if os.path.exists(os.path.join(site, cand)):
            return _date_for(cand)
    return REPO_DATE

body = "\n".join(
    f"  <url><loc>{u}</loc><lastmod>{lastmod(path)}</lastmod></url>" for u, path in urls)
open(os.path.join(dist, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    f"{body}\n</urlset>\n")

robots = os.path.join(site, "public", "robots.txt")
if not os.path.exists(robots):
    os.makedirs(os.path.dirname(robots), exist_ok=True)
    open(robots, "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\nSitemap: {origin}{base}/sitemap.xml\n")
# and copy whatever robots.txt exists into dist, since public/ was already copied
print(f"sitemap: {len(urls)} urls, {skipped} withheld (noindex or redirect)")
