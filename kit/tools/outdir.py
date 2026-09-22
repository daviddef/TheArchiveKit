"""Which built directory a check should read.

THE CLAIM THIS FILE EXISTS TO MAKE TRUE. On 22 September 2026 a commit in
this kit said, of `ARCHIVE_OUT`, that it is «the directory every other tool
in this kit honours». That was not true of a single tool in this kit.
Four of them take a `--dist` flag, and it was passed as the literal
`--dist dist` on the command line, so the variable was read by nothing and
overridden by everything.

AND THE SENTENCE ABOVE IS ITSELF ONE ARCHIVE TOO WIDE, twice. Two of the
eight had solved it already and both sessions had to tell me so, having
verified it in both directions before they did. Booyzen has passed
`--dist "${ARCHIVE_OUT:-dist}"` since 21 September — the shell expands it
before the flag exists, so the flag CARRIED the variable rather than
overriding it. Defranceski never calls the scripts directly: its
`gate-isolated.sh` builds into `dist-gate-$$` and passes `--dist "$OUT"` by
name, written in early September after three builds died when a foreign
build wiped `site/dist` underneath them. So the fault reached six of the
eight, and the claim that it reached all of them went out in two commit
messages that are now in those archives' histories. Correcting it here
because this file is where the claim will be read next.

WHY IT MATTERS MORE THAN IT SOUNDS. Several sessions build this estate at
the same time and share a working tree, so `dist` is routinely half-written,
or belongs to somebody else's uncommitted data. That has already produced a
false «868 broken links», a false «187 record lines reach 0 of 60 people»,
and — the one that should not have been possible — a row ratchet written
from a build nobody had just made. The estate's answer is to build to a
private directory and point the checks at it:

    ARCHIVE_OUT=dist-verify npx astro build --outDir dist-verify
    ARCHIVE_OUT=dist-verify npm run check:living

The living gate is the one that must never be wrong, and the living gate was
reading somebody else's `dist`.

THE ENVIRONMENT WINS OVER THE FLAG, which is the opposite of the usual
order, and deliberately. `--dist dist` in package.json is the repository's
default — what to read when nobody has said otherwise. `ARCHIVE_OUT` is an
operator standing at the keyboard saying «read THIS build, the one I just
made». Making the flag win would mean the only way to honour the operator is
to edit eight package.json files, which is how this was broken in the first
place.

Only the last component is replaced, so a tool whose default is `site/dist`
and one whose default is `dist` both land in the same place.
"""

import os


def resolve(dist):
    out = os.environ.get("ARCHIVE_OUT")
    if not out:
        return dist
    d = (dist or "").rstrip("/\\")
    parent = os.path.dirname(d)
    return os.path.join(parent, out) if parent else out


def note(dist):
    """One line for a tool to print, or "" when nothing was overridden."""
    return ("" if not os.environ.get("ARCHIVE_OUT")
            else "  ..    reading %s (ARCHIVE_OUT)" % dist)

# ---------------------------------------------------------------------------
# A PRIVATE NAME THAT EVERYBODY USES IS NOT PRIVATE.
#
# `dist` was shared, so the estate moved to `ARCHIVE_OUT=dist-verify` — and on
# 23 September two sessions collided in `dist-verify` inside one archive, which
# is `dist` again with an extra word. The gate caught it, loudly and correctly:
# «dist-verify changed while this ran — another build is in flight. Results
# would be noise, so nothing is reported.» That refusal is the thing that
# worked; the shared name is the thing that failed.
#
# Two answers, and the estate needs both.
#
# THE NAME. Pick one nobody else will pick. `ARCHIVE_OUT=dist-$$` is per
# process and wrong here, because a build and the checks that read it run in
# separate shells; the value has to be stable for a working session and unique
# between them. `suggest()` below composes one from whatever the host offers —
# a session id, a tmux pane, a PPID — and falls back to the user name.
#
# THE GUARD. A name cannot be relied on, because the operator chooses it and
# may choose badly. `settled()` fingerprints the tree before and after a run,
# so a check that straddles somebody else's build throws its results away
# instead of reporting them. checkarchive has done this since it was written
# and it is the reason the collision was visible at all; it belongs to every
# tool that reads a build.
# ---------------------------------------------------------------------------


def suggest():
    """A build directory name unlikely to collide with another session's."""
    import getpass
    for var in ("CLAUDE_SESSION_ID", "TMUX_PANE", "TERM_SESSION_ID", "STY"):
        v = os.environ.get(var)
        if v:
            tag = "".join(c for c in v if c.isalnum())[-10:]
            if tag:
                return "dist-" + tag
    try:
        who = getpass.getuser()
    except Exception:
        who = "x"
    return "dist-%s-%d" % (who, os.getppid())


def fingerprint(dist):
    """Name and size of every file under a built tree."""
    out = []
    for root, _, files in os.walk(dist):
        for f in files:
            p = os.path.join(root, f)
            try:
                out.append((p, os.path.getsize(p)))
            except OSError:
                out.append((p, -1))
    return sorted(out)


def settled(dist, before, label):
    """0 when the tree did not move under the run, 1 when it did.

    `astro build` empties a directory before it refills it, so a check that
    reads a half-written tree reports hundreds of absences that are simply not
    copied yet. A run that straddles a build has no result worth printing.
    """
    if fingerprint(dist) == before:
        return 0
    print("  --    %-10s %s changed while this ran — another build is in flight."
          % (label, dist))
    print("        Results would be noise, so nothing is reported. Re-run when "
          "the build has finished,")
    print("        or build to a directory of your own: ARCHIVE_OUT=%s" % suggest())
    return 1
