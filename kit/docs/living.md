# The living rule, and the gate that checks what is printed

David's rule (16 October 2026, tightened 25 October 2026): **a living person is anyone 80 or younger with no death recorded.**
They are named with their relationships and their town and country, and nothing more: no date, no record, no photograph.
A possible minor (an undated person with a living parent) is not published at all. The full standard is
`PERSON-PAGE-SPEC.md` section 8; this page is the code, the gate and how an archive adopts them.

## The line

There is one number: `living_rule.cutoff_year()` in Python, `cutoffYear()` in `kit/lib/person.js`. It is **this year minus
`LIVING_YEARS` (80)**, derived, never typed: **1946 in 2026, 1947 in 2027**. A person born *on or after* the line, with no death
record, is living. The boundary year is included (born 1946 is living in 2026; born 1945 is not).
`checkliving.py` used to read a second copy of the eighty from `living-words.json` (`presumeDeadAfter`); that key is gone.
No gate, page or archive should write the year or the eighty again.

## What frees a person from the rule, and what does not

| Evidence | Born on or after the line | Born before the line, or undated |
|---|---|---|
| A death **record** (a date, a year, a place, a burial, a register line) | dead | dead |
| A bare death **flag** (`dead: true`, `died: "deceased"`, no date, no place, no burial) | **still living** (the flag is the archive's belief, not evidence) | dead |
| A **public-source citation** (an ark, a passenger index, a newspaper) | **still living**: a source shows a birth or an arrival, never a death | not living, as before |
| A private tree entry | nothing | nothing |

The fault this closes: the rule used to treat a public-source citation as proof of death for anyone, so a man born in 1948 with
no death was published as dead, with his year, his parents, spouse and children, on a passenger-index line. Mazza, Defranceschi,
Lerena and Blažević each patched it archive-side (`cites_for_living`: withhold the citations from the rule for anyone with a birth
year). The kit now does it, and the same applies to an undated death flag.

`recorded_dead` / `recordedDead` is for a real record only. An archive that holds only a flag passes `undated_dead=True`
(`undatedDead`). `death_kind(died, buried, death_place, dead_flag, death_recorded)` and `deathKind(person)` classify a row into
`"record"`, `"flag"` or `None` in both languages, held to `death_cases` in the shared fixture. An adapter that knows a register line
records a death but not when it happened sets `deathRecorded: true` (a record), not `dead: true` (a flag).

```python
import living_rule as lr
lr.cutoff_year()                                    # 1946 in 2026
lr.is_living(birth_year, recorded_dead, citations, today_year, youngest_child_year, said_living, undated_dead)
lr.possible_minor(...same, parent_living, ..., undated_dead)   # unchanged for a dated person: never held out
```

The new arguments are keyword-compatible additions at the end: an archive that does not pass `undated_dead` still gets the old answer
for a flag (it passed `recorded_dead=True`), and an archive that already withheld citations (`cites_for_living`) gets the same
answers it did before. **The one behaviour change** is an archive that passed citations for a dated person inside the line: that
person is now living.

## The cases

`kit/data/living-rule-cases.json` is the one list both implementations answer: `python3 kit/tools/living_rule_selftest.py` and
`node kit/tools/checkperson_logic.mjs`. It covers the boundary (1945 out, 1946 in, and in 2027 1946 out and 1947 in through a per-case
`today`), a citation plus born 1946, 1947, 1980 (living), a citation plus a death record (dead), an undated flag plus born 1950
(living), born 1945 (not living), an undated person with a flag (dead, not a possible minor), and the unchanged possible-minor cases.
Both runners plant faults (a citation that frees a dated person, a flag read as a record, a cutoff typed as 1946, a cutoff one year
off, a strict `>`) and require the cases to catch each.

## The printed-year gate

```
python3 kit/tools/checkliving.py --dist dist --data src/data --years [--config standard.json] \
        [--allow-file data/living-year-allow.json] [--allow-prefix /feed/ ...] [--strict-allow] [--years-only] [--today-year N]
```

`checkliving.py` without `--years` is unchanged. With it, `kit/tools/livingyears.py` also fails the build if **any built HTML, JSON,
XML or text file prints a year or date on or after the line for a person the data says has no death**, whatever the person's own flag,
citations or page say. The person set is derived from the archive's own data the way the other gates read it (`rows_of`: name, born and
died keys, a living flag, "living" written where a date goes), by `living_rule`: birth year inside the window and no death record.
Three detectors:

| Detector | Fires on |
|---|---|
| `birth-shape` | the shape of a birth with a year on or after the line and no death beside it: `b. 1949`, `born 24 April 1949`, `(1950-)`, `"birthDate": "1949-04-24"`, in visible text, JSON-LD and the text attributes (meta content, alt, title). A death word within 90 characters after, a closed span, or a dead person of the data born within three years excuses it. A bare year is never screened by this detector. |
| `name-year` | a living person's name phrase with that person's own birth year within 80 characters after it or 40 before it. Exact namesakes of a dead person, and names inside a longer published name, are subtracted. |
| `json-row` | a row in a built `.json` with a birth field (`born`, `b`, `birth`, `birthYear`...) on or after the line and no death record. A bare flag counts as no death. |

A year that is not a living person's birth goes in a **registry** (`data/living-year-allow.json`, named in `standard.json` or by
`--allow-file`): entries `{text, why}` or `{file, contains, reason}` (the Mazza and Defranceschi, and the Lerena, files are read as they
stand; Lerena's `unpublished_deaths` slugs exempt that person's `/people/<slug>/` page and treat the name as a dead person's), each with a reason of at least 8 characters, or the gate refuses to run. The entry's text is removed from what the gate reads; an
entry that matched nothing is *stale*, counted, and a failure with `--strict-allow`. A built file that is not about people takes
`--allow-prefix`. In `standard.json`:

```json
"living_years": {"allow_file": "data/living-year-allow.json", "allow_prefixes": ["/gazetteer"], "data": "src/data"}
```

`checkstandard.py` ignores the block.

It refuses to pass (exit 1) on an empty build, an unreadable data file, a missing data directory, a data directory with no people in it,
and a run whose own probe (a planted fault through the real detectors) is missed. `python3 kit/tools/livingyears_selftest.py` plants one
fault per detector in a copy of a synthetic build, proves the controls (a dead person's birth beside a death, born one year before the
line, a copyright year, a sitemap date) pass, proves the line moves with the calendar, and proves the gate fails when its cutoff or its
flag handling is broken.

What it does not do: it reads a death only AFTER the year (a death word before it, as in «death registration 1983 · born 1948», is not an excuse; put such a line in the registry); it cannot see a person who is not in the archive's data (a newspaper's birth notice; the `birth-shape` detector
still reads the notice), and it cannot tell two people of one name apart (the namesake subtraction trades a possible miss for no noise).

## Adopting it (the re-pin)

1. Re-pin the kit (`package.json` and `package-lock.json` together; `checkpin.py`).
2. Pass `undated_dead=True` (or `undatedDead`) where the archive has only a death flag, and `recorded_dead` only for a real record.
3. Delete the archive-side `cites_for_living`-style workaround, or leave it: with the kit fixed it changes nothing. Keep `living_v2.py`'s
   interface; it is not deprecated *yet*, but its citation withholding and its own `cutoff` are now redundant, and a later archive-side
   change should read `living_rule.cutoff_year()` instead of `current year - LIVING_YEARS`.
4. Add `--years` to the archive's `checkliving` script, and a `living_years` block to `standard.json`. An archive's own gate (Mazza
   rule 7, Lerena `check-living-years`, Blažević `livingyears.py`, Defranceschi `check-living-v2` rule 7) keeps working and may be
   retired once the kit gate has run clean beside it for a release.
5. Expect people to change status: everyone born on or after the line who carried a public-source citation or a bare death flag and
   was published as dead is now living, and their year and page must go.

**Deprecation note.** The archives' own printed-year gates (above) and their `cites_for_living` helpers are superseded by this page. They
are not removed by the kit and their configuration keeps working unchanged; an archive should prefer `--years` and drop its copy at its next re-pin.
