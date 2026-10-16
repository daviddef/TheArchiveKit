#!/usr/bin/env python3
"""The estate's one definition of who counts as living, and of who is held out.

Written 16 October 2026 after eight archives each carried their own test: Mazza's
80-year `datesHidden`, D'Arcy's and Blazevic's 100-year bound, Defranceschi's and
Falco's hand-set flags, Lerena's one-line register. David's ruling replaces them:

  LIVING  =  80 or younger with no death recorded.
  Not the broader "the tree cannot show they died" (Mazza's presumedLiving, true of
  anyone with no dates, 280 of whom were plainly dead).

  1. A recorded death or burial, dated or not, means dead.
  2. At least one citation from a public record source (kit/data/public-sources.json:
     FamilySearch, MyHeritage records, Findmypast and the like) means NOT living:
     what that source says may be shown. A private family-tree entry does not count.
  3. Age is by year: today's year minus the birth year. 80 or less is living, 81 or
     more is not. A person with NO birth year cannot be shown to be 80 or younger,
     so is not living by this test.
  4. HELD OUT is separate from LIVING. Two exceptions (David, 16 October 2026): a
     person who is living-or-undated and might be a child, and named people whose
     privacy is promised by id (the DNA tester). A held-out person is not published
     at all: no page, no name as anyone's relative.
        possible minor = not recorded dead, no public source, and EITHER a birth
        year giving an age under 18, OR no birth year and a living parent.

An archive imports this instead of writing its own test:

    sys.path.insert(0, ".../node_modules/@daviddef/archive-kit/kit/tools")
    import living_rule as lr
    lr.is_living(birth_year, recorded_dead, citations, today_year)

`citations` is a list of strings (provider, URL or title of each source).
"""
import json
import os
import datetime

LIVING_YEARS = 80
MINOR_AGE = 18

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


def is_living(birth_year, recorded_dead, citations=(), today_year=None):
    """David's rule. birth_year: int or None. recorded_dead: any death or burial event, dated or not."""
    if recorded_dead:
        return False
    if public_source(citations):
        return False
    if birth_year is None:
        return False
    y = today_year or this_year()
    return (y - int(birth_year)) <= LIVING_YEARS


def possible_minor(birth_year, recorded_dead, citations=(), parent_living=False, today_year=None):
    """Held out: might be a child. Not for anyone recorded dead or evidenced by a public source."""
    if recorded_dead or public_source(citations):
        return False
    y = today_year or this_year()
    if birth_year is not None:
        return (y - int(birth_year)) < MINOR_AGE
    return bool(parent_living)


def is_held_out(person_id, birth_year, recorded_dead, citations=(), parent_living=False,
                held_ids=(), today_year=None):
    """Not published at all: the promised-by-id people, and possible minors."""
    if str(person_id) in {str(i) for i in held_ids}:
        return True
    return possible_minor(birth_year, recorded_dead, citations, parent_living, today_year)
