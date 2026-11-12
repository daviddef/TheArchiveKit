#!/usr/bin/env python3
"""Prove checknav.py can fail, on fixtures, without touching a real build.

A gate that has only ever been seen passing has not been seen working. Each case
below builds a throwaway tree with ONE departure in it and asserts the checker
names exactly that departure — including the case where it must say it could not
see a menu at all, which is the failure a quiet gate hides.

The real function runs against synthetic DATA; nothing shipped is ever broken to
test it (see the note on testing tools on copies, not in place).

    python3 kit/tools/checknav_selftest.py
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checknav  # noqa: E402

CANON = checknav.load_canon()
BASE = "/TheFixture"
CORE = [(c["route"], c["label"]) for c in CANON["core"]]


def nav(evidence):
    links = "".join('<a href="%s%s" class>%s</a>' % (BASE, r, l) for r, l in evidence)
    return ('<nav class="topnav" aria-label="Main">'
            '<details class="menu"><summary>Start</summary><div class="panel">'
            '<a href="%s/" class>Home</a></div></details>'
            '<details class="menu"><summary>Evidence</summary><div class="panel">%s</div></details>'
            '</nav>') % (BASE, links)


def tree(evidence, build=None, raw=None):
    d = tempfile.mkdtemp(prefix="checknav-")
    with open(os.path.join(d, "index.html"), "w") as f:
        f.write(raw if raw is not None else "<html><body>%s</body></html>" % nav(evidence))
    for r in (build if build is not None else [r for r, _ in CORE]):
        p = os.path.join(d, r.strip("/"))
        os.makedirs(p, exist_ok=True)
        open(os.path.join(p, "index.html"), "w").write("<html></html>")
    return d


fails = []


def expect(name, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", name))
    if not cond:
        fails.append(name)


# 1. a conforming menu passes, with Documents and Gallery allowed after the core
d = tree(CORE + [("/documents/", "Documents"), ("/gallery/", "Gallery")],
         build=[r for r, _ in CORE] + ["/documents/", "/gallery/"])
a = checknav.audit(d, CANON)
expect("conforming menu (core + documents + gallery) passes", a["ok"] and a["total"] == 10)

# 2. a local page and a fold are both named, and as different things
d = tree(CORE + [("/photograph-these/", "Photograph these"), ("/the-stones/", "The Stones")])
a = checknav.audit(d, CANON)
kinds = {e["route"]: (e["kind"], e["key"]) for e in a["extras"]}
expect("a page that does errands' job is a FOLD into errands",
       kinds.get("/photograph-these/") == ("fold", "errands"))
expect("an archive's own page is LOCAL", kinds.get("/the-stones/") == ("local", None))
expect("extras make the menu depart", not a["ok"])

# 3. a core page that is not built is ABSENT; one that is built but unlisted is UNLINKED
without_errands = [x for x in CORE if x[0] != "/errands/"]
d = tree(without_errands, build=[r for r, _ in without_errands])
a = checknav.audit(d, CANON)
expect("a core page that does not exist is ABSENT, not unlinked",
       a["problems"]["absent"] == ["errands"] and not a["problems"]["unlinked"])
d = tree(without_errands)  # errands/index.html exists, menu omits it
a = checknav.audit(d, CANON)
expect("a core page that exists but is not in the menu is UNLINKED",
       a["problems"]["unlinked"] == ["errands"] and not a["problems"]["absent"])

# 4. label drift
drift = [(r, "What has been read" if r == "/searched/" else l) for r, l in CORE]
a = checknav.audit(tree(drift), CANON)
expect("a label that differs from the canon is reported with both strings",
       a["problems"]["label"] == [("/searched/", "What has been read", "What Has Been Read")])

# 5. order
swapped = CORE[:]
swapped[3], swapped[4] = swapped[4], swapped[3]
a = checknav.audit(tree(swapped), CANON)
expect("core entries out of canon order are reported", bool(a["problems"]["order"]) and not a["ok"])

# 6. an alias route counts as the page, and says so
al = [("/what-changed/" if r == "/changes/" else r, l) for r, l in CORE]
a = checknav.audit(tree(al, build=[r for r, _ in CORE if r != "/changes/"] + ["/what-changed/"]), CANON)
expect("/what-changed/ is recognised as changes, and flagged as an alias",
       a["problems"]["aliased"] == [("/what-changed/", "changes")] and not a["problems"]["absent"])

# 7. CANNOT SEE is not a pass
for label, d in (("no topnav at all", tree(None, raw="<html><body>no nav</body></html>")),
                 ("an empty Evidence group", tree([])),
                 ("no index.html", tempfile.mkdtemp(prefix="checknav-"))):
    try:
        checknav.audit(d, CANON)
        saw = False
    except (FileNotFoundError, ValueError):
        saw = True
    expect("%s raises instead of passing" % label, saw)
rc = checknav.main(["--dist", tempfile.mkdtemp(prefix="checknav-")])
expect("main() exits 2 when it could not see a menu", rc == 2)

# 7b. folds parked in Investigations conform, but are still named
def tree2(evidence, overflow):
    d = tree(evidence)
    links = "".join('<a href="%s%s" class>%s</a>' % (BASE, r, l) for r, l in overflow)
    idx = os.path.join(d, "index.html")
    h = open(idx).read().replace("</nav>",
        '<details class="menu"><summary>Investigations</summary><div class="panel">%s</div></details></nav>' % links)
    open(idx, "w").write(h)
    return d

a2 = checknav.audit(tree2(CORE, [("/photograph-these/", "Photograph these"), ("/the-stones/", "The Stones")]), CANON)
expect("a fold parked in Investigations does not fail the menu", a2["ok"])
expect("...but it is still named as pending", [p["key"] for p in a2["parked"]] == ["errands"])
expect("a local page in Investigations is not a pending fold", len(a2["parked"]) == 1 and a2["overflow"] == 2)
a3 = checknav.audit(tree2(CORE + [("/photograph-these/", "Photograph these")], []), CANON)
expect("the same fold left in Evidence still departs", not a3["ok"])

# 8. advisory vs strict
d = tree(CORE + [("/the-stones/", "The Stones")])
expect("advisory mode exits 0 on a departure", checknav.main(["--dist", d]) == 0)
expect("--strict exits 1 on the same departure", checknav.main(["--dist", d, "--strict"]) == 1)

# 9. THE RESEARCH CANON (12 November 2026): core pages in the order of the three groups, the archive's own pages allowed in the menu
RES = checknav.load_canon("research")
RCORE = [(c["route"], c["label"]) for c in RES["core"]]


def rtree(links, build=None):
    """A tree whose menu group is called Research (the Research canon's group)."""
    d = tree([], build=build if build is not None else [r for r, _ in RCORE])
    idx = os.path.join(d, "index.html")
    body = "".join('<a href="%s%s" class>%s</a>' % (BASE, r, l) for r, l in links)
    h = open(idx).read().replace("<summary>Evidence</summary><div class=\"panel\"></div>",
                                  "<summary>Research</summary><div class=\"panel\">%s</div>" % body)
    open(idx, "w").write(h)
    return d


expect("the Research canon's core order is to-do, what's new, sources and method",
       [c["key"] for c in RES["core"]] == ["open-questions", "errands", "worklist", "searched", "corrections", "changes",
                                          "sources", "method"])
ra = checknav.audit(rtree(RCORE), RES)
expect("a Research menu with the eight pages in group order conforms", ra["ok"])
ra = checknav.audit(rtree(RCORE + [("/documents/", "Documents"), ("/gallery/", "Gallery"),
                                    ("/the-stones/", "The Stones"), ("/audit/", "The Audit")],
                          build=[r for r, _ in RCORE] + ["/documents/", "/gallery/"]), RES)
expect("deep dives and an archive's own pages are local, allowed, and do not depart", ra["ok"] and len(ra["extras"]) == 2)
expect("...and local pages still show in the report", "allowed in Research" in checknav.render(ra, RES))
ra = checknav.audit(rtree(RCORE[:-1], build=[r for r, _ in RCORE]), RES)
expect("a missing core page in the Research menu still departs", not ra["ok"] and ra["problems"]["unlinked"] == ["method"])
ra = checknav.audit(rtree(RCORE[:-1], build=[r for r, _ in RCORE[:-1]]), RES)
expect("...and one not built at all is absent", not ra["ok"] and ra["problems"]["absent"] == ["method"])
swapped = RCORE[:]
swapped[0], swapped[3] = swapped[3], swapped[0]
ra = checknav.audit(rtree(swapped), RES)
expect("core pages out of group order depart", not ra["ok"] and bool(ra["problems"]["order"]))
ra = checknav.audit(rtree(RCORE[:3] + [("/photograph-these/", "Photograph these")] + RCORE[3:]), RES)
expect("a fold in the Research menu still departs even though local pages are allowed", not ra["ok"])
ra = checknav.audit(rtree([(r, "X" if r == "/errands/" else l) for r, l in RCORE]), RES)
expect("a wrong label in the Research menu departs", not ra["ok"] and len(ra["problems"]["label"]) == 1)
d = rtree(RCORE)
expect("--canon research is strict-clean on a conforming Research menu",
       checknav.main(["--dist", d, "--canon", "research", "--strict"]) == 0)
expect("the old Evidence canon is still the default and ignores a Research group",
       checknav.main(["--dist", d]) == 2)

print()
print("%d failed" % len(fails) if fails else "all cases behave")
sys.exit(1 if fails else 0)
