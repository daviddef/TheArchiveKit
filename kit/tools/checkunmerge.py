#!/usr/bin/env python3
"""People a withdrawn merge deleted, counted against the previous commit.

WHERE THIS APPLIES, AND WHERE IT IS DEAD WEIGHT. Only an archive whose frozen
slug ledger has MORE THAN ONE KEY SHAPE can suffer the fault below. Where a
ledger keys every person one way — a GEDCOM id, a name — two keys can never
arrive at one slug, there is nothing for a collision guard to catch, and this
check has no work to do. It says so and stops, rather than sitting in a build
reassuring somebody about a fault their data cannot have. Measured across this
estate: one ledger of four has two shapes.

THE ONE THAT MADE THIS NECESSARY. The Falco archive withdrew a merge of two
people who had been joined on a name. The register halves of Carmina Falco and
Pasqualina Falco — carrying deaths of 19 December 1832 and 14 September 1836 —
ceased to exist. No output said so. Every gate passed. The person count stayed
at 863, and 863 was the whole symptom: a withdrawal SPLITS one record into two,
so the count had to rise and it had not. 865 was correct.

WHY IT READS THE PREVIOUS COMMIT AND NOT A FLOOR FILE. A floor records a number
somebody wrote down. The number that mattered here was 863 -> 863, which only a
real before-and-after can show; a floor of 863 is satisfied by 863 and would
have passed the day the records were destroyed. So the comparison is against
`git show <ref>:<path>` — the data as last committed — and the check is
worthless without it, which is why it declines rather than guesses.

WHAT IT ASKS.

  withdrawn   slugs present in BOTH versions that carried the merge marker
              before and do not now. That is a merge someone corrected.
  required    len(after) >= len(before) + len(withdrawn). Each withdrawal
              separates one record into two, so each owes one new person.
  shortfall   required - len(after). The USEFUL output, not a boolean: Falco's
              was exactly 2, and that 2 named the two records already gone
              before anybody knew anything was wrong.

IT REPORTS AND DOES NOT FAIL. A withdrawal landing in the same build as a
genuine removal is legitimate and will show a shortfall that is nobody's bug. A
gate that cries wolf gets learned as noise, and then it is worse than absent.
This one names the withdrawn slugs and the arithmetic and leaves the judgement
with the person who made the change.

  python3 checkunmerge.py --data src/data/people.json \
                          --ledger src/data/person-slugs.json
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import unread as _unread
except Exception:                                    # the kit may be partial
    _unread = None

LABEL = "unmerge"


def shape(key):
    """The KIND of a ledger key, which is what decides whether this can fire."""
    if ":" in key:
        return key.split(":", 1)[0] + ":"
    return "pipe|" if "|" in key else "plain"


def shapes(ledger):
    out = {}
    for k in ledger:
        if k.startswith("_"):
            continue
        out[shape(k)] = out.get(shape(k), 0) + 1
    return out


def rows_of(blob, field):
    """people.json is a bare list in some archives and wrapped in others."""
    if isinstance(blob, list):
        rows = blob
    else:
        rows = None
        for k in ("people", "persons", "rows", "register"):
            if isinstance(blob.get(k), list):
                rows = blob[k]
                break
        if rows is None:
            return None
    by = {}
    for r in rows:
        if isinstance(r, dict) and r.get(field):
            by[str(r[field])] = r
    return by


def committed(path, ref):
    """The file as <ref> holds it, or None when <ref> does not have it."""
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if top.returncode:
        return None, "not a git checkout"
    rel = os.path.relpath(os.path.abspath(path), top.stdout.strip())
    p = subprocess.run(["git", "show", "%s:%s" % (ref, rel)],
                       capture_output=True, text=True)
    if p.returncode:
        return None, "%s has no %s" % (ref, rel)
    try:
        return json.loads(p.stdout), None
    except Exception as e:
        return None, "%s:%s will not parse — %s" % (ref, rel, str(e)[:60])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="the person register")
    ap.add_argument("--ledger", help="the frozen slug ledger; the precondition "
                                     "is read from it, and without it the check "
                                     "runs anyway rather than assuming")
    ap.add_argument("--id", default="slug", help="the field identifying a person")
    ap.add_argument("--merged", default="mergedOn", help="the merge marker field")
    ap.add_argument("--ref", default="HEAD", help="the commit to compare against")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.data):
        print("  --    %-10s not run: no %s" % (LABEL, a.data))
        return 0

    # The precondition. A one-shape ledger cannot carry the fault.
    if a.ledger and os.path.exists(a.ledger):
        try:
            led = json.load(open(a.ledger, encoding="utf-8"))
        except Exception as e:
            if _unread:
                _unread.note(a.ledger, e)
            led = None
        if isinstance(led, dict):
            led = led.get("slugs", led)
            sh = shapes(led)
            if len(sh) <= 1:
                print("  --    %-10s not applicable: the ledger keys people one "
                      "way (%s), so two keys cannot reach one slug"
                      % (LABEL, ", ".join(sh) or "no keys"))
                return 0
            if not a.quiet:
                print("        note  %s ledger has %d key shapes — %s"
                      % (LABEL, len(sh),
                         ", ".join("%s %d" % (k, v) for k, v in sorted(sh.items()))))

    try:
        now = json.load(open(a.data, encoding="utf-8"))
    except Exception as e:
        if _unread:
            _unread.note(a.data, e)
        print("  FAIL  %-10s %s could not be read — %s" % (LABEL, a.data, str(e)[:60]))
        return 1

    was, why = committed(a.data, a.ref)
    if was is None:
        print("  --    %-10s not run: %s, and a floor cannot stand in for a "
              "before-and-after" % (LABEL, why))
        return 0

    after = rows_of(now, a.id)
    before = rows_of(was, a.id)
    if after is None or before is None:
        print("  --    %-10s not run: no list of people carrying %r"
              % (LABEL, a.id))
        return 0

    merged_before = {s for s, r in before.items() if r.get(a.merged)}
    withdrawn = sorted(s for s in merged_before & set(after)
                       if not after[s].get(a.merged))
    required = len(before) + len(withdrawn)
    shortfall = required - len(after)

    if not withdrawn:
        print("  ok    %-10s %d people, %d merged · no merge was withdrawn since %s"
              % (LABEL, len(after), len(merged_before), a.ref))
        return 0

    for s in withdrawn:
        print("        note  %s withdrawn: %s (%s)"
              % (LABEL, s, (after[s].get("name") or "?")))
    if shortfall > 0:
        print("        note  %s %d withdrawal(s) owe %d person(s); the count went "
              "%d -> %d and %d was required. A withdrawal SEPARATES one record "
              "into two, so the count must go UP by one for each. Short by %d — "
              "either a half was dropped, or something else was removed in the "
              "same change."
              % (LABEL, len(withdrawn), len(withdrawn), len(before), len(after),
                 required, shortfall))
    print("  ok    %-10s %d people · %d withdrawn · %d -> %d, %d required%s"
          % (LABEL, len(after), len(withdrawn), len(before), len(after), required,
             (" · SHORT BY %d" % shortfall) if shortfall > 0 else " · accounted for"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
