"""Files a gate could not read, so that it cannot pretend it read them.

THE FAULT, IN ITS GENERAL FORM. The Falco session put it best on 23
September 2026, having found it in a name test of its own: «a refusal that
is not counted is indistinguishable from a match». Its test skipped a
candidate with a bare `continue` and never added them to the refused list,
so a person who could not be matched looked exactly like a person who had
been.

The kit had it too. Ninety-three skips across its tools, seventeen counted
and seventy-six not. Most of the seventy-six are honest filters — a file
that is not `.html` was never in scope, and counting it would be noise. The
ones that matter are the SWALLOWED READS: seven `check*` tools wrapped
`open` or `json.load` in `except: continue`, so a file they could not parse
left the denominator without a word.

`checkliving` was the worst of them, because a malformed people file dropped
every living person it held and the gate printed «0 flagged in the data ·
ok» — a sentence that reads as a fact about the archive rather than as a
failure to read one. Demonstrated before it was fixed: same build, one
living person, sound data caught it and a truncated file passed it.

WHAT A FILTER IS AND WHAT A REFUSAL IS, since only one of them belongs here.
A filter says «this was never in scope» — the wrong extension, a blank line,
a comment. A refusal says «this was in scope and I could not handle it». The
first is correct to pass over in silence. The second is the tool declining to
answer, and it has to say so, because the alternative is a verdict on a
question it never asked.

    import unread
    try:
        s = open(p).read()
    except OSError as e:
        unread.note(p, e); continue
    ...
    unread.refuse("rows")      # in a gate: prints and returns non-zero
    unread.mention("atlas")    # in a generator: prints, returns 0
"""

import os

_FILES = []


def reset():
    del _FILES[:]


def note(path, exc):
    """Record a file that was in scope and could not be read.

    DEDUPED BY PATH, because several of these tools walk the same tree twice
    — once to report and once to count — and one unreadable file listed twice
    reads as two. The first count in this estate that was wrong tonight was
    wrong for the same reason: a pattern that matched one element under two
    spellings and summed both.
    """
    if any(p == path for p, _ in _FILES):
        return
    _FILES.append((path, str(exc).split("\n")[0][:100]))


def files():
    return list(_FILES)


def _lines(label, verb):
    print("  %-5s %-10s %d file(s) could not be read, so this %s"
          % ("FAIL" if verb == "refuse" else "..", label, len(_FILES),
             "gate does not cover them" if verb == "refuse"
             else "run is incomplete"))
    for p, why in _FILES:
        print("          %s — %s" % (os.path.basename(p), why))


def refuse(label):
    """For a GATE. Returns 1 when anything was unreadable, else 0.

    A gate that could not read part of its subject has no honest verdict to
    give, so it gives none. This is the same reasoning as `checkliving`
    refusing an empty build rather than passing it: could-not-look is not
    nothing-wrong.
    """
    if not _FILES:
        return 0
    _lines(label, "refuse")
    return 1


def mention(label):
    """For a GENERATOR, which has output to produce either way.

    It still says what it skipped, because a map missing four places and a
    map missing none look identical once drawn.
    """
    if _FILES:
        _lines(label, "mention")
    return 0
