#!/usr/bin/env python3
"""Every archive keeps one work list, in one shape, at one path.

Eight sessions were each asked what they were tracking and each began inventing
an answer. That is precisely how this estate ended up with a component called
Chip meaning two things, two Pedigrees 7.6KB apart, and one chart drawn under
three names in six archives. A convention that lives only in a document drifts,
because nothing is checking it; the conventions that held here — the menu canon,
the living-person rule, the component ledger — all held because a build refuses
when they slip.

So this refuses.

  site/src/data/worklist.json
  {
    "title": "...", "dek": "...", "lead": "...", "close": "...",
    "rows": [
      { "n": 1,
        "what":  "one line, what is being done",
        "state": "running | next | blocked | done | struck",
        "owner": "this archive | the Falco session | David | a machine",
        "since": "2026-09-15",
        "note":  "a paragraph; [links](/like-this/) resolve" }
    ]
  }

state   what is happening to it. `struck` is for an item founded on a mistake:
        kept and struck through rather than deleted, the same way these archives
        treat a retracted claim.
owner   WHO HAS TO MOVE IT. An item with no owner is how a list becomes
        wallpaper — it is the field the estate roll-up sorts on, because the
        question actually being asked is "what is waiting on me".
since   when it was raised, so a thing blocked for five weeks does not read the
        same as a thing raised this morning.

  python3 checkworklist.py --root site          # one archive
  python3 checkworklist.py --root . --all       # every archive under a folder
"""
import os, re, sys, json, glob, argparse, datetime

STATES = {"running", "next", "blocked", "done", "struck"}
REQ = ("what", "state", "owner")
STALE_DAYS = 45


def check(path, name):
    bad, warn = [], []
    if not os.path.exists(path):
        return [f"{name}: no worklist at {path} — every archive keeps one"], []
    try:
        w = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"{name}: worklist.json will not parse — {e}"], []
    rows = w.get("rows")
    if not isinstance(rows, list) or not rows:
        return [f"{name}: worklist has no rows"], []

    seen = set()
    today = datetime.date.today()
    for i, r in enumerate(rows, 1):
        where = f"{name} row {r.get('n', i)}"
        if not isinstance(r, dict):
            bad.append(f"{where}: not an object"); continue
        for k in REQ:
            if not str(r.get(k, "")).strip():
                bad.append(f"{where}: no {k}"
                           + ("  — who has to move it?" if k == "owner" else ""))
        st = r.get("state")
        if st not in STATES:
            bad.append(f"{where}: state {st!r} is not one of " + ", ".join(sorted(STATES)))
        n = r.get("n")
        if n in seen:
            bad.append(f"{where}: two rows numbered {n}")
        seen.add(n)
        since = str(r.get("since", "")).strip()
        if since:
            try:
                d = datetime.date.fromisoformat(since)
                age = (today - d).days
                if age > STALE_DAYS and st in ("running", "next", "blocked"):
                    warn.append(f"{where}: {st} for {age} days — still true?")
            except ValueError:
                bad.append(f"{where}: since {since!r} is not YYYY-MM-DD")
        elif st in ("running", "next", "blocked"):
            warn.append(f"{where}: open, with no date it was raised")
    return bad, warn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--warn-only", action="store_true",
                    help="report and exit 0 — for an estate still adopting this")
    a = ap.parse_args()

    targets = []
    if a.all:
        for p in sorted(glob.glob(os.path.join(a.root, "*", "site", "src", "data", "worklist.json"))):
            targets.append((p, os.path.relpath(p, a.root).split(os.sep)[0]))
        for d in sorted(glob.glob(os.path.join(a.root, "*", "site"))):
            name = os.path.relpath(d, a.root).split(os.sep)[0]
            p = os.path.join(d, "src", "data", "worklist.json")
            if not os.path.exists(p):
                targets.append((p, name))
    else:
        targets.append((os.path.join(a.root, "src", "data", "worklist.json"), "this archive"))

    bad, warn = [], []
    for p, n in targets:
        b, w = check(p, n)
        bad += b; warn += w

    for w in warn:
        print("  warn  worklist   " + w)
    for b in bad:
        print("  FAIL  worklist   " + b)
    if not bad:
        print(f"  ok    worklist   {len(targets)} checked, "
              f"{len(warn)} advisory" if warn else
              f"  ok    worklist   {len(targets)} checked")
    return 1 if bad and not a.warn_only else 0


if __name__ == "__main__":
    sys.exit(main())
