#!/usr/bin/env python3
"""Can a reader reach the sources, and does the page still know what they are?

Two questions nothing in this estate was asking, both raised on 21 September
2026 and both answered badly when measured.

REACHABLE, or said not to be. Of 208 sources across the six archives that hold theirs as data,
58 carried a link to the source itself and all 58 belonged to one archive.
Falco 0 of 26, Mazza 0 of 25, Booyzen 0 of 42, D'Arcy 0 of 18, Blazevic 0 of
12. Two archives do link, but inward, at their own pages — navigation, not a
source. A sources page whose sources cannot be reached is asking to be taken
on trust, which is the one thing a sources page exists not to do.

CURRENT. Commits to each archive's data since its sources page was last
touched: Lerena 302, Defranceski 121, Luwinski 93, Blazevic 64, Booyzen 57,
D'Arcy 29. A commit count is weak evidence on its own, so it was checked
against the data: Lerena's records cite 228 distinct sources and its page
names 54. The ones missing are not vague — `ark:/61903/1:1:XXXX-XXX` is a
specific record that has been read, is cited on a person's page, and has
never reached the sources page. A sources page is the one page in an archive
that goes stale SILENTLY, because nothing breaks when it does.

WHY THIS REPORTS AND DOES NOT FAIL, at least at first. A gate that fails 150
of 208 rows on the day it lands is a gate every archive turns off. So the
count is a RATCHET: --max-unreachable N fails only when the number goes UP.
Each archive starts at whatever it has today and the number can only come
down. The staleness half is reported and never fatal: a host can be used
once, in passing, for something that is genuinely not a source, and that
judgement belongs to the archive rather than to a regex.

WHAT THE SECOND HALF COUNTS, and two things it counted first and should not
have. A pass matching free text for source-shaped strings returned
"Argentina-South Africa relations." as a missing source. A pass matching
identifiers by shape — arks, film numbers, KAB and NAA references — returned
7,502 of them for Booyzen, every one real and not one of them a finding: a
sources page names COLLECTIONS, and no page should be expected to list 7,502
individual films. Both were wrong in the same way, which is the trap this
estate already has written down — a check that tests something else and
reports it as this.

What it counts instead is DOMAINS. Every host the archive links to anywhere
in its data, against the hosts its sources page names. A host the archive
uses and never declares is unambiguous, actionable — the fix is to add that
one line — and lands in the tens rather than the thousands. Measured on the
day it was written: Blazevic 17 of 17 undeclared, D'Arcy 58 of 58,
Defranceski 74 of 105, Lerena 11 of 17, Falco 3 of 5 including the Antenati
host it has a whole page about, Luwinski 0 of 5. Infrastructure hosts are
skipped, and an archive can skip more with --ignore.

    python3 checksources.py --root . [--max-unreachable N] [--quiet]
"""

import argparse, json, os, re, sys

# Shapes, measured rather than assumed. Seven archives, seven arrangements of
# the same rows, so the rows are found rather than declared.
ROW_PATHS = [
    lambda j: j if isinstance(j, list) else None,
    lambda j: j.get("rows") if isinstance(j, dict) else None,
    lambda j: j.get("recordSets") if isinstance(j, dict) else None,
    lambda j: [r for g in j.get("groups", []) for r in g.get("rows", [])]
              if isinstance(j, dict) and "groups" in j else None,
    lambda j: [r for s in j.get("sections", []) for r in s.get("rows", [])]
              if isinstance(j, dict) and "sections" in j else None,
]
URL_KEYS = ("url", "href", "link", "at", "site")   # Lerena calls it `link`
TITLE_KEYS = ("title", "t", "name", "source", "label")

# Hosts that are never a source: the page's own plumbing and this estate's
# own repositories. Everything else an archive links to is something it is
# standing on, and ought to say so.
INFRA = re.compile(r"(w3\.org|schema\.org|github|daviddef|localhost|example\.|"
                   r"creativecommons|openstreetmap|unpkg|jsdelivr|googleapis|gstatic)")


def rows_of(j):
    for f in ROW_PATHS:
        try:
            r = f(j)
        except Exception:
            continue
        if isinstance(r, list) and r and all(isinstance(x, (dict, list)) for x in r):
            return r
    return []


def first(row, keys):
    if isinstance(row, list):                    # Booyzen: a row IS its cells
        return " ".join(str(c.get("h", "")) for c in row if isinstance(c, dict))
    for k in keys:
        if row.get(k):
            return str(row[k])
    return ""


def url_of(row):
    """An EXTERNAL url is the source. An internal one is navigation, and the
       distinction is the whole finding — so they are never added together."""
    blob = first(row, URL_KEYS) or ""
    if blob.startswith("http"):
        return blob
    text = json.dumps(row, ensure_ascii=False)
    m = re.search(r'href=[\\"\']?(https?://[^\s"\'<>\\]+)', text)
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--data", default=None, help="sources.json; found under --root if omitted")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--max-unreachable", type=int, default=None,
                    help="ratchet: fail when more sources than this cannot be reached")
    ap.add_argument("--ignore", default=None,
                    help="regex of hosts that are not sources for this archive")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    # An archive does not have to call the file sources.json, and the first
    # version of this check assumed it did. Lerena keeps 121 sources in
    # sources-consulted.json, 38 of them already linked, and this tool
    # reported "nothing to check" and passed — which made the estate-wide
    # finding wrong, not merely incomplete. A check that cannot find its
    # subject must say so loudly; passing quietly is the worst thing it can do.
    CANDIDATES = ["sources.json", "sources-consulted.json", "bibliography.json"]
    path = a.data
    if not path:
        d = os.path.join(a.root, "src", "data")
        for c in CANDIDATES:
            if os.path.exists(os.path.join(d, c)):
                path = os.path.join(d, c)
                break
    if not path or not os.path.exists(path):
        found = sorted(f for f in (os.listdir(os.path.join(a.root, "src", "data"))
                                   if os.path.isdir(os.path.join(a.root, "src", "data")) else [])
                       if "source" in f or "biblio" in f)
        print("  FAIL  sources    no source list found under %s/src/data — looked for %s%s"
              % (a.root, ", ".join(CANDIDATES),
                 ("; did you mean " + ", ".join(found) + "?") if found else ""))
        return 1

    rows = rows_of(json.load(open(path, encoding="utf-8")))
    if not rows:
        print("  FAIL  sources    %s parsed, but no rows were found in it" % path)
        return 1

    # Three states, not two. A url means a reader can go and look. `held`
    # means the thing is paper in somebody's house and the row SAYS SO, which
    # is a different answer from a dead link and the only honest one for a
    # certificate issued by a comune in 2003. Counting those as failures
    # forever would mean the number could never reach zero, and a gate whose
    # target is unreachable is a gate people stop reading.
    reachable = [r for r in rows if url_of(r)]
    declared = [r for r in rows
                if not url_of(r) and isinstance(r, dict) and r.get("held")]
    unreachable = [r for r in rows if r not in reachable and r not in declared]
    n, tot = len(unreachable), len(rows)

    # Staleness: hosts the archive links to in its data that its sources page
    # has never heard of. Reported, never fatal — see the header.
    page = ""
    for p in (os.path.join(a.root, "src", "pages", "sources.astro"), path):
        if os.path.exists(p):
            page += open(p, encoding="utf-8").read()
    seen = ""
    data_dir = os.path.join(a.root, "src", "data")
    if os.path.isdir(data_dir):
        for fn in sorted(os.listdir(data_dir)):
            if fn.endswith(".json") and fn != "sources.json":
                try:
                    seen += open(os.path.join(data_dir, fn), encoding="utf-8").read()
                except Exception:
                    pass
    ignore = re.compile(a.ignore) if a.ignore else None
    used = {m.lower() for m in re.findall(r"https?://([A-Za-z0-9.\-]+)", seen)}
    used = {h for h in used if not INFRA.search(h) and not (ignore and ignore.search(h))}
    low = page.lower()
    missing = sorted(h for h in used
                     if h not in low and h.replace("www.", "") not in low)

    if not a.quiet:
        for r in unreachable[:12]:
            print("        no way to reach it — %s" % first(r, TITLE_KEYS)[:76])
        if len(unreachable) > 12:
            print("        ... and %d more" % (len(unreachable) - 12))
        for h in missing[:12]:
            print("        linked to in the data, named nowhere here — %s" % h)
        if len(missing) > 12:
            print("        ... and %d more" % (len(missing) - 12))

    tail = ("" if not missing else
            " · %d host(s) linked to in the data and named nowhere here" % len(missing))
    if a.max_unreachable is not None and n > a.max_unreachable:
        print("  FAIL  sources    %d of %d sources cannot be reached, and the ratchet is %d — "
              "this number may only go down%s" % (n, tot, a.max_unreachable, tail))
        return 1
    held = (" · %d held as paper and said to be" % len(declared)) if declared else ""
    if n:
        print("  ok    sources    %d of %d reachable%s, %d with no way to reach them%s"
              % (len(reachable), tot, held, n, tail))
    else:
        print("  ok    sources    every source reachable or accounted for — %d of %d "
              "linked%s%s" % (len(reachable), tot, held, tail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
