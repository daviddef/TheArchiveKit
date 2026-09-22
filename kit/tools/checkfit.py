#!/usr/bin/env python3
"""An archive holding data shaped exactly like a kit component it does not use.

On 21 September 2026 `Strands` was promoted into a kit that already contained
`BranchRivers`. Both drew the same figure — lanes of one surname, a spine of
dated places, a fan of endings — and nothing compared them, because
`checkshared` compares components that share a NAME and these shared none.

The duplicate was also quietly wrong. `BranchRivers` marks a soft ending with
a trailing `?`; the copy used a boolean. Fed Luwinski's data, four of
twenty-seven endings drew SOLID that should have been dotted: four claims the
archive does not make, in a figure that looked entirely normal.

THE EVIDENCE WAS IN THE DATA AND WAS NEVER LOOKED AT. Luwinski's lines.json
used `lanes`, `nodes`, `ends`, `colour`, `label`, `conf`, `read`, `href`,
`unplaced`, `loose` — 79% of its field names are ones BranchRivers reads, and
it fitted with no adapter at all. Data that already fits a component is data
that was shaped by it, at one remove, by somebody copying the drawing.

So this compares FIELD NAMES IN DATA against FIELD NAMES A COMPONENT READS,
and reports an archive holding a close fit for a component it never imports.

WHY NOT COMPARE THE COMPONENTS THEMSELVES. That was tried first and thrown
away. Fingerprinting the SVG grammar scored the real pair at 0.97 for tag
similarity — and every other chart in the estate scored nearly as high,
because they are all made of svg, g, path, circle and text. It surfaced 31
pairs with the true one EIGHTH. A check that reports thirty wrong answers
above the right one is worse than no check, and this estate has written that
down twice already.

  python3 checkfit.py --estate .. [--min 0.55] [--quiet]
"""

import argparse, collections, glob, json, os, re, sys

import os.path as _up, sys as _us
_us.path.insert(0, _up.dirname(_up.abspath(__file__)))
import unread as _unread  # a file a gate could not read; see kit/tools/unread.py

# Words that mean nothing on their own: every component reads `map`, `length`,
# `filter`, and every data file has an `id` and a `name`.
STOP = {"map", "filter", "length", "join", "slice", "split", "sort", "push",
        "replace", "toLowerCase", "toUpperCase", "trim", "includes", "reduce",
        "find", "some", "every", "concat", "keys", "values", "entries", "props",
        "flatMap", "startsWith", "endsWith", "padStart", "toFixed", "match",
        "forEach", "indexOf", "repeat", "astro", "default", "json", "then",
        "id", "name", "title", "href", "url", "src", "alt", "note", "label"}


def fields_read(src):
    body = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    body = re.sub(r"^\s*//.*$", " ", body, flags=re.M)
    return {f for f in re.findall(r"\.([a-z][A-Za-z0-9_]{2,})\b", body) if f not in STOP}


def keys_of(o, d=0, out=None):
    out = set() if out is None else out
    if d > 6:
        return out
    if isinstance(o, dict):
        out |= {k for k in o if k not in STOP}
        for v in o.values():
            keys_of(v, d + 1, out)
    elif isinstance(o, list):
        for v in o[:4]:
            keys_of(v, d + 1, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estate", default="..")
    ap.add_argument("--min", type=float, default=0.55)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    kit = {}
    for f in sorted(glob.glob(os.path.join(a.estate, "Archive Kit", "kit", "components", "*.astro"))):
        n = os.path.basename(f)[:-6]
        fr = fields_read(open(f, encoding="utf-8", errors="ignore").read())
        if len(fr) >= 5:
            kit[n] = fr
    if not kit:
        print("  --    fit        not run: no kit components found under %s"
              % os.path.abspath(a.estate))
        return 0

    hits = []
    for d in sorted(glob.glob(os.path.join(a.estate, "*", "site", "src"))):
        arch = os.path.basename(os.path.dirname(os.path.dirname(d)))
        used = set()
        for p in glob.glob(os.path.join(d, "**", "*.astro"), recursive=True):
            used |= set(re.findall(r"archive-kit/components/([A-Za-z]+)\.astro",
                                   open(p, encoding="utf-8", errors="ignore").read()))
        for jf in glob.glob(os.path.join(d, "data", "*.json")):
            try:
                keys = keys_of(json.load(open(jf, encoding="utf-8")))
            except (ValueError, OSError) as e:
                _unread.note(f, e)
                continue
            if len(keys) < 5:
                continue
            for comp, fr in kit.items():
                if comp in used:
                    continue
                cover = len(keys & fr) / len(keys)
                if cover >= a.min and len(keys & fr) >= 5:
                    hits.append((cover, arch, os.path.basename(jf), comp,
                                 sorted(keys & fr)))
    hits.sort(reverse=True)

    if not a.quiet:
        for cover, arch, jf, comp, shared in hits:
            print("        %.0f%%  %s / %s fits %s, which this archive never imports"
                  % (cover * 100, arch, jf, comp))
            print("              shared field names: %s" % ", ".join(shared[:12]))

    print("  %s  fit        %d kit component(s) against the estate's data; %d close fit(s) unused"
          % ("ok  " if not hits else "note", len(kit), len(hits)))
    return 0


if __name__ == "__main__":

# COULD-NOT-LOOK IS NOT NOTHING-WRONG, and it belongs at the exit rather than
# at each `return 0` inside main(). If this gate passed but could not read
# part of its subject, it has no honest verdict to give and gives none.
    sys.exit(main() or _unread.refuse("fit"))
