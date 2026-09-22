#!/usr/bin/env python3
"""What the row SHOWS, counted out of the built page.

THE FAULT THIS EXISTS FOR, stated plainly because it cost a fortnight.

`checkpages.py` asks whether a page imports a shared component. On 22
September 2026 all eight homepages imported the same four and scored
harmonised, while five of them drew no direct line at all and the three
that did drew a name, two years and a place. The measure said the estate
was aligned. The estate was not aligned, and the person who had asked for
it three times could see that at a glance.

  «i feel we need to bring these home page themes in line to show
   spouses, location pills, siblings, etc [like ive asked over and over.»

Component reuse is not content parity. A page can import the richest row
in the kit and hand it four fields out of fifteen — which is exactly what
six of them were doing, because the mapping in the page, not the
component, decides what a reader sees.

So this counts the rendered article. It reads `dist`, finds the spine
rows, and counts how many carry each thing a reader looks for: a spouse,
a place, an evidence grade, a trade, a household, a door to another
family. No source file is consulted, because the fault was invisible in
the source.

AND IT RATCHETS THE OTHER WAY FROM EVERY OTHER GATE HERE. The rest of
this toolbox fails when a bad number goes UP — unreachable sources,
inline evidence, bespoke pages. This one fails when a GOOD number goes
DOWN. Nothing has to get richer tomorrow; what is stopped is the quiet
slide back, the mapping that drops a field during an unrelated edit and
takes six months to notice.

  python3 checkrows.py --root . [--floor-file .rowfloor] [--write-floor]
  python3 checkrows.py --estate .. --report

`--write-floor` records today's counts. It is how a floor is raised, and
it is deliberately a separate, explicit act: a gate that re-baselines
itself on every run is not a gate.
"""

import argparse, glob, json, os, re, sys

# What a reader actually looks for, and the marks the kit's rows draw it
# with. Compact row and full row both, because an archive may show a
# spouse on one and not the other and that is still a hole.
MARKS = {
    "spouse":   [r'class="sp-csp"', r'class="sp-sp"'],
    "place":    [r'class="sp-pill sp-place"', r'<span class="sp-k">born</span>'],
    "grade":    [r'class="sp-pill sp-conf', r'<span class="chip">'],
    "trade":    [r'<i>trade</i>', r'<span class="sp-k">trade</span>'],
    "household":[r'class="sp-ckids"', r'class="sp-house"'],
    "door":     [r'class="sp-door', r'class="sp-door sp-dout'],
}
ROW = re.compile(r'<li class="sp-(?:cg|g)[^"]*"', re.I)


def pages(root):
    """The two pages that draw a line, wherever the build put them."""
    out = []
    for rel in ("index.html", "direct-line/index.html"):
        p = os.path.join(root, "dist", rel)
        if os.path.exists(p):
            out.append((rel, p))
    return out


def count(root):
    tally, rows = {k: 0 for k in MARKS}, 0
    looked = []
    for rel, p in pages(root):
        try:
            s = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        n = len(ROW.findall(s))
        if not n:
            continue
        looked.append(rel)
        rows += n
        for key, pats in MARKS.items():
            tally[key] += sum(len(re.findall(p_, s)) for p_ in pats)
    return tally, rows, looked


def floor_path(root, name):
    return os.path.join(os.path.abspath(os.path.join(root, "..")), name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--estate", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--floor-file", default=".rowfloor")
    ap.add_argument("--write-floor", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.report:
        estate = a.estate or ".."
        print("%-16s %5s %s" % ("archive", "rows", " ".join("%-10s" % k for k in MARKS)))
        for d in sorted(glob.glob(os.path.join(estate, "*", "site"))):
            arch = os.path.basename(os.path.dirname(d))
            t, rows, looked = count(d)
            if not looked:
                print("%-16s %5s  no built page draws a spine row" % (arch[:16], "-"))
                continue
            print("%-16s %5d %s" % (arch[:16], rows, " ".join("%-10d" % t[k] for k in MARKS)))
        return 0

    t, rows, looked = count(a.root)

    if not looked:
        # COULD-NOT-LOOK IS NOT NOTHING-WRONG. The same mistake that broke
        # eight deploys in eleven minutes when check:pages ran outside its
        # own repository: a gate that cannot find its subject must say so
        # and must not pass silently.
        print("  --    rows       not run: no built page under %s draws a spine row"
              % os.path.join(a.root, "dist"))
        return 0

    fp = floor_path(a.root, a.floor_file)
    if a.write_floor:
        json.dump({"rows": rows, **t}, open(fp, "w"), indent=1, sort_keys=True)
        open(fp, "a").write("\n")
        print("  ok    rows       floor written to %s: %d row(s), %s"
              % (a.floor_file, rows, ", ".join("%s %d" % (k, t[k]) for k in MARKS)))
        return 0

    if not os.path.exists(fp):
        print("  ok    rows       %d row(s) across %s; no floor recorded yet "
              "(run --write-floor to set one)" % (rows, ", ".join(looked)))
        return 0

    try:
        floor = json.load(open(fp, encoding="utf-8"))
    except (OSError, ValueError):
        print("  FAIL  rows       %s is unreadable" % a.floor_file)
        return 1

    lost = [(k, floor[k], t[k]) for k in MARKS if k in floor and t[k] < floor[k]]
    if not a.quiet:
        for k, was, now in lost:
            print("        %s fell from %d to %d" % (k, was, now))

    if lost:
        print("  FAIL  rows       %d thing(s) the rows used to show are no longer shown — "
              "this number may only go up" % len(lost))
        return 1
    gained = sum(1 for k in MARKS if k in floor and t[k] > floor[k])
    print("  ok    rows       %d row(s), nothing lost%s"
          % (rows, ", %d richer than the floor" % gained if gained else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
