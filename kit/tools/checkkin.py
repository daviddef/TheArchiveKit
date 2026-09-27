#!/usr/bin/env python3
"""Relationships a person chart should never draw.

THE ONE THAT MADE THIS NECESSARY. The Defranceski archive gave Ivan
Defranceski — born 1943, dead in 1945 aged two — a wife and a son. Nothing
was malicious and nothing was guessed: the test for «is this person a parent
in this household» asked only whether the household began twelve to sixty
years after their birth, and a household of 1948 sits squarely in that
window for a boy born in 1943. He was three years dead. Only a death date
could refuse it, and the test had never asked for one.

It was not a cosmetic tree error. The wife and the son on that chart are a
living woman and a living man, attached to the wrong person, on a public
page.

WHAT THIS ASKS, AND WHY EACH ONE IS SEPARATE.

  a parent who died a child   somebody with a spouse or a child whose own
                              record has them dead before fifteen. Fifteen
                              is deliberately generous: it refuses infants,
                              not early marriages.
  dates that cannot both      a death before a birth. Where a record carries
  be true                     both, one of them belongs to somebody else —
                              and in a merged record it is usually the merge
                              that is wrong, not either date.
  a life past 110             reported, never failed. People do live that
                              long, rarely, and an archive that holds one
                              should not be nagged about it.

THE RATCHET. `--max N` fails when the count goes UP. Nothing has to be
corrected today; what is stopped is the next one. This is the estate's usual
shape — checkinline and checkrows both work this way — because a gate that
fails on the day it ships gets silenced on the day it ships.

WHY THIS IS A DATA CHECK AND NOT A PAGE CHECK. The built page is where the
harm appears, but the record is where it can be answered: «Vittoria Cimmino,
born 1877, died Feb 7 1857» tells a researcher which two people were welded
together. «A chart with an impossible date» tells them nothing.

Every finding prints the RAW strings it was judged on. An early version of
this check reported eleven infant-parents in one archive and every one of
them was the checker's own parser, binding a ternary the wrong way so that
a person with no birth year came out as «died at 0».

  python3 checkkin.py --data site/src/data/people.json --born born --died died
  python3 checkkin.py --data site/src/data/roster.json --born b --died d --max 4
"""

import argparse, json, os, re, sys

MIN_PARENT_AGE = 15
IMPLAUSIBLE_AGE = 110


def year(v):
    m = re.search(r"\b(1[0-9]{3}|20[0-2][0-9])\b", str(v if v is not None else ""))
    return int(m.group(1)) if m else None


def rows_of(doc):
    if isinstance(doc, list):
        return doc
    for k in ("people", "rows", "roster", "persons"):
        v = doc.get(k)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return list(v.values())
    return []


def kin(r):
    """Children and spouses, wherever this archive keeps them.

    Some put them on the person, some under `rel`. A bare string is counted
    as an edge but carries no dates, which is why only the PERSON's own
    dates decide anything here.
    """
    rel = r.get("rel") if isinstance(r.get("rel"), dict) else {}
    ch = r.get("children") if isinstance(r.get("children"), list) else rel.get("children") or []
    sp = r.get("spouses") if isinstance(r.get("spouses"), list) else rel.get("spouses") or []
    return list(ch), list(sp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="the person register")
    ap.add_argument("--born", default="born")
    ap.add_argument("--died", default="died")
    ap.add_argument("--name", default="name")
    ap.add_argument("--max", type=int, default=None,
                    help="ratchet: fail when the count rises above this")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.data):
        print("  --    kin        not run: no %s" % a.data)
        return 0
    try:
        rows = [r for r in rows_of(json.load(open(a.data, encoding="utf-8")))
                if isinstance(r, dict)]
    except Exception as e:
        # A register this cannot read is a register it cannot vouch for.
        print("  FAIL  kin        %s could not be read — %s" % (a.data, str(e)[:70]))
        return 1

    infants, impossible, aged = [], [], []
    tested = 0                 # rows where BOTH dates parsed — see below
    has_born = has_died = 0    # rows carrying the field at all, parsed or not
    for r in rows:
        if r.get(a.born) not in (None, "", []):
            has_born += 1
        if r.get(a.died) not in (None, "", []):
            has_died += 1
        b, d = year(r.get(a.born)), year(r.get(a.died))
        nm = str(r.get(a.name) or "?")
        if b is None or d is None:
            continue
        tested += 1
        if d < b:
            impossible.append((nm, r.get(a.born), r.get(a.died), d - b))
            continue
        if d - b > IMPLAUSIBLE_AGE:
            aged.append((nm, r.get(a.born), r.get(a.died), d - b))
            continue
        if d - b < MIN_PARENT_AGE:
            ch, sp = kin(r)
            if ch or sp:
                infants.append((nm, r.get(a.born), r.get(a.died), len(ch), len(sp)))

    # WHAT THIS GATE ACTUALLY EXAMINED, which is not the same as how many
    # people it was given. Every test below needs BOTH a birth and a death, so
    # a row with one of them is skipped, and a run that skipped every row
    # reported «N people · 0 impossible relationship(s) · ok» having examined
    # nobody. Lerena did exactly that: 357 people, 191 with a birth, and no
    # `died` field anywhere in the file, so it tested 0 and passed, for as long
    # as this gate has existed.
    #
    # The Falco session put the rule that catches it — when a check reports
    # zero, ask whether zero is a finding or a failure to look — and the range
    # form it generalises to: a gate has two ends, and a gate that stops
    # finding anybody passes by refusing everyone just as surely as one that
    # stops refusing anybody passes by flagging everyone.
    #
    # Three cases, deliberately not one, because only two of them are faults:
    #   no rows at all           the register is gone or unreadable as a list
    #   the field is ABSENT      this archive does not record deaths in this
    #                            file. Not a fault, and not an «ok» either:
    #                            the gate declines and says whose fault it is
    #                            not, rather than claiming a clean archive.
    #   the field is PRESENT     and nothing parsed — a format or a key changed
    #                            and every test below silently did nothing.
    if not rows:
        print("  FAIL  kin        %s holds no people, so nothing was examined and a "
              "clean reading here would mean only that the register is gone" % a.data)
        return 1
    if not tested:
        if not has_died or not has_born:
            missing = "%s%s%s" % ("«%s»" % a.born if not has_born else "",
                                  " and " if not has_born and not has_died else "",
                                  "«%s»" % a.died if not has_died else "")
            print("  --    kin        not run: not one of the %d row(s) in %s carries "
                  "%s, so every test here needs a date this register does not hold. "
                  "Nothing was examined, and that is not the same as nothing being "
                  "wrong." % (len(rows), a.data, missing))
            return 0
        print("  FAIL  kin        %d row(s) carry %s and %d carry %s, and not one "
              "yielded a usable pair of years — the field names still match but "
              "nothing parses, so every test below examined nobody"
              % (has_born, "«%s»" % a.born, has_died, "«%s»" % a.died))
        return 1

    n = len(infants) + len(impossible)
    refusing = n > a.max if a.max is not None else bool(n)

    # A FINDING THE RATCHET IS HOLDING IS NOT A FAILURE, and must not print as
    # one. The estate learned this the hard way today with a probe that exited
    # non-zero on every healthy repository: a check that alarms on the normal
    # case is not a check anybody runs, it is noise they have learned to scroll
    # past. So the word matches the verdict — FAIL only when this run refuses.
    tag = "FAIL " if refusing else "held "
    for nm, b, d, nc, ns in infants:
        print("  %s kin        %s — born %r, died %r, and carries %d child(ren) "
              "and %d spouse(s)" % (tag, nm, b, d, nc, ns))
    for nm, b, d, gap in impossible:
        print("  %s kin        %s — born %r, died %r: %d years apart the wrong way"
              % (tag, nm, b, d, gap))
    if not a.quiet:
        for nm, b, d, gap in aged:
            print("        note  %s lived to %d — born %r, died %r. Rare, not refused."
                  % (nm, gap, b, d))

    if a.max is not None and n > a.max:
        print("  FAIL  kin        %d relationship(s) no chart should draw, and the "
              "ratchet is %d — this number may only go down" % (n, a.max))
        return 1
    if a.max is None and n:
        print("  FAIL  kin        %d relationship(s) no chart should draw" % n)
        return 1
    print("  ok    kin        %d of %d people carry both dates and were examined · "
          "%d impossible relationship(s)%s · %d aged past %d"
          % (tested, len(rows), n,
             (", the ratchet is %d" % a.max) if a.max is not None else "",
             len(aged), IMPLAUSIBLE_AGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
