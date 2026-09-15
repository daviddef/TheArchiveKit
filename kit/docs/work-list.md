# The work list

Every other register in these archives answers *what do we know* — searched,
open questions, gaps, errands, corrections. None of them answered **what is
being done**, so that lived in a chat window, which is the one place that does
not survive the session.

Eight lists, one shape. `worklist.json` in the archive, rendered by
`WorkList.astro`, checked by two gates on every build.

## A row

```json
{ "n": 13,
  "state": "next",
  "owner": "the Blazevic session",
  "since": "2026-09-15",
  "what": "Waiting on the Državni arhiv u Gospiću",
  "note": "Markdown. Say why it matters and what would move it.",
  "covers": ["register:letters/gospic", "letter:EMAIL-gospic.txt"] }
```

`state` is one of **running · next · blocked · done · struck**. `owner` is who
has to move it — this archive's session, another archive's, or a person. *A row
with no owner is how a list becomes wallpaper*, which is why the gate refuses a
build without one. `since` is the date it was raised, so an item blocked for
five weeks looks different from one raised this morning.

## Recording is not enough. Reconcile.

This is the part that sessions skip, and it is the part that matters.

`checkworklist.py` validates the rows a list **has**. It cannot see a row that
is **missing**, and on 15 September 2026 that cost exactly what you would
expect: five letters had been sent to archives and parish offices, four had
rows, and the fifth — the reply that named three further doors, and so the
reason three of the other rows existed at all — had none. Every row present
looked fine in isolation. The list was only wrong in what it did not say.

**An absence cannot be found by looking at what is there.** It needs a second
list to count against. So an archive declares where its outstanding work
actually lives:

```json
"accounts": [
  { "prefix": "register", "noun": "pending register rows",
    "file": "sources/searched.json", "rows": "rows",
    "when": {"outcome": "pending"}, "key": "key", "label": "src" },
  { "prefix": "letter", "noun": "sent letters",
    "dir": "requests/sent", "ignore": ["README.md"] }
]
```

and `checkcovers.py` then refuses in **both** directions:

* something outstanding that no row covers — the list is too short;
* a `covers` entry naming a key or a file that is gone — the list has gone
  stale, which is what happens when a pending row is finally retired and the
  work-list row pointing at it is left behind.

### Two things about this that are deliberate

**No fuzzy matching.** There is no guessing from titles. That register learned
the lesson at a cost: *Senj marriages, 1734–1858* is genuinely unopened while
*Senj marriages, 1859–1920* has been read end to end, and any gate matching on
names would have called the first one stale. A declared key is exact; a guess is
not, and **a gate that cries wolf gets switched off**.

So an archive whose rows carry no stable identifier cannot use that half of the
gate until it adds one. That is the honest answer rather than a heuristic, and
the gate says so by name rather than passing quietly.

**Declaring nothing is not an exemption.** Silence is the failure this exists to
end. An archive with no `accounts` gets a note on every build listing what is
going uncounted — it does not fail, because a session has to be able to adopt
this without its archive going red first. But the note does not go away on its
own.

### Where each archive stands, 15 September 2026

| Archive | Declared | What is uncounted |
|---|---|---|
| Blažević | **yes** | nothing — 7 pending register rows, 5 sent letters, all covered |
| D'Arcy | no | `errands.json` 62 rows, `questions.json` 11, `searched.json` 293, `requests/` 8 files — **none has a stable key** |
| Defranceschi | no | `searched.json` 273 rows, `errands.json` 28, `requests/` 2 files |
| Lerena | no | `errands.json` 40 rows, `requests/` 8 files |
| Mazza | no | `searched.json` 115 rows |
| Booyzen | no | `requests/` 8 files |
| Falco | no | nothing machine-readable: `/searched/` is hand-written prose, so **there is no list to count against at all** |

Adding a key is the unglamorous prerequisite and there is no way round it. The
work is: give each row of the register a short stable string, never derived from
its title, and never reused when a row is retired.

## The two gates

    python3 .../kit/tools/checkworklist.py --root .   # the rows that are there
    python3 .../kit/tools/checkcovers.py   --root .   # the rows that are not

Both find the repository by walking up, so they behave the same whether npm runs
them from `site/` or a person runs them from the repo root.

## Seeing all eight at once

    ./board.sh          # writes a page with every archive's list side by side

The cross-archive session keeps its list at the kit repo root. The work that
belongs to no single archive is exactly the work that went untracked longest, so
it is not exempt from the rule it is enforcing.
