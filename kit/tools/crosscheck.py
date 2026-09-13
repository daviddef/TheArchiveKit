#!/usr/bin/env python3
"""Read all seven archives at once and report where they disagree.

checkarchive.py asks "is this one site sound?". This asks the different
question the estate actually keeps failing: "do the seven still agree?" —
because every drift in this project has been invisible from inside a single
repository. The evidence ladder grew to nine words that way. The colours
collided that way. The search index forked five ways that way.

Nothing here is asserted. Every row is read out of the repositories: package
files, astro configs, built HTML, data files. Where a thing cannot be derived
it is reported as unknown rather than guessed.

Usage:  python3 crosscheck.py --root "/path/to/Projects" [--json out.json]
"""
import os, re, sys, json, glob, html, argparse, collections

SITES = [
    ("Defranceski", "Defranceski Family", "TheDefranceski"),
    ("Falco",       "Falco Family",       "TheFalco"),
    ("Booyzen",     "Booyzen Family",     "TheBooyzen"),
    ("D'Arcy",      "D'arcy Family",      "TheDArcy"),
    ("Blazevic",    "Blazevic Family",    "TheBlazevic"),
    ("Mazza",       "Mazza Family",       "TheMazza"),
    ("Lerena",      "Lerena Family",      "TheLerena"),
    ("Children",    "Our Family",         "Our-Family"),
]

SPINE = ["index", "direct-line", "people", "places", "timeline", "register",
         "sources", "method", "searched", "search", "open-questions",
         "corrections", "name", "trees", "who"]

CANON_EVIDENCE = ["documented", "probable", "inferred", "family", "disputed"]


def read(p, default=""):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return default


def jread(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def dist_sig(dist):
    """These repositories are rebuilt by other sessions while this runs, and
    `astro build` empties dist/ first. Anything read from dist has to be
    checked for having been read mid-build, or the report invents faults."""
    n = 0
    for rt, _, fs in os.walk(dist):
        n += len(fs)
    return n


def survey(root, key, folder, base):
    d = os.path.join(root, folder)
    site = os.path.join(d, "site")
    dist = os.path.join(site, "dist")
    sig0 = dist_sig(dist)
    r = {"key": key, "dir": folder, "base": base, "exists": os.path.isdir(site)}
    if not r["exists"]:
        return r

    pkg = jread(os.path.join(site, "package.json"), {}) or {}
    scripts = pkg.get("scripts", {})
    r["scripts"] = sorted(scripts)
    r["build"] = scripts.get("build", "")
    r["deps"] = sorted((pkg.get("dependencies") or {}))

    lock = read(os.path.join(site, "package-lock.json"))
    m = re.search(r'archive-kit"[^}]*?#([0-9a-f]{40})', lock, re.S)
    r["kit_pin"] = m.group(1)[:9] if m else None

    # which kit components does the source import?
    srcs = glob.glob(os.path.join(site, "src", "**", "*.astro"), recursive=True) + \
           glob.glob(os.path.join(site, "src", "**", "*.js"), recursive=True)
    kitc = collections.Counter()
    for f in srcs:
        for c in re.findall(r'@daviddef/archive-kit/(?:components|data|styles)/([\w.\-]+)', read(f)):
            kitc[c] += 1
    r["kit_uses"] = dict(sorted(kitc.items()))

    # pages actually built
    pages = set()
    for rt, _, fs in os.walk(dist):
        for f in fs:
            if f == "index.html":
                rel = os.path.relpath(rt, dist).replace(os.sep, "/")
                pages.add("index" if rel == "." else rel)
    r["built"] = len(pages)
    r["spine"] = {p: (p in pages) for p in SPINE}

    # top-level nav, read off the built home page
    home = read(os.path.join(dist, "index.html"))
    nav = re.search(r'<nav[^>]*class="[^"]*topnav[^"]*".*?</nav>', home, re.S)
    groups = []
    if nav:
        for g in re.findall(r'<summary[^>]*>(.*?)</summary>', nav.group(0), re.S):
            groups.append(html.unescape(re.sub(r"<[^>]+>", "", g)).strip())
    r["nav_groups"] = groups

    # evidence words actually rendered anywhere in the build
    words = collections.Counter()
    for rt, _, fs in os.walk(dist):
        for f in fs:
            if not f.endswith(".html"):
                continue
            s = read(os.path.join(rt, f))
            for w in re.findall(r'data-(?:ev|level)="([^"]+)"', s):
                words[w.strip().lower()] += 1
            for w in re.findall(r'class="[^"]*\bev\b[^"]*"[^>]*>\s*([A-Za-z ]{3,20}?)\s*<', s):
                words[w.strip().lower()] += 1
    r["evidence"] = dict(words.most_common())
    r["evidence_off"] = sorted(w for w in words if w and w not in CANON_EVIDENCE)

    # accent, fonts, tokens
    cfg = read(os.path.join(site, "astro.config.mjs"))
    r["astro_base"] = (re.search(r"base:\s*['\"]([^'\"]+)", cfg) or [None, None])[1]
    # The token sheet does not live in one place across the estate: two archives
    # keep it at src/styles/global.css and five at public/styles.css. That is
    # itself a finding, so look in both rather than papering over it.
    css_files = (glob.glob(os.path.join(site, "src", "**", "*.css"), recursive=True) +
                 glob.glob(os.path.join(site, "public", "**", "*.css"), recursive=True) +
                 glob.glob(os.path.join(site, "src", "layouts", "*.astro")))
    css = "\n".join(read(f) for f in css_files)
    r["css_home"] = sorted({os.path.relpath(f, site).replace(os.sep, "/")
                            for f in css_files if f.endswith(".css")})[:2]
    r["accent"] = (re.search(r"--accent:\s*([^;]+);", css) or [None, None])[1]
    r["fonts"] = sorted(set(re.findall(r"family=([A-Za-z+]+)", css + home)))
    r["tokens"] = sorted(set(re.findall(r"(--[a-z0-9\-]+):", css)))

    # search index
    si = jread(os.path.join(dist, "searchindex.json"))
    if isinstance(si, dict):
        si = si.get("rows", [])
    if isinstance(si, list) and si and isinstance(si[0], dict):
        r["search_rows"] = len(si)
        r["search_keys"] = sorted(si[0])
    else:
        r["search_rows"] = 0 if si is not None else None
        r["search_keys"] = None

    r["sitemap"] = len(re.findall(r"<loc>", read(os.path.join(dist, "sitemap.xml"))))
    r["counter"] = "vc-n" in home or any("vc-n" in read(f) for f in srcs[:400])
    r["noindex"] = sum(1 for rt, _, fs in os.walk(dist) for f in fs
                       if f.endswith(".html") and "noindex" in read(os.path.join(rt, f)))

    # sibling ring, from anchors only
    linked = set()
    for rt, _, fs in os.walk(dist):
        for f in fs:
            if f.endswith(".html"):
                for m2 in re.findall(r'<a\b[^>]*href="https://daviddef\.github\.io/(The\w+|Our-Family)',
                                     read(os.path.join(rt, f))):
                    linked.add(m2)
    r["ring"] = sorted(linked - {base})

    # local guards
    tools = os.path.join(d, "tools")
    r["guards"] = sorted(f for f in os.listdir(tools)
                         if re.search(r"check|drift|regen|consist", f)) if os.path.isdir(tools) else []
    r["living_decl"] = os.path.exists(os.path.join(site, "src", "data", "living.json"))

    # data files, for schema comparison
    dd = os.path.join(site, "src", "data")
    r["data_files"] = sorted(f for f in os.listdir(dd)) if os.path.isdir(dd) else []
    r["stale"] = (dist_sig(dist) != sig0)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/Claude/Projects"))
    ap.add_argument("--json")
    a = ap.parse_args()

    rows = [survey(a.root, k, f, b) for k, f, b in SITES]
    live = [r for r in rows if r.get("exists")]

    def line(label, fn, width=13):
        cells = []
        for r in live:
            try:
                v = fn(r)
            except Exception:
                v = "?"
            cells.append(str(v)[:width].ljust(width))
        print(f"  {label:<24}" + "".join(cells))

    print("\n" + "=" * 118)
    print("  CROSS-ARCHIVE CONSISTENCY".ljust(24) + "".join(r["key"][:13].ljust(13) for r in live))
    print("=" * 118)

    print("\n  ── shared kit")
    line("kit pinned", lambda r: r["kit_pin"] or "—")
    line("kit components used", lambda r: len(r["kit_uses"]))
    line("which", lambda r: ",".join(sorted(x.split(".")[0] for x in r["kit_uses"]))[:13])

    print("\n  ── build")
    line("build steps", lambda r: r["build"].count("&&") + 1)
    line("gates on check:kit", lambda r: "yes" if "check:kit" in r["build"] else "NO")
    line("gates on living", lambda r: "yes" if "check:living" in r["build"] else "—")
    line("local guards", lambda r: len(r["guards"]))

    if any(r.get("stale") for r in live):
        print("\n  !! dist changed while reading: " +
              ", ".join(r["key"] for r in live if r.get("stale")) +
              " — another build is in flight, so their dist-derived rows are unreliable")

    print("\n  ── shape")
    line("built pages", lambda r: r["built"])
    line("sitemap urls", lambda r: r["sitemap"])
    line("noindex pages", lambda r: r["noindex"])
    line("data files", lambda r: len(r["data_files"]))

    print("\n  ── the spine")
    for p in SPINE:
        line(f"/{p}/", lambda r, p=p: "yes" if r["spine"].get(p) else "MISSING")

    print("\n  ── navigation")
    line("nav groups", lambda r: len(r["nav_groups"]))
    mx = max((len(r["nav_groups"]) for r in live), default=0)
    for i in range(mx):
        line(f"  {i+1}.", lambda r, i=i: r["nav_groups"][i] if i < len(r["nav_groups"]) else "—")

    print("\n  ── vocabulary")
    line("evidence words", lambda r: len(r["evidence"]))
    line("off-canon", lambda r: ",".join(r["evidence_off"])[:13] if r["evidence_off"] else "—")

    print("\n  ── search & ring")
    line("search rows", lambda r: r["search_rows"] if r["search_rows"] is not None else "none")
    line("search keys", lambda r: ",".join(r["search_keys"]) if r["search_keys"] else "—")
    line("links to siblings", lambda r: len(r["ring"]))
    line("visit counter", lambda r: "yes" if r["counter"] else "NO")
    line("living declared", lambda r: "yes" if r["living_decl"] else "—")

    print("\n  ── identity")
    line("accent", lambda r: (r["accent"] or "—").strip())
    line("stylesheet home", lambda r: (r.get("css_home") or ["—"])[0].split("/")[-2:][0])
    line("astro base", lambda r: r["astro_base"] or "—")
    line("css tokens", lambda r: len(r["tokens"]))
    print()

    if a.json:
        json.dump(rows, open(a.json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"  full detail → {a.json}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
