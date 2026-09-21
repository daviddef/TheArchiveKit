#!/usr/bin/env python3
"""The kit you are building against is not the kit you committed.

Two estate-wide CI breakages on 21 September 2026, eight repositories between
them, and both had the same shape: PASSED LOCALLY, FAILED ON THE RUNNER.

The second one was a check that read outside its own repository — see
`checkpages.py`. The first is this one, and it is quieter.

    python3: can't open file '.../kit/tools/checksources.py': No such file

A new gate was added to package.json's build chain while the archive's
`@daviddef/archive-kit` pin still named a commit from BEFORE that gate
existed. Locally it worked, because the working copy of node_modules had been
installed from a newer sha by hand. CI installs from the committed pin, found
no such file, and stopped the deploy.

So the fault is never visible where the work happens. Nothing is wrong with
the script, the package.json or the pin on their own; the three only disagree
once somebody else installs them.

THIS CHECKS TWO THINGS, AND THE SECOND IS THE ONE THAT BITES.

  1. Every kit path named in a build script exists in the installed kit.
  2. The LOCKFILE resolved the same commit package.json PINS. The lockfile is
     the only place npm records which commit it fetched — the installed
     package.json says version 1.0.0 and has for months. A pin edited without
     an install, or an install never committed, is the whole failure above,
     and it passes every local build right up to the push.

  python3 checkpin.py --root .        (run from the site directory)
"""

import argparse, json, os, re, subprocess, sys

DEP = "@daviddef/archive-kit"


def locked_sha(root):
    """The lockfile is the only place npm records which commit it actually
       fetched. The installed package.json says version 1.0.0 and has said so
       for months, so it cannot answer this."""
    p = os.path.join(root, "package-lock.json")
    if not os.path.exists(p):
        return None, "no package-lock.json"
    try:
        j = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None, "package-lock.json unreadable"
    for k, v in (j.get("packages") or {}).items():
        if k.endswith(DEP):
            m = re.search(r"#([0-9a-f]{7,40})", str(v.get("resolved") or ""))
            if m:
                return m.group(1), None
    return None, "the lockfile does not record a commit for the kit"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    pkg = os.path.join(a.root, "package.json")
    if not os.path.exists(pkg):
        print("  FAIL  pin        no package.json under %s" % os.path.abspath(a.root))
        return 1
    j = json.load(open(pkg, encoding="utf-8"))
    scripts = j.get("scripts", {})
    pinned = ""
    for field in ("dependencies", "devDependencies"):
        v = (j.get(field) or {}).get(DEP)
        if v:
            m = re.search(r"#([0-9a-f]{7,40})", v)
            pinned = m.group(1) if m else v
            break
    if not pinned:
        print("  ok    pin        this archive does not depend on the kit")
        return 0

    # 1. Referenced kit files must exist.
    missing = []
    for name, cmd in scripts.items():
        for rel in re.findall(r"node_modules/@daviddef/archive-kit/(\S+?\.(?:py|mjs|js))", cmd):
            if not os.path.exists(os.path.join(a.root, "node_modules", DEP, rel)):
                missing.append((name, rel))

    got, why = locked_sha(a.root)
    drift = got and not (got.startswith(pinned) or pinned.startswith(got))

    if not a.quiet:
        for name, rel in missing:
            print("        script %s calls %s, which the installed kit does not have" % (name, rel))
        if drift:
            print("        package.json pins %s, the lockfile resolved %s" % (pinned[:12], got[:12]))

    if missing:
        print("  FAIL  pin        %d build script(s) call a kit file that is not in the installed "
              "kit — CI installs from the pin and will not find them either" % len(missing))
        return 1
    if drift:
        print("  FAIL  pin        the lockfile resolved %s but package.json pins %s — "
              "every local build is testing something nobody else will get"
              % (got[:12], pinned[:12]))
        return 1
    if why:
        print("  ok    pin        %d kit file(s) referenced, all present (%s)"
              % (len(scripts), why))
        return 0
    print("  ok    pin        kit %s installed and pinned, every referenced file present"
          % pinned[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
