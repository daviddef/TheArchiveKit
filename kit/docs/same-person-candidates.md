# Same-person candidates (prototype)

**Status: a prototype, tuned on one archive (Defranceschi), run once on two others (Lerena, Mazza), and wired into nothing.** `kit/tools/samepersonc*.py` proposes joins in a family tree for a person to look at. It never joins anyone, never writes to a tree, a roster or the Atlas, and a proposal is never a finding (the estate's rule: a `lead` is never a finding).

It is the idea behind a people-search site's "these records are one person", rebuilt to be inspectable: every proposal carries the reasons it was made, a tier that says how far to trust it, and a count of the namesakes it could be confused with. The matching knowledge is not kept here. Surname spellings, given-name forms and dated place names are read from the Record Atlas catalogues (`data/surname-families.json`, `data/given-name-families.json`, `data/place-names.json`), read-only.

## What it proposes

| Mode | Question | Evidence it can use |
|---|---|---|
| `father`, `mother` | who may be this person's parents? (an orphan's likely parents) | surname, dates, place, the candidate's other children, a mother's husband's surname, named-for-a-grandfather |
| `spouse` | who may be this person's husband or wife? | dates, place, overlap of adult lives |
| `same` | which other rows may be this same person written twice? | surname, given name, birth and death years, birth place, parents and spouse |

Input is one archive's `tree.json` (the Roots & Routes contract, `family-tree-page` skill) and its `place_map.json`. Any archive that has a tree page can run it on its own data.

## The signals

Every signal is a number and a sentence; their sum is a ranking aid, not a probability. Weights are set by hand, written in `samepersoncore.py`, and none was fitted to a result except the tier thresholds (below).

* **Relationships** are the strongest: the candidate's other children born where this person was, in the years that fit the spacing; a mother whose husband bears this person's surname. A sibling already bearing the same *whole* given name is a clash (a sibling who had died is not).
* **Surname** from the Atlas: `same`, `attested` and `rule` forms are strong, `lead` is weak, `case-by-case` is neutral, `not-same` blocks. Typography (case, spaces, hyphens, a spaced particle) is never a spelling; an accent is. For a mother or a spouse the surname is no evidence at all (a maiden name differs).
* **Given name** from the Atlas given-name families (Ivan = Johann = Giovanni = Zuane = Joannes). Whole names are compared: *Maria Anna* is not *Maria Teresa*.
* **Place** resolved to an Atlas place with the name of the year (Borgovecchio is Marenza before 1900, in the tests), then same place, within 25 km, or further. A place taken from a relative (`bpe`) and a place from another age (more than 40 years from the date) say nothing.
* **Dates** are ranges, never points: a parent is 13 to 60 years older (a mother 13 to 55), and stated ages are off by 3 to 8 years, so an estimated year (`bye`) is a wide range. A year nobody knows scores slightly above zero, not below an average one.
* **Blocks** remove a candidate: a parent dead before the birth (a recorded death only; an estimated death is not a death record), a gap outside 13 to 60, the person's own descendant, a register-grade different parent, a `not-same` surname. A recorded **sex mismatch is a penalty, not a block**, because some trees guess sex from a given name.

**Deceased people only.** A person is eligible only if the kit's own living rule (`living_rule.is_living`) says they are not living. An estimated death year does not release anyone born inside the living window. Nobody living is ever a subject or a candidate.

## Tiers

`strong`, `possible`, `weak`. A tier is a *calibrated* statement, not a feeling: `evaluate` hides every link the archive already asserts, one at a time, asks for it back, and picks for each kind the lowest score at which the tool's top proposal was right at least 90 % of the time (`strong`, and it needs a margin of 1.0 over the runner-up) or 50 % (`possible`), measured on one half of the cases (split by a hash of the id). The other half reports how those thresholds behave. **If no threshold reaches the target the tier is not offered.** On Defranceschi `strong` is offered only for a mother (score 6.5 with margin 1; 9 of 10 right on the calibration half, 3 of 3 on the test half: far too few cases to rely on). It is not offered for a father or a spouse; they top out at `possible`.

`same` has too few adjudicated pairs to calibrate (23) and always uses the default constants; the review header says so.

## Running it

```bash
KIT=node_modules/@daviddef/archive-kit/kit/tools
ATLAS="$HOME/Projects/Family Projects/Record Atlas"        # read-only

# 1. Does it work on this archive? (prints aggregate numbers only; nothing about a person)
python3 $KIT/samepersoncandidates.py evaluate --tree data/tree-page/tree.json --atlas "$ATLAS" --write-thresholds thr.json

# 2. A review list for people joined to no one. The file holds NAMES: write it outside every repo.
python3 $KIT/samepersoncandidates.py propose --tree data/tree-page/tree.json --atlas "$ATLAS" \
    --subjects orphans --thresholds thr.json --out ~/Desktop/review

# 3. A pair a reader decides against is never proposed again (ids only)
python3 $KIT/samepersoncandidates.py keep-apart kept-apart.json ID_A ID_B --relation same --why "two men of one name, two parishes"

# 4. How do rows the archive already adjudicated score? (pairs.json: [{"a","b","same":true|false}])
python3 $KIT/samepersoncandidates.py evaluate-same --tree data/tree-page/tree.json --atlas "$ATLAS" --pairs pairs.json
```

`evaluate` runs **strict**: an estimated year or a borrowed place counts as unknown, because an estimate worked out from the very relative being hidden would hand the tool the answer. `propose` also scores strictly, but lets an estimate *block* a gross contradiction (a father born 160 years after his child), which cannot flatter any candidate. `--lenient` scores estimates as wide ranges; the numbers it gives are circular and are shown below only to say so.

Nothing is written unless `--out`, `--cases`, `--write-thresholds` or `keep-apart` is given. `check-living` style gates do not read these files, which is why they must stay out of the repo.

## Evaluation on Defranceschi (aggregate numbers only)

The archive's `tree.json` (1,315 deceased people; the living are withheld by the builder) holds 340 father links, 411 mother links and 138 spouse links. For each, that person's own links were removed so they became an orphan, and the tool was asked to find the true partner among every other eligible person (median 445 candidates for a father, 414 for a mother, 1,314 for a spouse). **The numbers are conditional on the true parent being in the tree.** A real orphan's parents are often not in it, so precision on real orphans will be lower.

Leave-one-out, strict (an estimated year or a borrowed place counts as unknown), final code. "Top-1/3/10": the true person was ranked first, in the first three, in the first ten. "Random" is the chance of top-1 if the candidates were shuffled.

| Archive | Link | Cases | Top-1 | Top-3 | Top-10 | Median rank (of) | Random top-1 | Truth blocked |
|---|---|---:|---:|---:|---:|---|---:|---:|
| Defranceschi | father | 340 | 45.4 % | 63.7 % | 71.2 % | 2 (445) | 0.2 % | 4 |
| Defranceschi | mother | 411 | 33.1 % | 50.9 % | 73.4 % | 3.5 (414) | 0.3 % | 6 |
| Defranceschi | spouse | 138 | 15.5 % | 25.6 % | 43.2 % | 14.5 (1,314) | 0.1 % | 0 |
| Lerena (never tuned on) | father | 680 | 26.6 % | 38.6 % | 57.9 % | 7.5 (667) | 0.15 % | 6 |
| Lerena | mother | 665 | 25.8 % | 36.8 % | 44.7 % | 19 (655) | 0.15 % | 0 |
| Lerena | spouse | 515 | 4.6 % | 7.5 % | 13.3 % | 173.5 (1,097) | 0.09 % | 0 |
| Mazza (never tuned on) | father | 406 | 56.1 % | 81.6 % | 93.7 % | 1.5 (310) | 0.33 % | 6 |
| Mazza | mother | 392 | 54.1 % | 80.3 % | 94.9 % | 1.5 (299) | 0.34 % | 2 |
| Mazza | spouse | 352 | 39.2 % | 58.4 % | 77.7 % | 2.5 (599) | 0.18 % | 0 |

The weights were set while looking at Defranceschi and were not changed for B and C, so Lerena and Mazza are an honest out-of-sample check, and they vary a great deal: Mazza is far better than Defranceschi, Lerena worse (its spouse top-1 is 4.6 %, about 50 times a shuffle of the field, and useless in practice). A reader should not expect any figure here to carry over to another archive; run `evaluate` on it first.

**Register-read links against index-only links** (Defranceschi, the archive that records the grade). Father top-1 is 36.8 % where the hidden link was read in a register and 54.9 % where it came from an index; mother 29.4 % and 36.0 %. The index-only links are probably partly circular (the tree's own years and places for such people may have been filled in from those very links), so quote the register-read figures as the honest ones.

**Lenient mode** (estimates count as wide ranges) on Defranceschi: father 51.6 / 72.3 / 81.7 %, mother 40.5 / 64.1 / 81.5 %, spouse 32.2 / 48.4 / 61.4 % (top-1 / 3 / 10). These are circular, because an estimate can have been worked out from the relative being hidden. They are given only so nobody quotes them.

### Tiers on the held-out half (precision of the top proposal, per tier)

| Archive | Link | `strong` | `possible` | `weak` |
|---|---|---|---|---|
| Defranceschi | father | not offered | 53 % (64 of 120) | 22 % (11 of 49) |
| Defranceschi | mother | 3 of 3 (9 of 10 on the calibration half) | 41 % (20 of 49) | 29 % (41 of 143) |
| Defranceschi | spouse | not offered | 33 % (5 of 15) | 3.5 % (2 of 57) |
| Lerena | father | not offered | 49 % (of 115) | 15 % (of 227) |
| Lerena | mother | not offered | 56 % (of 114) | 11 % (of 222) |
| Lerena | spouse | not offered | not offered | 3.9 % (of 258) |
| Mazza | father | not offered | 59 % (of 193) | 0 of 2 |
| Mazza | mother | not offered | 54 % (of 189) | none |
| Mazza | spouse | not offered | 62 % (of 98) | 35 % (of 77) |

The `strong` tier (90 % right, with a margin of 1.0 over the runner-up) was reachable for one kind in one archive, a mother in Defranceschi, on 13 cases in all. In every other archive and kind the top proposal is never right often enough to be called `strong`. The `possible` thresholds differ enormously between archives (a score of 6.0 on Defranceschi, 1.1 on Mazza), so a threshold file is only good for the archive that made it.

### What carries the score (ablation; top-1 / top-10, Defranceschi unless stated)

| Take away | Father | Mother | Spouse |
|---|---|---|---|
| nothing (full model) | 45 / 71 % | 33 / 73 % | 16 / 43 % |
| the candidate's household | 32 / 61 % | 13 / 46 % | 13 / 47 % |
| the dates | 47 / 78 % | 34 / 77 % | 10 / 43 % |
| the surname | 36 / 69 % | 33 / 73 % | 16 / 43 % |
| the place | 41 / 67 % | 27 / 60 % | 0.5 / 5 % |
| the namesake and grandfather-naming signals | 48 / 76 % | 38 / 76 % | 16 / 43 % |
| place alone (the rest removed) | 11 / 61 % | 12 / 57 % | 4 / 32 % |
| dates alone (the rest removed) | 0.3 / 3 % | 0.3 / 3 % | 0.3 / 3 % |

On Defranceschi the household (the candidate's other children) and the place carry parent matching, and **the date signals and the namesake/naming signals do not help: removing them improves the result** (father top-10 71 to 78 %, 76 %). On Lerena and Mazza removing them is roughly neutral for parents (Mazza father 56.1 to 56.7 % without dates, Lerena 26.6 to 25.8 %), and dates carry a spouse (Mazza spouse falls from 39 % to 16 % without them). They were left in because they are the only protection against a gross contradiction and they matter for spouses, but a later version should look at them again.

### Namesake traps (father, top-1)

Where another age-plausible man of the same name and surname was among the candidates: Defranceschi 39.8 % against 56.1 % without; Lerena 15.2 % against 30.2 %; Mazza 40.9 % against 65.5 %. In 62 of Defranceschi's 220 trap cases the top proposal was the decoy. A namesake count is on every proposal; `strong` needs a margin; but neither can see a fact the tree does not hold.

### `same` (rows that may be one person), Defranceschi

Against the 23 pairs the archive had adjudicated: all 18 proven-one-person pairs were found (rank 1 for 15, `strong` for 16). Five stated-distinct pairs also scored high and were kept below `strong` only by the margin rule. These are rows from one register entry, the easy case, and `same` is not calibrated (the number of pairs is too small).

### Real orphans (Defranceschi, 683 people joined to no one; the list is not in this repository)

At the `possible` tier or better there is a proposal for 435 of the 683, counting a father, a mother, a spouse and a duplicate row each separately:

| Kind | People with a proposal | `strong` | `possible` |
|---|---:|---:|---:|
| father | 206 | 0 | 206 |
| mother | 43 | 2 | 41 |
| spouse | 192 | 0 | 192 |
| same row | 330 | 117 | 213 |

These are places to look. No proposal has been read against a register. Read by eye (a sample of the top proposals), the father and mother proposals are plausible and always the family's one surname, which is the very reason they cannot be told from other households; the `strong` `same` proposals include pairs the tool is right to put forward (the same man written in Latin and in Italian) and some it should not have called `strong` (two men of one name four years apart).

## What it cannot do (read before trusting it)

* **A one-name study is the hard case for names.** In Defranceschi nearly everyone carries one surname, so the surname separates fathers from strangers (it helps) but not one Defranceschi from another; a given name common to a family (Maria, Giovanni, Pietro) separates nobody. Mazza and Lerena (both multi-surname) were run once, and came out far better and worse than Defranceschi respectively, so the surname mix does not by itself decide it.
* **The household does most of the work.** Without the candidate's other children the mother's top-1 falls from 33 % to 13 % on Defranceschi (and 26 % to 7 % on Lerena, 54 % to 16 % on Mazza). For a real orphan with no known family, the best the tool can do is place and dates, which in a small parish is a short list, not an answer.
* **Namesakes are the trap.** Where the true father had a namesake who was also age-plausible, the tool ranked the truth first 40 % of the time against 56 % where there was none, and in 62 cases the top proposal *was* the namesake. The count is on every proposal (`namesakes`) and `strong` needs a margin, but a margin cannot see a fact the tree does not hold.
* **Strong is nearly unavailable for a parent.** At the default threshold (score 6 with margin 1) the top father proposal is wrong about 30 % of the time; the only region above 90 % (score 8 with margin 2) is 15 of 340 cases. A mother reaches `strong` only at 6.5, on 13 calibration and test cases together.
* **Sex is sometimes a guess** (the tree guesses from a first name), so a woman can be proposed as a father at a penalty instead of being blocked. It happened.
* **Spouse mode is weak.** Top-1 is 15 % (median rank 14.5 among 1,314), the best tier a spouse proposal reaches is `possible` (a score of 2.5, 5 right of 15 on the test half) and the rest are `weak` (2 right of 57), and without the children (which would reveal the answer) there is little to go on but a place and an age gap. It is included to be measured, not recommended.
* **`same` is not calibrated and its `strong` is too generous.** On the orphan run, 117 of its top proposals were `strong` at the default constants; by eye, most are one person written in two languages (a Latin and an Italian form of one given name, born in the same year and place), but the strong tier also holds pairs four years apart with the same name and a death year in common, which are as likely to be two cousins as one man. Read `namesakes` and the birth gap before believing one.
* **`same` finds duplicates, not distinct namesakes.** It found all 18 pairs the archive had proved to be one person (rank 1 for 15, strong tier for 16), but the five stated-distinct pairs it could score looked just as alike (same name, year and place) and only the margin kept them below `strong`. These pairs are rows drawn from one register entry, the easy case; rows from different sources with different spellings have no ground truth here.
* **Weights were set by hand and the code was changed while looking at this one archive's results** (the changes are listed in the pull request). The tier thresholds are fitted on one half and tested on the other, but the design itself has seen all of it. The Defranceschi figures are therefore optimistic. Lerena and Mazza were run once each with the same weights, unseen (the table above), which is what to trust more.

## Rules it keeps

* Nothing about a person goes into the Atlas or into any repo: the tool reads the catalogues, never writes them; its aggregate output names no one; the review list is written only where `--out` says and contains names.
* A form met in a register and not in the catalogue goes in through the Atlas's own tools (`surname_variants.py add`, `given_name_variants.py add`, `place_names.py add`), never into this tool's data. This tool has none.
* The result of a decision belongs in the archive, not here: accept a join by writing it in the archive's own data with its evidence grade (`doc`, `inf`, `lore`, `dna`); reject it with `keep-apart`.
