#!/usr/bin/env python3
"""Refuse to ship a build that gives away a living person's details.

THE RULE, in David's words: a living person is NAMED AND NOTHING MORE. No date
of birth, no date of death, no place. Public figures are the exception and are
declared. A name is unlocked when its owner dies, one at a time.

AND THE AGE RULE: anyone more than EIGHTY YEARS OLD is treated as deceased. An
archive that cannot say whether someone is alive has to presume something, and
this is what it presumes.

TWO MODES, because the estate genuinely has two situations.

  derived      the archives. Living people are IN the data, flagged, and the
               guard reads them out of it. This is Falco's design, generalised.
  declared     the children's site. There is no people file, just four boys and
               grown-ups referred to by initials, so the list is written by hand.

WHY THE DERIVED MODE TESTS EXACT DATE STRINGS AND NOT PROXIMITY — this is
Falco's reasoning, kept because it was paid for twice:

  Screening on BARE YEARS passes vacuously. This is a genealogy site; every
  year appears somewhere.

  Screening on a living person's NAME NEAR A DATE fires on every homonym. A
  living Luigi Falco shares his name with four dead ones and the HTML cannot
  tell them apart. Identity lives in the data, not in the markup.

So it takes the full date strings the DATA attaches to a LIVING person and
asserts those literal strings appear nowhere in the build. That is the leak
that actually reached a front page: line.json carried a living generation's
«3 Sep 1955» and a diagram printed it verbatim.

An archive that omits living people from its data altogether — Defranceschi
drops them at import, Blazevic redacts before writing — passes this with
nothing to check, which is correct. Their rule is stricter than this one.

Usage:
  python3 checkliving.py --dist dist                  # derived, the archives
  python3 checkliving.py --dist dist --declared f.json  # the children's site
"""
import os
import re
import sys
import json
import html
import argparse
import datetime

PRESUME_DEAD_AFTER = 80          # years. Older than this is treated as deceased.

NAME_KEYS = ("name", "n", "who", "t")
BORN_KEYS = ("born", "b", "birth", "byear", "b_date")
DIED_KEYS = ("died", "d", "death", "dyear", "d_date")
LIVING_KEYS = ("living", "presumedLiving", "alive", "isLiving")

MONTHS = (r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|"
          r"January|February|March|April|June|July|August|September|October|"
          r"November|December|"
          r"Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|"
          r"Settembre|Ottobre|Novembre|Dicembre")
FULL_DATE = re.compile(r"\b\d{1,2}\s+(?:" + MONTHS + r")[a-z]*\.?\s+(?:1[89]\d\d|20\d\d)\b")
ISO_DATE = re.compile(r"\b(?:1[89]\d\d|20\d\d)-\d{2}-\d{2}\b")
SLASH_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/(?:1[89]\d\d|20\d\d)\b")
YEAR = re.compile(r"\b(1[89]\d\d|20\d\d)\b")


def rows_of(j):
    if isinstance(j, list):
        return [r for r in j if isinstance(r, dict)]
    if isinstance(j, dict):
        for key in ("people", "rows", "spine", "ancestors", "individuals"):
            v = j.get(key)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
            if isinstance(v, dict):
                return [r for r in v.values() if isinstance(r, dict)]
    return []


def first(r, keys):
    for k in keys:
        v = r.get(k)
        if v not in (None, "", "—", "-"):
            return str(v)
    return ""


def older_than(born, years, today):
    """True when a birth date is far enough back to presume death."""
    m = YEAR.search(born or "")
    if not m:
        return False
    return (today.year - int(m.group(1))) > years


def gather(data_dir, today, verbose):
    """Every person the data marks living, with the date strings attached."""
    living, presumed_dead = {}, 0
    for f in sorted(os.listdir(data_dir)) if os.path.isdir(data_dir) else []:
        if not f.endswith(".json"):
            continue
        try:
            j = json.load(open(os.path.join(data_dir, f), encoding="utf-8"))
        except Exception:
            continue
        for r in rows_of(j):
            flagged = any(r.get(k) is True for k in LIVING_KEYS) or \
                      str(r.get("conf", "")).lower() == "living"
            if not flagged:
                continue
            name = re.sub(r"\s*\(.*?\)", "", first(r, NAME_KEYS)).strip()
            if not name or len(name) < 3:
                continue
            born, died = first(r, BORN_KEYS), first(r, DIED_KEYS)
            # the age rule: too old to still be presumed alive
            if older_than(born, PRESUME_DEAD_AFTER, today):
                presumed_dead += 1
                continue
            dates = set()
            for blob in (born, died):
                for rx in (FULL_DATE, ISO_DATE, SLASH_DATE):
                    dates.update(rx.findall(blob))
                    dates.update(m.group(0) for m in rx.finditer(blob))
            living.setdefault(name, set()).update(d for d in dates if isinstance(d, str))
    if verbose:
        print(f"  living: {len(living)} people flagged in the data, "
              f"{presumed_dead} presumed dead by the {PRESUME_DEAD_AFTER}-year rule")
    return living


def built_text(dist):
    pages = {}
    for root, _, files in os.walk(dist):
        for f in files:
            if not f.endswith(".html"):
                continue
            p = os.path.join(root, f)
            pages[os.path.relpath(p, dist).replace(os.sep, "/")] = \
                open(p, encoding="utf-8", errors="replace").read()
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--data", default="src/data")
    ap.add_argument("--declared", default=None,
                    help="a hand-written living.json (the children's-site mode)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    today = datetime.date.today()

    if not os.path.isdir(a.dist):
        print(f"checkliving: no {a.dist} — build first")
        return 1
    pages = built_text(a.dist)
    if len(pages) < 5:
        print(f"checkliving: only {len(pages)} page(s) under {a.dist} — the build is "
              f"unfinished or in flight. Refusing to pass.")
        return 1

    fails = []

    if a.declared:
        # ---- the children's site: a hand-written list of names to forbid ----
        if not os.path.exists(a.declared):
            print(f"checkliving: no declaration at {a.declared}. This guard is only as "
                  f"good as its list, so a missing list is a failure, not a pass.")
            return 1
        decl = json.load(open(a.declared, encoding="utf-8"))
        allow = [x.lower() for x in decl.get("allow", [])]
        terms = []
        for p in decl.get("living", []):
            who = p.get("initials") or "?"
            for n in p.get("forbid", []):
                if n:
                    terms.append((re.compile(r"\b" + re.escape(n) + r"\b", re.I),
                                  f"{who}: the name «{n}»"))
            if p.get("born"):
                terms.append((re.compile(r"\b" + re.escape(str(p["born"])) + r"\b"),
                              f"{who}: the birth year {p['born']}"))
        if not terms:
            print("checkliving: the declaration forbids nothing — nothing to check.")
            return 1
        for rel, raw in pages.items():
            for rx, label in terms:
                m = rx.search(raw)
                if not m:
                    continue
                ctx = re.sub(r"\s+", " ", raw[max(0, m.start() - 45):m.end() + 45])
                if any(x in ctx.lower() for x in allow):
                    continue
                fails.append((rel, label, ctx))
                break
        who = ", ".join(p.get("initials", "?") for p in decl.get("living", []))
        ok = f"{len(pages)} pages carry no name and no birth year for {who}"

    else:
        # ---- the archives: read the living from their own data -------------
        living = gather(a.data, today, not a.quiet)
        forbidden = {}
        for name, dates in living.items():
            for dstr in dates:
                forbidden.setdefault(dstr, set()).add(name)
        if not a.quiet:
            shown = ", ".join(sorted(forbidden)[:4])
            print(f"  guarding {len(forbidden)} date string(s) belonging to living people"
                  + (f": {shown}" if forbidden else
                     " — none found, which is what an archive that omits them looks like"))
        for rel, raw in pages.items():
            text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
            for dstr, owners in forbidden.items():
                if dstr in text or dstr in raw:
                    fails.append((rel, f"the date «{dstr}», which the data attaches to "
                                       f"{', '.join(sorted(owners))} (living)",
                                  re.sub(r"\s+", " ", text[max(0, text.find(dstr) - 50):
                                                           text.find(dstr) + 50])))
                    break
        ok = (f"{len(pages)} pages — no living person's date reaches the build "
              f"({len(living)} living, {len(forbidden)} dates guarded)")

    if fails:
        print(f"  FAIL  living      {len(fails)} leak(s)")
        for rel, label, ctx in fails[:8]:
            print(f"          /{rel}  →  {label}")
            print(f"              …{ctx.strip()}…")
        if len(fails) > 8:
            print(f"          … and {len(fails)-8} more")
        print("\n  A living person is named and nothing more. If one of these people has "
              "died,\n  record the death — do not silence the check.")
        return 1

    if not a.quiet:
        print(f"  ok    {ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
