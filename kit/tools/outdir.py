"""Which built directory a check should read.

THE CLAIM THIS FILE EXISTS TO MAKE TRUE. On 22 September 2026 a commit in
this kit said, of `ARCHIVE_OUT`, that it is «the directory every other tool
in this kit honours». That was not true of a single one of them. Four tools
take a `--dist` flag and every archive's package.json passes `--dist dist`
on the command line, so the environment variable was read by nothing and
overridden by everything.

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
