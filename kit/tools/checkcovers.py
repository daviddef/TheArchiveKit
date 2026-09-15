#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refuse when outstanding work exists on disk with no work-list row against it.

checkworklist.py checks the rows a list HAS. Nothing checked for the rows it was
MISSING, and on 15 September 2026 that cost exactly what you would expect: five
letters had been sent to archives and parish offices, four of them had rows, and
the fifth — the reply that named three further doors, and so the reason three of
the other rows existed at all — had none. Every row present looked fine in
isolation. The list was only wrong in what it did not say.

An absence cannot be spotted by looking at what is there. It needs a second list
to count against. Written first in the Blazevic archive against its two exact
lists; this is that gate, generalised, because every archive has the same hole
and none of the others had noticed it either.

DECLARING WHAT TO COUNT. An archive says where its outstanding work lives, in
its own worklist.json:

    "accounts": [
      { "prefix": "register", "noun": "pending register rows",
        "file": "sources/searched.json", "rows": "rows",
        "when": {"outcome": "pending"}, "key": "key", "label": "src" },
      { "prefix": "letter", "noun": "sent letters",
        "dir": "requests/sent", "ignore": ["README.md"] }
    ]

and a row then declares what it answers for:

    { "n": 13, "what": "Waiting on the Drzavni arhiv u Gospicu",
      "covers": ["register:letters/gospic", "letter:EMAIL-gospic.txt"] }

This refuses when

  * something outstanding is covered by no row — the missing-row case; or
  * a `covers` entry names a key or a file that does not exist — the rot case,
    which is what happens when a pending row is finally retired and the
    work-list row pointing at it is left behind.

Both directions matter. The first catches a list that is too short; the second
catches one that has gone stale.

WHY MATCHING IS EXPLICIT AND NOT CLEVER. There is no fuzzy match on titles here,
deliberately. The Blazevic register learned this at a cost: "Senj marriages,
1734-1858" is genuinely unopened while "Senj marriages, 1859-1920" is read end
to end, and any gate matching on names would have called the first one stale. A
declared key is exact. A guess is not, and a gate that cries wolf gets switched
off. An archive whose register rows carry no stable key cannot use the register
half of this until it adds one, and that is the honest answer rather than a
heuristic.

THE BACKLOG IS A RATCHET, NOT A CLIFF. Turning enforcement on in an archive
that has never reconciled means every outstanding item fails the build at once
— 143 of them across four archives the first time this was tried — and the only
ways out are to write 143 rows in one sitting or to leave the whole thing
switched off. Both are how a gate ends up disabled.

So a work list may declare what it has NOT yet reconciled:

    "unreconciled": 31

and the build fails only when the real number is HIGHER than that. It can
never get worse, the count is printed on every build so it is impossible to
forget, and each covering row added lets the session lower the number by one.
A declaration that is too generous is caught too: when the real number is
lower, this says so and names the figure to drop to, so the ratchet cannot be
left slack.

AN ARCHIVE THAT DECLARES NOTHING IS NOT SILENTLY EXCUSED. It would defeat the
purpose to pass quietly: silence is the failure this gate exists to end. So when
there is no declaration, this looks for the files an archive of this estate
usually has, and prints what is going uncounted — without failing the build,
because a session has to be able to adopt this without its archive going red
first.

    python3 .../checkcovers.py --root .
"""
import argparse
import json
import os
import sys

USUAL_FILES = ["sources/searched.json", "site/src/data/searched.json",
               "site/src/data/errands.json", "site/src/data/questions.json"]
USUAL_DIRS = ["requests/sent", "requests", "letters/sent"]
PENDING_HINTS = [("outcome", "pending"), ("state", "open"), ("status", "pending"),
                 ("status", "open"), ("state", "next")]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def rows_of(blob, path="rows"):
    cur = blob
    for seg in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(seg)
    if cur is None and isinstance(blob, list):
        return blob
    return cur if isinstance(cur, list) else []


def files_in(d, ignore):
    out = []
    for fn in sorted(os.listdir(d)):
        if fn.startswith(".") or fn in ignore:
            continue
        if os.path.isdir(os.path.join(d, fn)):
            continue
        out.append(fn)
    return out


def undeclared_report(root, name):
    """What this archive is NOT counting. Never fails; always speaks."""
    found = []
    for rel in USUAL_FILES:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        try:
            rows = rows_of(load(p))
        except Exception:
            continue
        if not rows:
            continue
        keyed = sum(1 for r in rows if isinstance(r, dict) and r.get("key"))
        pend = 0
        for field, val in PENDING_HINTS:
            n = sum(1 for r in rows if isinstance(r, dict)
                    and str(r.get(field, "")).lower() == val)
            pend = max(pend, n)
        # The count is GUESSED from field names, so it is offered as a guess.
        # This gate's own argument is that a declared key beats a clever match;
        # the same applies to its prose.
        bit = f"{rel} ({len(rows)} rows"
        if pend:
            bit += f", of which perhaps {pend} look outstanding"
        if rows and not keyed:
            bit += "; no stable key on its rows, so it needs one first"
        found.append(bit + ")")
    for rel in USUAL_DIRS:
        p = os.path.join(root, rel)
        if os.path.isdir(p):
            n = len(files_in(p, {"README.md", "REPLIES.md"}))
            if n:
                found.append(f"{rel} ({n} files)")
            break
    if found:
        print(f"  note  {name}: nothing declared to count the work list against. "
              f"On disk: {'; '.join(found)}.")
        print(f"        Add \"accounts\" to worklist.json to have this counted — "
              f"until then a missing row cannot be seen.")
    else:
        print(f"  note  {name}: nothing declared, and nothing obvious on disk to count against.")
    return 0


def find(root):
    """The work list, and the REPO ROOT that declared paths resolve against.

    npm runs these scripts from site/, so --root . is the site and not the
    repository — while an archive's outstanding work (sources/, requests/) sits
    beside the site, not inside it. Both are found by walking up from wherever
    this was pointed, so it behaves the same whether a person runs it from the
    repo root by hand or npm runs it from site/.
    """
    # Which pattern matched says where the repository root is: finding
    # src/data/worklist.json means the directory searched IS the site, and the
    # repo is its parent. Returning the site as the root was the first version
    # of this, and it reported all fifteen of an archive's declarations as
    # pointing at things that no longer existed — a gate accusing a correct list
    # because it was standing in the wrong place.
    here = os.path.abspath(root)
    for _ in range(4):
        for rel, up_levels in (("site/src/data/worklist.json", 0),
                               ("src/data/worklist.json", 1),
                               ("worklist.json", 0)):
            p = os.path.join(here, rel)
            if os.path.exists(p):
                repo = here
                for _ in range(up_levels):
                    repo = os.path.dirname(repo)
                return p, repo
        up = os.path.dirname(here)
        if up == here:
            break
        here = up
    return None, os.path.abspath(root)


def check(root, name):
    wl, root = find(root)
    if not wl:
        print(f"  FAIL  {name}: no worklist.json")
        return 1
    work = load(wl)
    accounts = work.get("accounts") or []
    if not accounts:
        return undeclared_report(root, name)

    bad = []
    outstanding = {}
    known = set()

    for acc in accounts:
        pre = acc.get("prefix")
        if not pre:
            bad.append("an accounts entry has no prefix")
            continue
        if acc.get("file"):
            p = os.path.join(root, acc["file"])
            if not os.path.exists(p):
                bad.append(f"accounts names {acc['file']!r}, which does not exist")
                continue
            keyf = acc.get("key", "key")
            labf = acc.get("label", "what")
            when = acc.get("when") or {}
            for r in rows_of(load(p), acc.get("rows", "rows")):
                if not isinstance(r, dict):
                    continue
                k = r.get(keyf)
                if k in (None, ""):
                    continue
                token = f"{pre}:{k}"
                known.add(token)
                if all(str(r.get(f, "")).lower() == str(v).lower() for f, v in when.items()):
                    outstanding[token] = str(r.get(labf, "?"))[:60]
        elif acc.get("dir"):
            d = os.path.join(root, acc["dir"])
            if not os.path.isdir(d):
                bad.append(f"accounts names {acc['dir']!r}, which is not a folder")
                continue
            for fn in files_in(d, set(acc.get("ignore") or [])):
                token = f"{pre}:{fn}"
                known.add(token)
                outstanding[token] = acc.get("label", "outstanding until it is answered")
        else:
            bad.append(f"accounts entry {pre!r} names neither a file nor a dir")

    claimed = {}
    for row in work.get("rows", []):
        for c in row.get("covers", []):
            claimed.setdefault(c, []).append(row.get("n"))

    uncovered = [(t, w) for t, w in sorted(outstanding.items()) if t not in claimed]
    allowed = work.get("unreconciled", 0)
    try:
        allowed = int(allowed)
    except (TypeError, ValueError):
        bad.append(f"unreconciled must be a whole number, not {allowed!r}")
        allowed = 0
    over = len(uncovered) - allowed
    if over > 0:
        for t, w in uncovered[:allowed + 12][allowed:]:
            bad.append(f"nothing on the work list covers {t!r} — {w}")
        if over > 12:
            bad.append(f"… and {over - 12} more uncovered")
        bad.append(f"{len(uncovered)} outstanding items have no row and the list "
                   f"declares only {allowed} unreconciled — raise a row, or raise the number "
                   f"deliberately and say why")

    for token, rws in sorted(claimed.items()):
        where = ", ".join(f"row {n}" for n in rws)
        if token not in known:
            bad.append(f"{where}: covers {token!r}, but no such thing exists any more")

    if bad:
        for b in bad:
            print("  " + b)
        print(f"\n  FAIL  {len(bad)} problem(s) — "
              f"the work list does not account for what is outstanding")
        return 1

    # Counted in the order the archive declared them, and named in its own
    # words: "7 pending register rows" reads as something a person can check,
    # where "7 register" does not.
    per = {}
    for k in outstanding:
        per[k.split(":", 1)[0]] = per.get(k.split(":", 1)[0], 0) + 1
    bits = []
    for acc in accounts:
        pre = acc.get("prefix")
        if per.get(pre):
            bits.append(f"{per[pre]} {acc.get('noun', pre)}")
    detail = " · ".join(bits) or "nothing outstanding"
    covered = len(outstanding) - len(uncovered)
    tail = ""
    if uncovered:
        tail = f" · {len(uncovered)} not yet reconciled"
    print(f"  ok    {name} accounts for {covered} of {len(outstanding)} outstanding item(s) "
          f"— {detail}{tail}")
    if uncovered and len(uncovered) < allowed:
        print(f"        the backlog has fallen to {len(uncovered)}: lower \"unreconciled\" "
              f"from {allowed} so it cannot drift back up")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    return check(root, "work list")


if __name__ == "__main__":
    sys.exit(main())
