#!/usr/bin/env python3
"""Re-derive what shared-pages.json claims, and say where it has drifted.

WHY THIS EXISTS. Every count in that register — five of seven, four of five,
503 to 11,809 words — was measured once, by hand, on the day the row was
written. Then the estate moved underneath it. Within a single session two of
its notes were found false:

  · /corrections/ said "Mazza has none recorded yet". Mazza holds 102 in 39
    kind-groups. That note had me calling a conversion blocked that was a
    straight job.
  · /register/ said "Mazza and Lerena have none". Both keep one — Mazza builds
    it out of seven data files, Lerena out of people.json — and the row had
    been marked ALIGNED on the strength of that sentence.

A register that is wrong is worse than no register, because it is the thing the
work is counted against. So the structural facts are derived here and the prose
is checked against them, rather than being trusted.

WHAT IS DERIVED, and what is not. `has` (how many archives carry the page) and
`using` (how many import a kit component on it) are filesystem facts and are
computed. Whether a page SHOULD share a shape is a judgement and stays in the
note — this tool never rewrites prose. It only refuses to let prose and
arithmetic disagree in silence.

  python3 readacross.py --root <dir containing the archives> [--write] [--strict]

Advisory by default. --write updates has/using/archives in place and leaves
every note alone. --strict exits non-zero on drift, for a session that wants
the register to hold still.
"""
import argparse, io, json, os, re, sys

ARCHIVES = ["Falco Family", "Defranceski Family", "Booyzen Family", "D'Arcy Family",
            "Blazevic Family", "Mazza Family", "Lerena Family"]
WORDS = {"no": 0, "none": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
         "twelve": 12, "all seven": 7, "all five": 5, "all six": 6, "all four": 4}


def page_of(root, archive, route):
    """The file that serves this route, whichever of the two shapes it uses."""
    r = route.strip("/")
    for c in ("%s/site/src/pages/%s.astro" % (archive, r),
              "%s/site/src/pages/%s/index.astro" % (archive, r)):
        p = os.path.join(root, c)
        if os.path.exists(p):
            return p
    return None


def claims(note):
    """Every 'N of M' the prose asserts, as (n, m) pairs.

    Only this one shape is read. A note saying '503 to 11,809 words' is a
    measurement of something this tool cannot see, and guessing at it would
    produce exactly the confident wrongness the register already suffers from.
    """
    t = note.lower()
    for a, n in WORDS.items():
        t = re.sub(r"\b%s\b" % re.escape(a), str(n), t)
    out = []
    for m in re.finditer(r"\b(\d+)\s+of\s+(\d+)\b", t):
        out.append((int(m.group(1)), int(m.group(2))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--register", default=None)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    reg = a.register or os.path.join(root, "Archive Kit", "shared-pages.json")
    if not os.path.exists(reg):
        print("  no shared-pages.json at %s" % reg)
        return 1
    doc = json.load(io.open(reg, encoding="utf-8"))
    rows = doc["rows"]

    drift = []
    for r in rows:
        key = r["key"]
        route = r.get("route") or "/%s/" % key
        has, using = [], []
        for arch in ARCHIVES:
            p = page_of(root, arch, route)
            if not p:
                continue
            has.append(arch)
            src = io.open(p, encoding="utf-8").read()
            # The component THIS ROW is about, not any kit import. Mazza's
            # register page imports Evidence, which is a chip and not a
            # register, and counting it made a page look converted that is not.
            want = r.get("component")
            mark = ("archive-kit/components/%s.astro" % want) if want else "archive-kit/components/"
            if mark in src:
                using.append(arch)
        short = [x.split()[0] for x in has if x not in using]

        was_on = r.get("on")
        if was_on is not None and was_on != len(has):
            drift.append("%s: row says it is on %s archives; %d carry the page (%s)"
                         % (key, was_on, len(has), ", ".join(x.split()[0] for x in has)))

        # A row calling itself aligned while some archive draws its own is the
        # failure that matters: it is how /register/ came to be marked done.
        if r["state"] == "aligned" and short:
            drift.append("%s: marked ALIGNED, but %d of %d draw their own — %s"
                         % (key, len(short), len(has), ", ".join(short)))
        if r["state"] == "local" and using:
            drift.append("%s: marked LOCAL, but %d already use a kit component — %s"
                         % (key, len(using), ", ".join(x.split()[0] for x in using)))

        # Only a claim written in the estate's own idiom for this - "four of
        # seven on the shared Searched" - is judged. The notes also count
        # letters, words, rows and which archives hold something as DATA, and
        # /sources/ saying "two of seven hold sources as data" is true while
        # nought import the component. Reading that as a contradiction is the
        # same confident wrongness this tool exists to catch.
        note = r.get("note", "")
        for n, m in (claims(note) if re.search(r"on the shared", note, re.I) else []):
            if m == len(has) and n != len(using):
                drift.append("%s: note says %d of %d, but %d import the component"
                             % (key, n, m, len(using)))

        if a.write:
            r["on"] = len(has)
            r["using"] = len(using)
            r["drawingTheirOwn"] = short

        print("  %-16s %d carry it, %-2d on the shared shape  %-8s %s"
              % (key, len(has), len(using), r["state"], ", ".join(short) or ""))

    if a.write:
        io.open(reg, "w", encoding="utf-8").write(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        print("\n  written: on/using/drawingTheirOwn refreshed on %d rows; no note touched"
              % len(rows))

    print()
    if drift:
        for d in drift:
            print("  DRIFT  %s" % d)
        print("\n  %d place(s) where the register and the estate disagree" % len(drift))
        return 1 if a.strict else 0
    print("  ok    the register matches the estate on every row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
