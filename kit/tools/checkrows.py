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
# TWO COMPONENTS DRAW A LINE IN THIS ESTATE AND THIS MUST SEE BOTH. `Spine`
# emits sp-*; `Descent` — the couple-and-children row adopted on 22 September
# — emits dsc-*. Defranceski moved to Descent and this gate reported spouses,
# places, grades and trades all halving and the doors going to zero, because
# it was counting the marks of the component that had been replaced.
#
# That is the same fault as `checkpages`, in the tool written to fix it: a
# measure that tracks one implementation and reports on the estate. A count
# here is of the THING A READER SEES, so every way the estate draws that
# thing belongs in its list.
MARKS = {
    "spouse":   [r'class="sp-csp"', r'class="sp-sp"', r'class="dsc-side"'],
    "place":    [r'class="sp-pill sp-place"', r'<span class="sp-k">born</span>',
                 r'class="dsc-place"'],
    "grade":    [r'class="sp-pill sp-conf', r'<span class="chip">',
                 r'class="dsc-pill dsc-conf"'],
    "trade":    [r'<i>trade</i>', r'<span class="sp-k">trade</span>',
                 r'class="dsc-trade"'],
    "household":[r'class="sp-ckids"', r'class="sp-house"', r'class="dsc-kid'],
    "door":     [r'class="sp-door', r'class="sp-door sp-dout', r'class="dsc-door'],
}
# ONE ALTERNATION PER MARK, NOT A SUM OVER PATTERNS. Summing `findall` for
# each pattern counts an element once per pattern it matches, and these
# patterns nest: `class="sp-door sp-dout"` matches both `class="sp-door` and
# `class="sp-door sp-dout`, so every EXTERNAL door scored two. Defranceski's
# floor was written at 15 doors for a page that draws 3, and the gate then
# reported a loss when the true number had not moved. A single alternation
# consumes the match once.
RX = {k: re.compile("|".join(pats)) for k, pats in MARKS.items()}

ROW = re.compile(r'<li class="sp-(?:cg|g)[^"]*"|<div class="dsc-gen"', re.I)


def pages(root):
    """EVERY BUILT PAGE THAT DRAWS A SPINE ROW, not a list of two.

    The first version looked at index.html and direct-line/index.html and
    nothing else — which left Lerena's Argentina and Uruguay descents and
    Luwinski's Wear line outside the gate entirely. That is the same
    mistake this tool exists to correct, committed inside the correction:
    a measure that inspects part of the estate and reports on all of it.

    Person pages are scanned too and cost nothing, because they draw
    `pt-` nodes rather than spine rows and simply do not match.
    """
    dist = os.path.join(root, "dist")
    if not os.path.isdir(dist):
        return []
    out = []
    for f in sorted(glob.glob(os.path.join(dist, "**", "*.html"), recursive=True)):
        try:
            s = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if ROW.search(s):
            out.append((os.path.relpath(f, dist).replace(os.sep, "/"), f, s))
    return out


def count(root):
    tally, rows = {k: 0 for k in MARKS}, 0
    looked = []
    for rel, _p, s in pages(root):
        n = len(ROW.findall(s))
        if not n:
            continue
        looked.append(rel)
        rows += n
        for key, rx in RX.items():
            tally[key] += len(rx.findall(s))
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
