#!/usr/bin/env python3
"""A build must leave the git working tree clean.

If `npm run build` rewrites a file that git tracks, the committed copy and the built copy have drifted apart, and
nobody finds out until the next person's diff is full of noise they did not make (Lerena's seven generated files,
fixed in #25, sat like that for weeks). The fault is invisible where the work happens: the build is green, the
site is right, and the working tree is quietly dirty. So the build is run, and THEN this asks git.

    npm run build
    python3 node_modules/@daviddef/archive-kit/kit/tools/cleantree.py --root .

WHAT IT DOES. `git status --porcelain` on the repository, read only:

  * TRACKED files that differ from what is committed (modified, deleted, renamed, staged, conflicted). These FAIL
    the check (exit 1), each listed with its two-letter git status code.
  * NEW files that are untracked and not ignored. These are listed under their own heading, because they are a
    different fault (a build wrote something nobody ignored or committed), and they do NOT fail unless you pass
    `--fail-untracked`. Ignored files (site/dist, node_modules, the GEDCOM) are never listed.

OPTIONS
  --root DIR           the repository, or a directory inside it (default: the current directory). Only paths
                       under DIR are looked at, but they are shown relative to the repository root.
  --allow GLOB         a file the build legitimately rewrites; repeatable; none by default. Matched with
                       fnmatch against the path relative to the repository root, and `*` also crosses `/`
                       (`site/src/generated/*` covers everything below it). An --allow that matches nothing is
                       reported as a note, not a failure, so the list can be pruned. It is the documented escape,
                       not the first resort: if a build rewrites a tracked file, the usual cure is to commit
                       the regenerated file, or to stop tracking it and ignore it.
  --fail-untracked     treat new untracked non-ignored files as a failure too
  --quiet              print nothing when the tree is clean

EXIT  0 clean (or only allowed / untracked-not-failing)   1 the build left the tree unclean   2 could not ask git

READ ONLY. It runs `git --no-optional-locks status` and `git rev-parse` and nothing else: it never commits,
resets, cleans, stashes, adds or checks out, and `--no-optional-locks` stops even status from refreshing the
index. It cannot tell a file the build rewrote from one you edited by hand before the build, so run it on a clean
checkout (CI is one); locally, commit or stash first.

Proved by cleantree_selftest.py.
"""

import argparse
import fnmatch
import os
import subprocess
import sys


def git(root, *args):
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", root] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def parse(raw):
    """Porcelain v1 with -z: `XY path\\0`, and a rename or copy is followed by the ORIGINAL path as its own
       NUL-terminated field. Returns [(code, path)]; a rename is reported once, under its new path."""
    out = []
    fields = raw.split(b"\0")
    i = 0
    while i < len(fields):
        f = fields[i]
        i += 1
        if len(f) < 4:
            continue
        code = f[:2].decode("ascii", "replace")
        path = f[3:].decode("utf-8", "replace")
        if code[0] in "RC" or code[1] in "RC":
            i += 1  # the original path, which we do not list
        out.append((code, path))
    return out


def allowed(path, globs):
    hit = [g for g in globs if fnmatch.fnmatchcase(path, g)]
    return hit


def survey(root, globs=()):
    """Return (tracked, untracked, allowed_paths, used_globs) or raise RuntimeError."""
    try:
        top = git(root, "rev-parse", "--show-toplevel")
    except OSError as e:
        raise RuntimeError("could not run git: %s" % e)
    if top.returncode != 0:
        raise RuntimeError("%s is not inside a git repository (%s)"
                           % (root, top.stderr.decode("utf-8", "replace").strip()))
    st = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", ".")
    if st.returncode != 0:
        raise RuntimeError("git status failed: %s" % st.stderr.decode("utf-8", "replace").strip())
    tracked, untracked, skipped, used = [], [], [], set()
    for code, path in parse(st.stdout):
        if code == "!!":
            continue
        hit = allowed(path, globs)
        if hit:
            skipped.append((code, path))
            used.update(hit)
            continue
        (untracked if code == "??" else tracked).append((code, path))
    return tracked, untracked, skipped, used


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fail when a build leaves the git working tree unclean.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--allow", action="append", default=[], metavar="GLOB")
    ap.add_argument("--fail-untracked", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    try:
        tracked, untracked, skipped, used = survey(a.root, a.allow)
    except RuntimeError as e:
        print("cleantree: cannot check: %s" % e)
        return 2

    unused = [g for g in a.allow if g not in used]
    bad = bool(tracked) or (a.fail_untracked and bool(untracked))

    if tracked:
        print("cleantree: the build rewrote %d tracked file%s (git status code, path):"
              % (len(tracked), "" if len(tracked) == 1 else "s"))
        for code, p in sorted(tracked, key=lambda x: x[1]):
            print("  %s  %s" % (code, p))
        print("  Commit the regenerated file, or stop tracking it and ignore it; if a build must rewrite it,"
              " pass --allow GLOB with the reason.")
    if untracked:
        print("cleantree: %d new untracked file%s the build left (not ignored)%s:"
              % (len(untracked), "" if len(untracked) == 1 else "s",
                 "" if a.fail_untracked else " [reported only; --fail-untracked makes this a failure]"))
        for _, p in sorted(untracked, key=lambda x: x[1]):
            print("  ??  %s" % p)
    for g in unused:
        print("cleantree: note: --allow %r matched nothing; it can be dropped." % g)
    if skipped and not a.quiet:
        print("cleantree: %d changed file%s allowed by --allow." % (len(skipped), "" if len(skipped) == 1 else "s"))

    if bad:
        return 1
    if not tracked and not untracked and not skipped and not a.quiet:
        print("cleantree: ok, the working tree is clean after the build.")
    elif not bad and not a.quiet and not tracked:
        print("cleantree: ok, no tracked file was rewritten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
