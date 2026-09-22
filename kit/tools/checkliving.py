#!/usr/bin/env python3
"""Refuse to ship a build that gives away a living person.

ONE GUARD, THREE POLICIES. Two were written separately on the same day — one
in the kit reading committed data for dates, one in D'Arcy reading the GEDCOM
for names — and they were never duplicates: they enforce different rules.

    named-bare   a living person is NAMED AND NOTHING MORE. Their name may
                 appear; no date of theirs may. The estate rule.
    absent       a living person is not published at all — not their dates and
                 not their name. Stricter. D'Arcy applies it at the boundary in
                 build_site_data.py, and this proves it held.
    declared     no people file to read, so the list is written by hand. The
                 children's site, which guards four boys and their grown-ups.

AND THE AGE RULE, under every policy: anyone more than EIGHTY YEARS OLD is
treated as deceased. An archive that cannot say whether somebody is alive has
to presume something, and this is what it presumes.

WHO IS LIVING comes from whichever source the archive has, and the archive
owns that question, not this file:

    a GEDCOM       richest, and gitignored, so only ever present locally
    committed data a living / presumedLiving / conf:"living" flag
    a declaration  a hand-written list

An archive with a GEDCOM passes its own lists in — see feed(). This keeps the
hard part in one place while leaving each archive to know its own people.

WHY DATES ARE TESTED AS EXACT STRINGS, and names as PHRASES WITH SUBTRACTIONS.
Both lessons were paid for, and rebuilding either would cost the same again:

  · Screening dates on BARE YEARS passes vacuously. On a genealogy site every
    year appears somewhere. Screening a name NEAR a date fires on every
    homonym. So dates are matched as the literal strings the data attaches to
    a living person. Identity lives in the data, not the markup.

  · A bare surname matches every page and a bare forename most of them, so a
    forbidden NAME is a phrase — given + surname, and the full recorded name.
    Two things must then be subtracted or it cries wolf and gets switched off:
    EXACT NAMESAKES, where a living person's name is also a published dead
    person's and the phrase cannot tell them apart; and LONGER PUBLISHED NAMES
    that merely contain it — "Bruce Atwell" sits inside "Eric George Bruce
    Atwell".

An archive that omits living people from its data altogether passes with
nothing to check, which is correct rather than a gap.
"""
import os
import re
import sys
import json
import html
import argparse
import datetime
import collections

import os.path as _p, sys as _sys
_sys.path.insert(0, _p.dirname(_p.abspath(__file__)))
import outdir as _outdir  # ARCHIVE_OUT beats --dist; see kit/tools/outdir.py

PRESUME_DEAD_AFTER = 80
MIN_PHRASE = 7

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


# ---- names -----------------------------------------------------------------

def norm(name):
    name = re.sub(r"\s*\(.*?\)", " ", name or "")
    name = re.sub(r"[\"“”]", " ", name)
    return " ".join(name.split())


def phrases_of(full):
    """The forms a page might use: the whole recorded name, and first + last."""
    parts = norm(full).split()
    if len(parts) < 2:
        return set()
    return {" ".join(parts), parts[0] + " " + parts[-1]}


def visible(src):
    s = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", src)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


# ---- reading the archive's own data ----------------------------------------

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
    m = YEAR.search(born or "")
    return bool(m) and (today.year - int(m.group(1))) > years


UNREADABLE = []          # data files this gate could not parse — see below


def from_data(data_dir, today):
    """Living people and their dates, out of the committed data.

    A FILE THIS CANNOT READ IS NOT A FILE WITH NOBODY IN IT. The parse
    failure below used to `continue`, so a malformed people file dropped
    every living person it held and the gate printed «0 flagged in the data
    · ok». Tested 23 September 2026: one living person, one page naming
    them, sound data — caught. The same build with a truncated JSON file —
    «0 flagged», exit 0. The gate passed while knowing nothing, and its own
    summary line read as a fact about the archive rather than as a failure
    to read one.

    The Falco session put the general form of this better than I can: a
    refusal that is not counted is indistinguishable from a match. It found
    it in a name test that skipped a person with `continue` and never added
    them to the refused list. This is the same shape in the one gate in this
    estate that must never be wrong, and it is the third instance tonight of
    a check reporting on a question it had not managed to ask.

    Unreadable files are collected and the caller refuses on them.
    """
    living, presumed, skipped = {}, 0, 0
    del UNREADABLE[:]
    for f in sorted(os.listdir(data_dir)) if os.path.isdir(data_dir) else []:
        if not f.endswith(".json"):
            continue
        try:
            j = json.load(open(os.path.join(data_dir, f), encoding="utf-8"))
        except Exception as e:
            UNREADABLE.append((f, str(e).split("\n")[0][:90]))
            continue
        for r in rows_of(j):
            flagged = any(r.get(k) is True for k in LIVING_KEYS) or \
                      str(r.get("conf", "")).lower() == "living"
            if not flagged:
                continue
            name = norm(first(r, NAME_KEYS))
            if not name or len(name) < 3:
                # A living person this gate cannot name is a living person it
                # cannot protect. Counted and printed rather than dropped.
                skipped += 1
                continue
            born, died = first(r, BORN_KEYS), first(r, DIED_KEYS)
            if older_than(born, PRESUME_DEAD_AFTER, today):
                presumed += 1
                continue
            dates = set()
            for blob in (born, died):
                for rx in (FULL_DATE, ISO_DATE, SLASH_DATE):
                    dates.update(m.group(0) for m in rx.finditer(blob))
            living.setdefault(name, set()).update(dates)
    return living, presumed, skipped


def published_names(data_dir):
    """Everyone the data does NOT mark living — needed to subtract namesakes."""
    out = set()
    for f in sorted(os.listdir(data_dir)) if os.path.isdir(data_dir) else []:
        if not f.endswith(".json"):
            continue
        try:
            j = json.load(open(os.path.join(data_dir, f), encoding="utf-8"))
        except Exception as e:
            # THE SAME SWALLOW AS `from_data`, IN ITS SIBLING. That one was
            # fixed earlier tonight and this was not looked at, which is the
            # ordinary way a fixed bug survives: the fix went where the
            # symptom was rather than where the pattern was. This set is the
            # published names that get SUBTRACTED from the leak search, so
            # losing a file here makes the gate noisier rather than quieter
            # — the safe direction, and still a lie about what was read.
            UNREADABLE.append((f, str(e).split("\n")[0][:90]))
            continue
        for r in rows_of(j):
            if any(r.get(k) is True for k in LIVING_KEYS):
                continue
            n = norm(first(r, NAME_KEYS))
            if n and len(n.split()) >= 2:
                out.add(n)
    return out


# ---- the checks ------------------------------------------------------------

def check_dates(pages, living, allow_files):
    """No literal date string the data attaches to a living person may appear."""
    forbidden = collections.defaultdict(set)
    for name, dates in living.items():
        for d in dates:
            forbidden[d].add(name)
    fails = []
    for rel, raw in pages.items():
        if rel in allow_files:
            continue
        text = visible(raw)
        for d, owners in forbidden.items():
            if d in text or d in raw:
                i = text.find(d)
                ctx = re.sub(r"\s+", " ", text[max(0, i - 50):i + 50]).strip()
                fails.append((rel, f"the date «{d}» — the data attaches it to "
                                   f"{', '.join(sorted(owners))} (living)", ctx))
                break
    return fails, len(forbidden)


def check_names(pages, living_names, publishable, allow, allow_files):
    """No living person's NAME PHRASE may appear, minus the two subtractions."""
    pub_names = {n for n in publishable if len(n.split()) >= 2}
    pub_phrases = set()
    for n in pub_names:
        pub_phrases |= {x.lower() for x in phrases_of(n)}

    forbidden = collections.defaultdict(set)
    for full in living_names:
        for ph in phrases_of(full):
            low = ph.lower()
            if len(low) < MIN_PHRASE or low in pub_phrases:
                continue                     # an exact namesake: indistinguishable
            forbidden[low].add(full)
    if not forbidden:
        return [], 0, 0, 0

    covers = {ph: sorted((n for n in pub_names if ph in n.lower() and len(n) > len(ph)),
                         key=len, reverse=True) for ph in forbidden}
    rx = re.compile(r"\b(" + "|".join(sorted(map(re.escape, forbidden), key=len,
                                             reverse=True)) + r")\b", re.I)
    fails, allowed_hits, covered_hits = [], 0, 0
    for rel, raw in pages.items():
        if rel in allow_files:
            continue
        text = visible(raw)
        for m in rx.finditer(text):
            ph = m.group(1).lower()
            window = text[max(0, m.start() - 40):m.end() + 40].lower()
            if any(longer.lower() in window for longer in covers.get(ph, ())):
                covered_hits += 1
                continue                     # part of a longer published name
            ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 70):m.end() + 70]).strip()
            if ph in allow or any(x in ctx.lower() for x in allow):
                allowed_hits += 1
                continue
            fails.append((rel, f"the name «{m.group(1)}» (living)", ctx))
    return fails, len(forbidden), allowed_hits, covered_hits


# ---- entry points ----------------------------------------------------------

def load_pages(dist):
    """Every built page, and a count of what disappeared while we looked.

    Several sessions work these repositories at once and `astro build` empties
    dist before refilling it, so a file listed by os.walk can be gone a
    millisecond later. This used to end in a FileNotFoundError traceback that
    read like a broken archive rather than a race — the same failure
    checkarchive.py already guards against, unlearnt in its sibling.
    """
    pages, vanished = {}, 0
    for root, _, files in os.walk(dist):
        for f in files:
            # AND THE JSON, WHICH THIS READ ONLY HTML FOR MONTHS.
            #
            # An atlas fetches its places from a .json in dist, a search box
            # fetches its index the same way, and both are served to anybody
            # who asks for the URL. This gate walked past every one of them,
            # so a living person could sit in atlas-data.json with a date and
            # a pin and the build would pass: the name never reaches a page as
            # text, it reaches the browser and is drawn.
            #
            # Raised by the Luwinski session, which has two children flagged
            # living in its emigration data and said plainly that check:living
            # guards the built pages and not that JSON. Measured across the
            # estate before changing anything: three archives DO carry living
            # names in served JSON, and every one of them is also the name of
            # a published dead person - a namesake, which published_names()
            # already subtracts. So nothing is leaking today. The blind spot
            # was real and the leak was not, and both halves are worth saying.
            # A KNOWN LIMIT, FROM THE D'ARCY SESSION, WHICH BUILT THE SAME
            # THING LOCALLY. A raw sweep over a 2.1MB search index reports 25
            # hits there and every one is noise - "George" inside George Pitt
            # D'Arcy, "Geraldine" inside Geraldine D'Arcy. That does not bite
            # HERE because the fault under named-bare is a DATE beside a living
            # name, not the name, and because published_names() subtracts
            # namesakes first: run over the whole estate this widening found
            # nothing and added no noise.
            #
            # It WOULD bite under --policy absent, where the name alone is the
            # fault. An archive on that policy with a search index should read
            # person-name FIELDS rather than raw text - {"k":"Person","t":name}
            # in a search index, "people":[{"n":name}] in atlas data - which is
            # what D'Arcy does locally over 917 names. Not built here because
            # no archive in the estate is on `absent`, and a structure this
            # tool guesses at is a structure it will get wrong.
            if not (f.endswith(".html") or f.endswith(".json")):
                continue
            p = os.path.join(root, f)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except FileNotFoundError:
                vanished += 1
                continue
            pages[os.path.relpath(p, dist).replace(os.sep, "/")] = text
    if vanished:
        print(f"check_living: {vanished} page(s) disappeared from {dist} while this "
              f"ran — another build is in flight. Refusing to pass on a partial read.")
        raise SystemExit(1)
    return pages


def report(fails, ok_line, quiet):
    if fails:
        print(f"  FAIL  living      {len(fails)} leak(s)")
        seen = set()
        for rel, what, ctx in fails:
            if what in seen:
                continue
            seen.add(what)
            print(f"          /{rel}  →  {what}")
            print(f"              …{ctx}…")
            if len(seen) >= 8:
                break
        if len(fails) > len(seen):
            print(f"          … and {len(fails)-len(seen)} more")
        print("\n  A living person is named and nothing more — and under the «absent» "
              "policy,\n  not named either. If one of these people has died, record the "
              "death;\n  do not silence the check.")
        return 1
    if not quiet:
        print(f"  ok    {ok_line}")
    return 0


def feed(dist, living_names, publishable, allow=(), allow_files=(), quiet=False,
         label=""):
    """For an archive that knows its own living people — a GEDCOM, usually.

    D'Arcy calls this. The archive answers «who is alive»; this file answers
    «did any of them reach the build», which is the part worth having once.
    """
    pages = load_pages(dist)
    if len(pages) < 5:
        print(f"checkliving: only {len(pages)} page(s) under {dist} — the build is "
              f"unfinished or in flight. Refusing to pass.")
        return 1
    fails, n, allowed, covered = check_names(
        pages, living_names, publishable, {x.lower() for x in allow}, set(allow_files))
    ok = (f"{len(pages)} pages carry none of {n:,} name phrases belonging to "
          f"{len(living_names):,} living people"
          + (f" — {allowed} declared, {covered} inside longer published names" if
             (allowed or covered) else "")
          + (f" · {label}" if label else ""))
    return report(fails, ok, quiet)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--data", default="src/data")
    ap.add_argument("--policy", default="named-bare",
                    choices=["named-bare", "absent", "declared"])
    ap.add_argument("--declared", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    a.dist = _outdir.resolve(a.dist)
    today = datetime.date.today()

    if not os.path.isdir(a.dist):
        print(f"checkliving: no {a.dist} — build first")
        return 1
    pages = load_pages(a.dist)
    # AN IN-FLIGHT BUILD IS NOT A BUILD, and for this gate the dangerous
    # direction is the opposite of the usual one: a page not yet copied
    # cannot leak, so a run that straddles somebody else's build reports a
    # clean estate it never saw. Fingerprinted here, checked before the
    # verdict is printed.
    _before = _outdir.fingerprint(a.dist)
    if len(pages) < 5:
        print(f"checkliving: only {len(pages)} page(s) under {a.dist} — the build is "
              f"unfinished or in flight. Refusing to pass.")
        return 1

    if a.policy == "declared" or a.declared:
        path = a.declared or os.path.join(a.data, "living.json")
        if not os.path.exists(path):
            print(f"checkliving: no declaration at {path}. This guard is only as good "
                  f"as its list, so a missing list is a failure, not a pass.")
            return 1
        decl = json.load(open(path, encoding="utf-8"))
        allow = {x.lower() for x in decl.get("allow", [])}
        allow_files = set(decl.get("allowFiles", []))
        names, terms = [], []
        for p in decl.get("living", []):
            who = p.get("initials") or "?"
            for n in p.get("forbid", []):
                if n:
                    terms.append((re.compile(r"\b" + re.escape(n) + r"\b", re.I),
                                  f"{who}: the name «{n}»"))
            if p.get("born"):
                terms.append((re.compile(r"\b" + re.escape(str(p["born"])) + r"\b"),
                              f"{who}: the birth year {p['born']}"))
            names.append(who)
        if not terms:
            print("checkliving: the declaration forbids nothing — nothing to check.")
            return 1
        fails = []
        # AN ALLOW THAT SILENCES A FINDING HAS TO BE COUNTED. `check_names`
        # tallies `allowed_hits` for exactly this and this branch did not, so
        # a declaration could suppress every hit on the page and read the same
        # as a page with no hits on it. It also means a STALE allow — one
        # nobody has matched for months — is invisible, and an exemption
        # nobody revisits is the estate's oldest complaint about itself.
        skipped_files, allowed_hits = 0, 0
        for rel, raw in pages.items():
            if rel in allow_files:
                skipped_files += 1
                continue
            for rx, lbl in terms:
                m = rx.search(raw)
                if not m:
                    continue
                ctx = re.sub(r"\s+", " ", raw[max(0, m.start() - 45):m.end() + 45])
                if any(x in ctx.lower() for x in allow):
                    allowed_hits += 1
                    continue
                fails.append((rel, lbl, ctx))
                break
        said = ""
        if allowed_hits or skipped_files:
            said = (f" — {allowed_hits} hit(s) allowed by the declaration, "
                    f"{skipped_files} file(s) exempt")
        return report(fails, f"{len(pages)} pages carry no name and no birth year "
                             f"for {', '.join(names)}{said}", a.quiet)

    # derived: read the archive's own committed data
    living, presumed, skipped = from_data(a.data, today)
    if UNREADABLE:
        # THE GATE CANNOT ANSWER, SO IT MUST NOT PASS. A file it could not
        # parse holds an unknown number of living people, and every one of
        # them is invisible to every check below.
        print(f"  FAIL  living      {len(UNREADABLE)} data file(s) could not be read, "
              f"so this gate does not know who is living")
        for f, why in UNREADABLE:
            print(f"          {f} — {why}")
        return 1
    if skipped:
        print(f"  FAIL  living      {skipped} person(s) flagged living carry no usable "
              f"name in the data, so nothing can be searched for")
        return 1
    if not a.quiet:
        print(f"  living: {len(living)} flagged in the data, {presumed} presumed dead "
              f"by the {PRESUME_DEAD_AFTER}-year rule · policy {a.policy}")
    fails, ndates = check_dates(pages, living, set())
    extra = ""
    if a.policy == "absent":
        nf, nph, allowed, covered = check_names(
            pages, set(living), published_names(a.data), set(), set())
        fails += nf
        extra = f", {nph:,} name phrases"
    if _outdir.settled(a.dist, _before, 'living'):
        return 1
    ok = (f"{len(pages)} pages — no living person reaches the build "
          f"({len(living)} living, {ndates} dates{extra} guarded)")
    return report(fails, ok, a.quiet)


if __name__ == "__main__":
    sys.exit(main())
