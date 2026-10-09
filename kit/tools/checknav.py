#!/usr/bin/env python3
"""Does this archive's BUILT Evidence menu say what the estate means by Evidence?

Eight archives, eight hand-written menus, 122 entries, 9 to 25 per archive, and
five labels common to all of them. The menu canon of 15 September fixed the
order of the groups and one label per shared route; it never said what Evidence
contains, so each archive filled it with whatever it had built. This reads
`data/evidence-menu.json`, which now says, and compares it with what a reader
actually gets.

IT READS THE BUILD, NOT THE LAYOUT. A menu is whatever the browser is handed.
The layout is a template that several sessions edit at once, and a check of the
template grades the intention. So this opens `index.html` in the built tree
(ARCHIVE_OUT beats --dist, as everywhere in this kit: see outdir.py), finds the
`topnav`, and takes the links inside the group called Evidence.

IT READS THIS ARCHIVE ONLY. The first version of `checkpages.py` read other
repositories, and on a CI runner, where there is only one, it broke the deploy
of every archive it was wired into within eleven minutes. Nothing here leaves
the build directory it is given.

ADVISORY BY DEFAULT. It reports and exits 0, because eight archives do not meet
the canon yet and a gate that fails everywhere is a gate that gets removed.
`--strict` exits 1 on any departure. It exits 2, in either mode, when it could
not SEE a menu at all: a check that finds nothing because it looked in the
wrong place has not found that nothing is wrong (a page that is not built, a
build that is half-written, a layout that no longer has a `topnav`).

WHAT IT SAYS ABOUT EACH ENTRY IN THE EVIDENCE MENU
  core      one of the eight every archive carries
  optional  Documents or Gallery, allowed where the archive holds any
  fold      does the same job as a core page under another name (the fold
            table in the data file) — named, so the work is visible
  local     the archive's own page, which belongs in Investigations once it
            leaves Evidence

AND ABOUT THE INVESTIGATIONS GROUP
  A fold page parked there is reported as PENDING, not as a departure: it is
  where the page should wait, and the work of merging it is still owed.

AND ABOUT EACH CORE PAGE
  absent    the page is not built at all, so the archive has nothing to list
            (this is the real gap: Falco and Mazza have no Errands)
  unlinked  the page is built but not in the Evidence menu
  label     it is there under a different label than the estate's
"""

import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outdir  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CANON_FILE = os.path.join(HERE, "..", "data", "evidence-menu.json")


def load_canon(path=CANON_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def norm(route):
    """'/x', 'x/' and '/x/' are the same page. '' is the root."""
    r = "/" + (route or "").strip("/")
    return r if r == "/" else r + "/"


def read_menu(index_html):
    """[(group, [(href, label), ...]), ...] from the built topnav, or None."""
    nav = re.search(r'<nav[^>]*class="[^"]*topnav[^"]*".*?</nav>', index_html, re.S)
    if not nav:
        return None
    groups = []
    for m in re.finditer(r"<details[^>]*>\s*<summary[^>]*>(.*?)</summary>(.*?)</details>",
                         nav.group(0), re.S):
        name = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        links = []
        for a in re.finditer(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', m.group(2), re.S):
            links.append((html.unescape(a.group(1)),
                          html.unescape(re.sub(r"<[^>]+>", "", a.group(2))).strip()))
        groups.append((name, links))
    return groups


def base_of(groups):
    """The site's base path, taken from the first link of the first group."""
    for _, links in groups:
        if links:
            return "/" + links[0][0].strip("/") if links[0][0].strip("/") else ""
    return ""


def page_built(dist, route):
    r = route.strip("/")
    return (os.path.exists(os.path.join(dist, r, "index.html"))
            or os.path.exists(os.path.join(dist, r + ".html")))


def audit(dist, canon):
    """A dict describing how this build's Evidence menu departs from the canon.

    Raises FileNotFoundError / ValueError when the menu cannot be SEEN — which
    is a different answer from 'it conforms'."""
    idx = os.path.join(dist, "index.html")
    if not os.path.exists(idx):
        raise FileNotFoundError("no index.html under %s" % dist)
    with open(idx, encoding="utf-8") as f:
        groups = read_menu(f.read())
    if not groups:
        raise ValueError("no <nav class=\"topnav\"> in %s/index.html" % dist)
    ev = next((links for name, links in groups if name == canon["group"]), None)
    if ev is None:
        raise ValueError("no group called %s (groups: %s)"
                         % (canon["group"], ", ".join(n for n, _ in groups)))
    if not ev:
        raise ValueError("the %s group is empty — that is a menu that did not render, "
                         "not an archive with no evidence" % canon["group"])

    base = base_of(groups)
    over = next((links for name, links in groups
                 if name == canon["overflow"]["label"]), [])
    core = {c["key"]: c for c in canon["core"]}
    opt = {c["key"]: c for c in canon["optional"]}
    alias = {norm(k): v for k, v in canon["aliases"].items()}
    fold_of = {}
    for target, keys in canon["folds"].items():
        if target == "note":
            continue
        for k in keys:
            fold_of[norm("/" + k)] = target

    entries = []
    for href, label in ev:
        route = norm(href[len(base):] if base and href.startswith(base) else href)
        key = alias.get(route) or next((k for k, c in {**core, **opt}.items()
                                        if norm(c["route"]) == route), None)
        if key in core:
            kind = "core"
        elif key in opt:
            kind = "optional"
        elif route in fold_of:
            kind, key = "fold", fold_of[route]
        else:
            kind, key = "local", None
        entries.append(dict(route=route, label=label, kind=kind, key=key,
                            aliased=route in alias))

    present = {e["key"] for e in entries if e["kind"] in ("core", "optional")}
    problems = {"absent": [], "unlinked": [], "label": [], "order": [], "aliased": []}
    for c in canon["core"]:
        if c["key"] in present:
            continue
        # the page may still be there under an alias route
        built = page_built(dist, c["route"]) or any(
            page_built(dist, a) for a, k in alias.items() if k == c["key"])
        (problems["unlinked"] if built else problems["absent"]).append(c["key"])
    for e in entries:
        if e["kind"] in ("core", "optional"):
            want = (core.get(e["key"]) or opt[e["key"]])["label"]
            if e["label"] != want:
                problems["label"].append((e["route"], e["label"], want))
            if e["aliased"]:
                problems["aliased"].append((e["route"], e["key"]))
    want_order = [c["key"] for c in canon["core"]]
    got = [e["key"] for e in entries if e["kind"] == "core"]
    if got != sorted(got, key=want_order.index):
        problems["order"] = got
    # core entries should lead, optional follow, nothing else interleaved
    kinds = [e["kind"] for e in entries]
    first_other = next((i for i, k in enumerate(kinds) if k != "core"), len(kinds))
    interleaved = any(k == "core" for k in kinds[first_other:])
    extras = [e for e in entries if e["kind"] in ("fold", "local")]
    # Pages that do a core page's job but have been moved out of Evidence into
    # the overflow group. That is the right interim home and not a departure, but
    # it is work that is not finished, so it is named on every run.
    parked = []
    for href, label in over:
        route = norm(href[len(base):] if base and href.startswith(base) else href)
        if route in fold_of:
            parked.append(dict(route=route, label=label, key=fold_of[route]))
    ok = not (problems["absent"] or problems["unlinked"] or problems["label"]
              or problems["order"] or interleaved or extras)
    return dict(dist=dist, base=base, entries=entries, problems=problems,
                interleaved=interleaved, extras=extras, parked=parked, ok=ok,
                total=len(entries), overflow=len(over))


def render(a, canon):
    p = a["problems"]
    out = ["  menu   %d entries in %s  (canon: %d core + up to %d optional)"
           % (a["total"], canon["group"], len(canon["core"]), len(canon["optional"]))]
    for e in a["entries"]:
        tag = {"core": "core", "optional": "optional",
               "fold": "fold -> %s" % e["key"], "local": "local"}[e["kind"]]
        out.append("    %-34s %-22s %s" % (e["label"][:34], e["route"], tag))
    if p["absent"]:
        out.append("  ABSENT   not built at all: " + ", ".join(p["absent"]))
    if p["unlinked"]:
        out.append("  UNLINKED built but not in the menu: " + ", ".join(p["unlinked"]))
    for r, have, want in p["label"]:
        out.append("  LABEL    %s says %r, the estate says %r" % (r, have, want))
    for r, k in p["aliased"]:
        out.append("  ROUTE    %s stands in for the canon route of %r" % (r, k))
    if p["order"]:
        out.append("  ORDER    core entries appear as %s" % " > ".join(p["order"]))
    if a["interleaved"]:
        out.append("  ORDER    a core entry comes after a non-core one")
    if a["extras"]:
        folds = [e for e in a["extras"] if e["kind"] == "fold"]
        local = [e for e in a["extras"] if e["kind"] == "local"]
        if folds:
            out.append("  FOLD     %d page(s) do a core page's job: %s" % (
                len(folds), "; ".join("%s -> %s" % (e["label"], e["key"]) for e in folds)))
        if local:
            out.append("  LOCAL    %d page(s) to move to %s: %s" % (
                len(local), canon["overflow"]["label"], "; ".join(e["label"] for e in local)))
    if a["overflow"]:
        out.append("  %s  %d page(s) of the archive's own" % (canon["overflow"]["label"], a["overflow"]))
    if a["parked"]:
        out.append("  PENDING  %d fold(s) parked in %s, not yet merged: %s" % (
            len(a["parked"]), canon["overflow"]["label"],
            "; ".join("%s -> %s" % (e["label"], e["key"]) for e in a["parked"])))
    out.append("  result  " + ("conforms" if a["ok"] else "departs from the canon")
               + ("  (folds pending)" if a["ok"] and a["parked"] else ""))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="site/dist")
    ap.add_argument("--canon", default=CANON_FILE)
    ap.add_argument("--strict", action="store_true", help="exit 1 on any departure")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    dist = outdir.resolve(args.dist)
    canon = load_canon(args.canon)
    before = outdir.fingerprint(dist) if os.path.isdir(dist) else None
    try:
        a = audit(dist, canon)
    except (FileNotFoundError, ValueError) as e:
        print("  --    checknav  COULD NOT SEE A MENU: %s" % e)
        print("        That is not a pass. Build first, or point ARCHIVE_OUT at the build you made.")
        return 2
    if before is not None and outdir.settled(dist, before, "checknav"):
        return 2
    n = outdir.note(dist)
    if args.json:
        print(json.dumps(a, indent=1, ensure_ascii=False))
    else:
        if n:
            print(n)
        print(render(a, canon))
    return 0 if (a["ok"] or not args.strict) else 1


if __name__ == "__main__":
    sys.exit(main())
