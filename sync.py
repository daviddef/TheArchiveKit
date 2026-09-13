#!/usr/bin/env python3
"""Copy the kit into all seven archives, or just report where they have drifted.

    python3 sync.py --check     say what differs, change nothing
    python3 sync.py             copy the kit out to every archive

Deliberately a copier rather than a package dependency. These seven sites are
static, deploy straight from a push, and are worked on by several people at
once; a shared npm dependency means one bad publish can take all seven offline
at the same moment. A copy that is checked costs one command and cannot fail
that way. If that trade stops being worth it, this is the file to replace.
"""
import os, sys, shutil, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS = os.path.dirname(ROOT)

# kit file -> where it lands inside each archive
FILES = {
    "kit/components/Evidence.astro":        "site/src/components/Evidence.astro",
    "kit/components/SiblingArchives.astro": "site/src/components/SiblingArchives.astro",
    "kit/data/archives.json":               "site/src/data/archives.json",
    "kit/tools/sitemap.py":                 "tools/sitemap.py",
}

ARCHIVES = ["Defranceski Family", "Falco Family", "Booyzen Family", "D'arcy Family",
            "Blazevic Family", "Mazza Family", "Lerena Family"]

# CSS is not copied — each archive's stylesheet is its own. These markers say
# whether the kit's blocks are present, so a missing one is visible.
CSS_MARKERS = [".ev-documented", ".ladder{", ".ring{", "--ev-inferred"]


def digest(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12] if os.path.exists(p) else None


def main(check):
    drift = 0
    for a in ARCHIVES:
        home = os.path.join(PROJECTS, a)
        if not os.path.isdir(home):
            print(f"  ?  {a:<20} not found"); continue
        notes = []
        for src, dst in FILES.items():
            s, d = os.path.join(ROOT, src), os.path.join(home, dst)
            if digest(s) != digest(d):
                notes.append(os.path.basename(dst))
                if not check:
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.copy2(s, d)
        css = os.path.join(home, "site/public/styles.css")
        if os.path.exists(css):
            have = open(css, encoding="utf-8").read()
            missing = [m for m in CSS_MARKERS if m not in have]
            if missing:
                notes.append("css:" + ",".join(missing))
        if notes:
            drift += 1
            verb = "differs" if check else "updated"
            print(f"  !  {a.split()[0]:<13} {verb}: {'  '.join(notes)}")
        else:
            print(f"  ok {a.split()[0]:<13} in step")
    if check and drift:
        print(f"\n{drift} archive(s) out of step. Run without --check to copy the kit out.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
