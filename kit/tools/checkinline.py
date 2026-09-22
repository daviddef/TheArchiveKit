#!/usr/bin/env python3
"""Evidence living where only a template can reach it.

This estate has lifted the same fault out of one page after another and
written the reason down every time — Mazza's sources page: «seventy lines of
source list were inline in sources.astro, which meant they could not be
counted, checked or added to without editing a page»; Blazevic's: «a fact
living where only a template can reach it».

Four more were found in one week of harmonisation work, every one by
accident while converting something else: Blazevic's eight photograph jobs,
Falco's five strands, Falco's eleven families, Luwinski's ten open questions.

Then the estate was counted properly. THERE ARE SIXTY-FIVE, across 337KB,
and the largest is a 160KB, 178-row research log inside
`research-log.astro`. By archive: Falco 16, Luwinski 13, Booyzen 7, Lerena
7, D'Arcy 6, Mazza 5, Blazevic 3, Defranceski 2.

So this is the cheap half of the problem made visible. Finding them needs no
judgement: an array literal of objects or rows, assigned to a const in a
page's frontmatter, above a size worth arguing about. Fixing one does — it
means deciding what the rows are — and that stays with whoever knows.

WHAT IS NOT A FINDING. A vocabulary is not data: LABEL maps, colour ramps,
priority orders and section headings belong in the page that renders them,
and the thresholds are set to miss them. What is caught is a list of THINGS
THE ARCHIVE KNOWS — places, people, sources, findings, questions — which is
evidence, and evidence belongs in `src/data` where a tool can read it.

  .inline-exempt   one `path::const` per line at the archive root, optionally
                   followed by `— reason`. Printed on every run, like
                   .harmonise-exempt, because an exemption nobody reads is an
                   exemption nobody revisits.

THE RATCHET. --max-inline N fails when the count goes UP. Nothing has to be
extracted tomorrow; what is stopped is the sixty-sixth.

  python3 checkinline.py --root . [--max-inline N] [--quiet]
  python3 checkinline.py --estate .. --report
"""

import argparse, glob, os, re, sys

import os.path as _up, sys as _us
_us.path.insert(0, _up.dirname(_up.abspath(__file__)))
import unread as _unread  # a file a gate could not read; see kit/tools/unread.py

# Above both of these, or it is not worth anybody's morning.
MIN_BYTES = 900
MIN_ROWS = 4

# A SITE'S OWN NAVIGATION IS NOT SOMETHING THE ARCHIVE KNOWS. Two layouts
# hold a `nav` of three kilobytes, and it is a list of this site's pages —
# structure, not evidence, and it belongs beside the layout that draws it.
# Named narrowly rather than skipping layouts wholesale, so a layout that
# does hide evidence is still caught.
CONFIG = {"nav", "menu", "routes", "links", "sections", "order"}


def arrays(src):
    """Const-assigned array literals in the frontmatter, with their size."""
    parts = src.split("---")
    if len(parts) < 3:
        return []
    fm = parts[1]
    out = []
    for m in re.finditer(r"const\s+([A-Za-z_$][\w$]*)\s*=\s*\[", fm):
        start = m.end() - 1
        depth = 0
        end = None
        for i in range(start, len(fm)):
            c = fm[i]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            continue
        body = fm[start:end + 1]
        # A row is an object or a nested array at the top level of the literal.
        rows = len(re.findall(r"\n\s*[\[{]", body))
        if len(body) >= MIN_BYTES and rows >= MIN_ROWS:
            out.append((m.group(1), len(body), rows))
    return out


def exemptions(root):
    p = os.path.join(root, ".inline-exempt")
    out = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.split("#")[0].strip()
            if not line:
                continue
            key, _, why = line.partition("—")
            out[key.strip()] = why.strip()
    return out


def scan(root):
    found = []
    for f in sorted(glob.glob(os.path.join(root, "src", "**", "*.astro"), recursive=True)):
        rel = os.path.relpath(f, root).replace(os.sep, "/")
        try:
            src = open(f, encoding="utf-8", errors="ignore").read()
        except OSError as e:
            _unread.note(f, e)
            continue
        for name, size, rows in arrays(src):
            if name.lower() in CONFIG and "/layouts/" in rel:
                continue
            found.append((size, rows, rel, name))
    found.sort(reverse=True)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--estate", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--max-inline", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.report:
        estate = a.estate or ".."
        allf = []
        for d in sorted(glob.glob(os.path.join(estate, "*", "site"))):
            arch = os.path.basename(os.path.dirname(d))
            ex = exemptions(os.path.dirname(d))
            for size, rows, rel, name in scan(d):
                if f"{rel}::{name}" in ex:
                    continue
                allf.append((size, rows, arch, rel, name))
        allf.sort(reverse=True)
        print("%-26s %-42s %-12s %7s %5s" % ("archive", "page", "const", "bytes", "rows"))
        for size, rows, arch, rel, name in allf[:25]:
            print("%-26s %-42s %-12s %7d %5d" % (arch[:26], rel[:42], name[:12], size, rows))
        print("\n%d list(s) of evidence living in a template, %d bytes in total."
              % (len(allf), sum(x[0] for x in allf)))
        return 0

    root = a.root
    ex = exemptions(os.path.abspath(os.path.join(root, "..")))
    found = [(s, r, rel, n) for s, r, rel, n in scan(root)
             if f"{rel}::{n}" not in ex]
    kept = [(rel, n) for s, r, rel, n in scan(root) if f"{rel}::{n}" in ex]

    if not a.quiet:
        for size, rows, rel, name in found[:10]:
            print("        %s in %s — %d rows, %d bytes, reachable only by editing the page"
                  % (name, rel, rows, size))
        if len(found) > 10:
            print("        ... and %d more" % (len(found) - 10))
        for rel, n in kept:
            why = ex.get(f"{rel}::{n}", "")
            print("        exempt — %s::%s%s" % (rel, n, (": " + why) if why else "  (NO REASON GIVEN)"))

    n = len(found)
    if a.max_inline is not None and n > a.max_inline:
        print("  FAIL  inline     %d list(s) of evidence in a template, and the ratchet is %d — "
              "this number may only go down" % (n, a.max_inline))
        return 1
    if n:
        print("  ok    inline     %d list(s) of evidence still in a template, %d exempt"
              % (n, len(kept)))
    else:
        print("  ok    inline     no evidence left in a template, %d exempt" % len(kept))
    return 0


if __name__ == "__main__":

# COULD-NOT-LOOK IS NOT NOTHING-WRONG, and it belongs at the exit rather than
# at each `return 0` inside main(). If this gate passed but could not read
# part of its subject, it has no honest verdict to give and gives none.
    sys.exit(main() or _unread.refuse("inline"))
