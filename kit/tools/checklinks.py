#!/usr/bin/env python3
"""The gate behind autolink.py: a name the archive can resolve must be linked, and the number may not get worse.

    python3 checklinks.py --dist dist --index names.json [--living living.json] [--scope main]
                          [--floor .linkfloor.json] [--write-floor] [--new-page-max 3]
                          [--allow-prefix /people/ --allow-prefix /who/] [--min-words 2]

WHAT IT COUNTS. For every built page it counts the places where a resolvable name (the same index, the same matching rules
and the same sections as autolink.py) is written in running text and the page has NO link to that person in that section:
exactly the links an autolink run would still add. A page that autolink has just processed counts 0. A page of a
build that never ran autolink counts what is missing, and that count is the floor an archive starts from.

THE RATCHET (.linkfloor.json, committed): one number per page, and a page may only go DOWN.
  rise          a page's count is above its floor                                          fail
  new page      a page that is not in the floor and counts more than --new-page-max (3)    fail
  --write-floor writes the floor from this build: every page's number becomes the lower of its old floor and its
                current count, and a page not yet in the floor enters at its current count (this is how an archive
                starts, and how a new page is accepted on purpose). It REFUSES to write while any page has risen,
                or a stale or living link exists. A floor goes up only when a person edits the file, in a commit
                that says why.
  below floor   a page whose count fell is a pass; the summary says so, and --write-floor locks it in.

WHAT ELSE IT FAILS
  stale         a link carrying data-autolink whose address is not in the index (a person was merged, removed or hidden
                after the pass ran), or whose text is no longer a name or alias of that address
  living        a link carrying data-autolink to an address, or with the text, that the living list holds
  refusal       (exit 2) an empty build, no page with the scope element, an empty index, an index entry the living list
                also holds, an address outside the public prefixes: "a check that examined nothing has not passed"

Prints counts, never a person's name. A page under a public prefix (/people/, /who/) is reported in a group, not by
address, because its address is a name.

EXIT CODES: 0 pass; 1 fail; 2 refused.
"""
import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autolink as al  # noqa: E402
import outdir as _outdir  # noqa: E402

FLOOR_VERSION = 1


def count_build(dist, idx, scope):
    """{page url: (missing, mentions)} for pages that have the scope element, plus the autolink links found, plus counters."""
    pages = {}
    links = []          # (page url, href normalized, folded text)
    n_html = 0
    for p in al.html_pages(dist):
        n_html += 1
        sc = al.scan_html(al.read_page(p), idx, scope)
        if not sc.scope_seen:
            continue
        url = al.page_url(dist, p)
        pages[url] = (len(sc.inserts), sc.mentions)
        for l in sc.autolinks:
            links.append((url, l["href"], l["text"]))
    return pages, links, n_html


def load_floor(path):
    if not path or not os.path.exists(path):
        return None
    try:
        d = json.load(open(path, encoding="utf-8"))
        pg = d["pages"]
        assert isinstance(pg, dict) and all(isinstance(k, str) and isinstance(v, int) and v >= 0 for k, v in pg.items())
        return pg
    except (OSError, ValueError, KeyError, AssertionError, TypeError):
        raise al.Refusal("the floor file %s is not a valid {\"pages\": {url: count}} file" % path)


def evaluate(counts, links, idx, floor, new_page_max, living_names, living_urls):
    """Returns a list of (kind, page url or None, detail) for every violation, and a summary dict."""
    v = []
    rises = new_bad = below = 0
    for url, (n, _m) in sorted(counts.items()):
        if floor is not None and url in floor:
            if n > floor[url]:
                rises += 1
                v.append(("rise", url, "%d unlinked resolvable names, floor %d" % (n, floor[url])))
            elif n < floor[url]:
                below += 1
        else:
            if n > new_page_max:
                new_bad += 1
                v.append(("new", url, "a page not in the floor has %d unlinked resolvable names (allowed %d)" % (n, new_page_max)))
    stale = mismatch = living = 0
    for (url, href, text) in links:
        if href in living_urls or al.name_key(text) in living_names:
            living += 1
            v.append(("living", url, "a data-autolink link to a living or held-out person"))
            continue
        if href not in idx.urls:
            stale += 1
            v.append(("stale", url, "a data-autolink link whose address is not in the index"))
            continue
        if al.name_key(text) not in idx.names_by_url.get(href, set()):
            mismatch += 1
            v.append(("stale", url, "a data-autolink link whose text is no longer a name of its address"))
    summary = {"rises": rises, "new_bad": new_bad, "below": below, "stale": stale, "mismatch": mismatch, "living": living}
    return v, summary


def label(url, prefixes):
    for p in prefixes:
        if url and url.startswith(p):
            return p + "*"
    return url


def render(violations, prefixes, limit=30):
    masked, plain = {}, []
    for (kind, url, detail) in violations:
        lab = label(url, prefixes) if url else "(index)"
        if lab.endswith("*"):
            masked.setdefault((kind, lab), []).append(detail)
        else:
            plain.append("%s: %s %s" % (kind, lab, detail))
    lines = plain + ["%s: %d page(s) under %s (an address that is a name is not printed)" % (k, len(d), lab[:-1])
                     for (k, lab), d in sorted(masked.items())]
    out = ["  - " + l for l in lines[:limit]]
    if len(lines) > limit:
        out.append("  ... and %d more" % (len(lines) - limit))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="The gate behind autolink.py (see the docstring).")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--index", required=True)
    ap.add_argument("--living")
    ap.add_argument("--scope", default="main")
    ap.add_argument("--floor", default=".linkfloor.json")
    ap.add_argument("--write-floor", action="store_true")
    ap.add_argument("--new-page-max", type=int, default=3)
    ap.add_argument("--allow-prefix", action="append", default=[])
    ap.add_argument("--min-words", type=int, default=2)
    a = ap.parse_args(argv)
    dist = _outdir.resolve(a.dist)
    try:
        idx, prefixes = al.prepare(a)
        if not os.path.isdir(dist) or not al.html_pages(dist):
            raise al.Refusal("no built page under %s: nothing was examined" % dist)
        floor = load_floor(a.floor)
    except al.Refusal as e:
        print("checklinks: REFUSED. %s" % e)
        return 2
    before = _outdir.fingerprint(dist)
    counts, links, n_html = count_build(dist, idx, a.scope)
    if _outdir.settled(dist, before, "checklinks"):
        return 2
    if not counts:
        print("checklinks: REFUSED. none of the %d pages has a <%s>: wrong --scope, or nothing was built" % (n_html, a.scope))
        return 2
    note = _outdir.note(dist)
    if note:
        print(note)
    viol, s = evaluate(counts, links, idx, floor, a.new_page_max, idx.living_names, idx.living_urls)
    total = sum(n for n, _ in counts.values())
    mentions = sum(m for _, m in counts.values())
    pages_missing = sum(1 for n, _ in counts.values() if n)
    base = ("%d pages, %d with <%s>; %d resolvable names unlinked in their section on %d pages (of %d resolvable mentions); "
            "%d data-autolink links checked; floor %s"
            % (n_html, len(counts), a.scope, total, pages_missing, mentions, len(links),
               ("%d pages" % len(floor)) if floor is not None else "absent"))
    if a.write_floor:
        viol = [x for x in viol if x[0] != "new"]      # a page not yet in the floor enters it at its current count
        if viol:
            print("checklinks: FLOOR NOT WRITTEN, %d problem(s) first:" % len(viol))
            print("\n".join(render(viol, prefixes)))
            print("  " + base)
            return 1
        new = {}
        old = floor or {}
        for url, (n, _m) in counts.items():
            new[url] = min(old[url], n) if url in old else n
        dropped = len([u for u in old if u not in counts])
        with open(a.floor, "w", encoding="utf-8") as fh:
            fh.write('{\n "version": %d,\n "note": "Per page: unlinked resolvable names. A page may only go down. Written by checklinks.py --write-floor; raise a number only by hand, in a commit that says why.",\n "pages": {\n' % FLOOR_VERSION)
            fh.write(",\n".join('  %s: %d' % (json.dumps(k, ensure_ascii=False), new[k]) for k in sorted(new)))
            fh.write("\n }\n}\n")
        print("checklinks: floor written to %s: %d pages (%d new, %d lowered, %d no longer built and dropped); total now %d. %s"
              % (a.floor, len(new), len([u for u in new if u not in old]), len([u for u in new if u in old and new[u] < old[u]]),
                 dropped, sum(new.values()), base))
        return 0
    if viol:
        print("checklinks: FAIL (%d)" % len(viol))
        print("\n".join(render(viol, prefixes)))
        print("  " + base)
        return 1
    extra = ""
    if floor is not None and s["below"]:
        extra = "; %d page(s) are below their floor: run with --write-floor to lock the gain in" % s["below"]
    if floor is None:
        extra = "; no floor file, so every page was held to --new-page-max %d" % a.new_page_max
    print("checklinks: ok. " + base + extra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
