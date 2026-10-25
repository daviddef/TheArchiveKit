#!/usr/bin/env python3
"""The estate's one definition of who counts as living, and of who is held out.

Written 16 October 2026 after eight archives each carried their own test: Mazza's
80-year `datesHidden`, D'Arcy's and Blazevic's 100-year bound, Defranceschi's and
Falco's hand-set flags, Lerena's one-line register. David's ruling replaces them:

  LIVING  =  80 or younger with no death recorded.
  Not the broader "the tree cannot show they died" (Mazza's presumedLiving, true of
  anyone with no dates, 280 of whom were plainly dead).

  1. A recorded death or burial means dead. A DEATH RECORD is a date, a place, a burial,
     a register line: something that says the person died. A bare FLAG ("deceased", dead:
     true, no date, no place, no burial) is NOT a death record for a person whose birth
     year is inside the living window (25 October 2026): it is the archive's belief, not
     evidence, and the person stays living until a record is found. (For a person with no
     birth year a bare flag still means dead: nothing makes them living.)
  2. A citation from a public record source (kit/data/public-sources.json: FamilySearch,
     MyHeritage records, Findmypast, NAA and the like) means an UNDATED person is NOT
     living: what that source says may be shown. It NEVER frees a person with a birth
     year inside the window (25 October 2026): a passenger index, an ark or a newspaper
     shows that someone was born or arrived, never that they died, and a man born in 1948
     was published as dead, with his year, on exactly that. Only a death record does.
     A private family-tree entry does not count as a source at all.
  3. Age is by year, and the line is ONE derived number, cutoff_year(): today's year
     minus LIVING_YEARS (1946 in 2026, 1947 in 2027). Born in that year or later is
     living (so born 1946 is living in 2026 and born 1945 is not); every gate in the kit
     and in the archives reads the cutoff from here and none types a year. A person with
     NO birth year cannot be shown to be 80 or younger,
     so is not living by this test, EXCEPT an undated parent whose youngest known
     child was born 60 years ago or less (17 October 2026): a parent is about twenty
     years older than a child, so that parent is 80 or younger. They are living, not
     held out.
  4. HELD OUT is separate from LIVING. Two exceptions (David, 16 October 2026): an
     UNDATED person with a living parent, who might be a child, and named people
     whose privacy is promised by id (the DNA tester). A held-out person is not
     published at all: no page, no name as anyone's relative.
        possible minor = not recorded dead, no public source, no birth year, and a
        living parent.
     A child with a KNOWN birth year under 18 is NOT held out: David ruled on
     16 October 2026 that every child follows the same standard as any living
     person (name, relationships, town and country, a page, no dates).

The cases that pin all of this down live in kit/data/living-rule-cases.json, read by this
module's self-test AND by the JavaScript port in kit/lib/person.js, so the two cannot drift.

An archive imports this instead of writing its own test:

    sys.path.insert(0, ".../node_modules/@daviddef/archive-kit/kit/tools")
    import living_rule as lr
    lr.is_living(birth_year, recorded_dead, citations, today_year)
    lr.cutoff_year(today_year)        # the living line: born on or after it, no death record, is living

`citations` is a list of strings (provider, URL or title of each source).
"""
import json
import os
import re
import datetime

LIVING_YEARS = 80
# An UNDATED person is living when their youngest child with a known birth year was born this many years ago
# or less: a parent is about twenty years older than their child, so a child born 60 years ago or less puts
# the parent at 80 or younger (David, 17 October 2026, after D'Arcy found 8 such parents published as dead).
CHILD_LIVING_YEARS = 60

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "data", "public-sources.json")


def _load():
    with open(_SRC, encoding="utf-8") as f:
        d = json.load(f)
    return ([p.lower() for p in d["providers"]], [x.lower() for x in d["excluded"]])


PROVIDERS, EXCLUDED = _load()


def public_source(citations):
    """True if any citation names a public record source and is not a private tree entry."""
    for c in citations or []:
        s = str(c).lower()
        if "familysearch" in s:      # always: FamilySearch hides its living people
            return True
        if any(x in s for x in EXCLUDED):
            continue
        if any(p in s for p in PROVIDERS):
            return True
    return False


def this_year():
    return datetime.date.today().year


def cutoff_year(today_year=None):
    """THE LIVING LINE, derived and never typed: this year minus LIVING_YEARS (1946 in 2026).
    A person born in this year or later, with no death record, is living. Boundary included."""
    return int(today_year or this_year()) - LIVING_YEARS


def in_window(birth_year, today_year=None):
    """True if a known birth year falls inside the living window (on or after cutoff_year())."""
    return birth_year is not None and int(birth_year) >= cutoff_year(today_year)


# What a death value that is only a FLAG looks like. Anything else in a died/buried field (a year, a
# date, a place, a register) is a death RECORD.
FLAG_WORDS = re.compile(r"^(true|yes|y|dead|deceased|died|d\.?|death|buried|\(?deceased\)?|d\.s\.p\.?)$", re.I)


def death_kind(died=None, buried=None, death_place=None, dead_flag=False, death_recorded=False):
    """Classify what an archive holds about a death: "record", "flag" or None.
    record: a date, a year, a place, a burial: something that says the person died.
    flag:   only a bare yes/deceased with no date and no place (dead_flag=True, or the word alone in a field).
    death_recorded=True is an adapter saying "a register line records the death, undated": a record.
    Empty, "living", "alive", "unknown", "?" and dashes are no death at all.
    Twin of recordedDead/undatedDeadFlag in kit/lib/person.js, held to `death_cases` in
    kit/data/living-rule-cases.json."""
    def one(v):
        if v is None or v is False:
            return None
        if v is True:
            return "flag"
        s = str(v).strip()
        if re.fullmatch(r"(|living|alive|—|-|–|\?|unknown|none)", s, re.I):
            return None
        return "flag" if FLAG_WORDS.match(s) else "record"
    kinds = [one(died), one(buried), "record" if (death_place and str(death_place).strip()) else None,
             "record" if death_recorded else None,
             "flag" if dead_flag else None]
    if "record" in kinds:
        return "record"
    return "flag" if "flag" in kinds else None


def recent_child(youngest_child_year, today_year=None):
    """True if a known child was born CHILD_LIVING_YEARS ago or less."""
    if youngest_child_year is None:
        return False
    return ((today_year or this_year()) - int(youngest_child_year)) <= CHILD_LIVING_YEARS


def is_living(birth_year, recorded_dead, citations=(), today_year=None, youngest_child_year=None,
              said_living=False, undated_dead=False):
    """David's rule. birth_year: int or None. recorded_dead: any death or burial event, dated or not.
    youngest_child_year: the birth year of this person's youngest child with a known birth year, or None.
    An undated person with no recorded death and no public source is living if that child is 60 years old
    or younger; a dated person is judged by their own birth year alone.
    said_living: the archive's own data says in so many words that the person is living (Booyzen records
    three people so, with no year). David ruled on 17 October 2026 that for Booyzen such a statement counts;
    an archive passes True only for that. Default False: no year and no statement is not living.
    undated_dead: the archive holds only a bare FLAG that the person is dead (no date, no place, no burial).
    It is not a death record: for a person born inside the window it is ignored (they stay living), and
    for an undated person it means dead. recorded_dead is for a real record only (see death_kind).

    A public-source citation can never free a person born inside the window (25 October 2026): the
    window is decided by the birth year and a death RECORD alone. For an undated person a public
    source still means not living, as before."""
    if recorded_dead:
        return False
    if birth_year is not None:
        return in_window(birth_year, today_year)
    if public_source(citations) or undated_dead:
        return False
    return bool(said_living) or recent_child(youngest_child_year, today_year)


def possible_minor(birth_year, recorded_dead, citations=(), parent_living=False, today_year=None,
                   youngest_child_year=None, said_living=False, undated_dead=False):
    """Held out: an UNDATED person with a living parent, who might be a child.
    Not for anyone recorded dead or evidenced by a public source, and not for a child
    whose birth year is known (David, 16 Oct 2026: known children follow the standard)."""
    if recorded_dead or public_source(citations) or undated_dead:
        return False
    if birth_year is not None:
        return False
    if recent_child(youngest_child_year, today_year):
        return False        # a parent of a recent child is an adult: living, not held out
    if said_living:
        return False        # the archive's own data says this person is living (it knows what the page may not
                            # carry, e.g. a living child's birth year): a known child follows the standard
    return bool(parent_living)


def is_held_out(person_id, birth_year, recorded_dead, citations=(), parent_living=False,
                held_ids=(), today_year=None, youngest_child_year=None, said_living=False, undated_dead=False):
    """Not published at all: the promised-by-id people, and possible minors."""
    if str(person_id) in {str(i) for i in held_ids}:
        return True
    return possible_minor(birth_year, recorded_dead, citations, parent_living, today_year, youngest_child_year, said_living,
                          undated_dead)


# ---- what a living person's PLACE may be (item 5 of the standard) -------------------------
# "Full town and country, never a street, an address-like string or an institution (a
# hospital, a care home)." A heuristic, and deliberately conservative: it refuses rather than
# shows. Written once here and once in kit/lib/person.js (placeIsAddressLike); BOTH are held to
# the `place_cases` in kit/data/living-rule-cases.json, so they cannot drift.
_INSTITUTION = re.compile(
    r"\b(hospital|clinic|infirmary|hospice|sanatorium|nursing|care home|rest home|retirement|"
    r"aged care|maternity|medical cent(?:re|er))\b", re.I)
# a street-type word that ENDS a comma-part and has a word before it: "Main St", "High Street";
# not "St Louis", "Lane Cove" or "Road Town", where the word is part of a town's name
_STREET = re.compile(
    r"(?:^|[,;])\s*[^,;]*\S\s+(?:street|st|road|rd|avenue|ave|lane|ln|boulevard|blvd|highway|hwy)\.?\s*(?=[,;]|$)", re.I)


def address_like(place):
    """True if `place` looks like an address or an institution rather than a town."""
    s = str(place or "")
    return bool(re.search(r"\d", s) or _INSTITUTION.search(s) or _STREET.search(s))
