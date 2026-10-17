#!/usr/bin/env python3
"""The kit's own file manifest: a hash of every file in kit/, shipped inside the kit.

WHY (Falco's fault-planting sweep, 17 October 2026). checkpin.py read the lockfile and package.json and never the
INSTALLED files, so editing kit/styles/print.css under node_modules still said "ok pin": the same way a stale kit
passed on 13 October. The manifest lets any archive prove the files it is building with are the files that were
committed: kit/MANIFEST.json maps every path under kit/ (except itself) to its sha256.

    python3 kit/tools/manifest.py --write            regenerate kit/MANIFEST.json (run before every kit commit)
    python3 kit/tools/manifest.py --check            verify the manifest matches kit/ (the kit's own test)
    python3 kit/tools/manifest.py --check --kit DIR  verify an INSTALLED kit directory (checkpin.py does this)

A stale manifest (a kit file changed, manifest not regenerated) fails --check, so the kit cannot ship one.
"""
import os
import sys
import json
import hashlib
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
KIT_DIR = os.path.dirname(HERE)            # .../kit
NAME = "MANIFEST.json"
SKIP_DIRS = {"__pycache__", ".git", "node_modules"}
SKIP_FILES = {".DS_Store", NAME}


def hashes(kit_dir):
    out = {}
    for d, ds, fs in os.walk(kit_dir):
        ds[:] = sorted(x for x in ds if x not in SKIP_DIRS)
        for f in sorted(fs):
            if f in SKIP_FILES or f.endswith(".pyc"):
                continue
            p = os.path.join(d, f)
            rel = os.path.relpath(p, kit_dir).replace(os.sep, "/")
            with open(p, "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


def compare(kit_dir):
    """Return (problems, n_files, manifest_present)."""
    mp = os.path.join(kit_dir, NAME)
    if not os.path.exists(mp):
        return [], 0, False
    try:
        want = json.load(open(mp, encoding="utf-8")).get("files") or {}
    except (OSError, ValueError):
        return ["%s is unreadable" % NAME], 0, True
    got = hashes(kit_dir)
    bad = []
    for rel, h in want.items():
        if rel not in got:
            bad.append("missing: " + rel)
        elif got[rel] != h:
            bad.append("changed: " + rel)
    for rel in got:
        if rel not in want:
            bad.append("not in the manifest: " + rel)
    return bad, len(want), True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--kit", default=KIT_DIR)
    a = ap.parse_args()
    if a.write:
        h = hashes(a.kit)
        json.dump({"note": "sha256 of every file under kit/ except this one. Regenerate with `python3 kit/tools/manifest.py --write` "
                           "before every kit commit; `--check` fails on a stale manifest. Read by checkpin.py.",
                   "files": h}, open(os.path.join(a.kit, NAME), "w", encoding="utf-8"), indent=1, sort_keys=True)
        open(os.path.join(a.kit, NAME), "a").write("\n")
        print("manifest: wrote %d file hashes" % len(h))
        return 0
    bad, n, present = compare(a.kit)
    if not present:
        print("manifest: %s has no %s (a kit from before 17 October 2026)" % (a.kit, NAME))
        return 2
    if bad:
        print("manifest: FAIL, %d difference(s) from the manifest:" % len(bad))
        for b in bad[:20]:
            print("  - " + b)
        return 1
    print("manifest: ok, %d files match" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
