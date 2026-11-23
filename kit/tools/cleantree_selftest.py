#!/usr/bin/env python3
"""Prove cleantree.py can fail, on throwaway git repositories, and that it never changes one.

A gate that has only ever been seen passing has not been seen working. Each case builds a fresh repository with
ONE departure from clean and asserts the exit code and the file the tool names. The last cases prove it is read
only: the same repository, byte for byte (HEAD, index, every working file), before and after.

    python3 kit/tools/cleantree_selftest.py
"""

import contextlib
import hashlib
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cleantree  # noqa: E402

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")


def sh(d, *args):
    subprocess.run(["git", "-C", d] + list(args), check=True, env=ENV,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def write(d, rel, text):
    p = os.path.join(d, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


def repo():
    d = tempfile.mkdtemp(prefix="cleantree-")
    sh(d, "init", "-q", "-b", "main")
    write(d, ".gitignore", "site/dist/\nnode_modules/\n")
    write(d, "site/src/data/a.json", "{}\n")
    write(d, "site/src/generated/places.json", "[]\n")
    write(d, "site/src/generated/flags.json", "[]\n")
    write(d, "docs/b.md", "b\n")
    write(d, "café à deux.txt", "x\n")
    sh(d, "add", "-A")
    sh(d, "commit", "-q", "-m", "base")
    return d


def run(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cleantree.main(args)
    return code, out.getvalue()


def fingerprint(d):
    h = hashlib.sha256()
    for dp, dn, fn in os.walk(d):
        dn[:] = sorted(x for x in dn if x != ".git")
        for f in sorted(fn):
            p = os.path.join(dp, f)
            h.update(p.encode("utf-8", "replace"))
            h.update(open(p, "rb").read())
    for rel in ("HEAD", "index"):
        p = os.path.join(d, ".git", rel)
        h.update(open(p, "rb").read())
    return h.hexdigest()


FAILS = []


def case(name, args, want_code, want_in=(), want_out=(), setup=None, root_sub=None):
    d = repo()
    if setup:
        setup(d)
    root = os.path.join(d, root_sub) if root_sub else d
    before = fingerprint(d)
    code, text = run(["--root", root] + list(args))
    after = fingerprint(d)
    problems = []
    if code != want_code:
        problems.append("exit %s, wanted %s" % (code, want_code))
    for w in want_in:
        if w not in text:
            problems.append("output lacks %r" % w)
    for w in want_out:
        if w in text:
            problems.append("output should not contain %r" % w)
    if before != after:
        problems.append("THE REPOSITORY CHANGED: the tool is not read only")
    print("%s  %s%s" % ("ok  " if not problems else "FAIL", name, "" if not problems else "  <- " + "; ".join(problems)))
    if problems:
        FAILS.append(name)
        print(text)


def modify(d):
    write(d, "site/src/generated/places.json", "[1]\n")


def main():
    case("clean tree passes", [], 0, ["ok"])
    case("a tracked file the build rewrote fails and is named", [], 1,
         ["site/src/generated/places.json", " M"], ["flags.json"], setup=modify)
    case("a deleted tracked file fails", [], 1, ["docs/b.md", " D"],
         setup=lambda d: os.remove(os.path.join(d, "docs/b.md")))
    case("a staged change fails", [], 1, ["docs/b.md", "M "],
         setup=lambda d: (write(d, "docs/b.md", "bb\n"), sh(d, "add", "docs/b.md")))
    case("a staged rename fails once, under the new name", [], 1, ["docs/c.md", "R "], ["docs/b.md"],
         setup=lambda d: sh(d, "mv", "docs/b.md", "docs/c.md"))
    case("a path with spaces and an accent is named intact", [], 1, ["café à deux.txt"],
         setup=lambda d: write(d, "café à deux.txt", "y\n"))
    case("a new untracked file is flagged but does not fail", [], 0, ["site/src/new.json", "reported only"],
         setup=lambda d: write(d, "site/src/new.json", "{}\n"))
    case("--fail-untracked makes it fail", ["--fail-untracked"], 1, ["site/src/new.json"],
         setup=lambda d: write(d, "site/src/new.json", "{}\n"))
    case("an ignored build output is never listed", [], 0, ["ok"], ["dist", "node_modules"],
         setup=lambda d: (write(d, "site/dist/index.html", "x"), write(d, "node_modules/p/i.js", "x")))
    case("--allow excuses a glob that crosses a slash", ["--allow", "site/src/generated/*"], 0,
         ["allowed by --allow"], ["places.json"], setup=modify)
    case("--allow of another file does not excuse this one, and says it matched nothing", ["--allow", "docs/*"], 1,
         ["places.json", "matched nothing"], setup=modify)
    case("only the allowed file is excused, a second rewritten file still fails", ["--allow", "site/src/generated/places.json"], 1,
         ["flags.json"], ["  M  site/src/generated/places.json"],
         setup=lambda d: (modify(d), write(d, "site/src/generated/flags.json", "[2]\n")))
    case("--root inside the repository looks only below it", [], 0, ["ok"], ["docs/b.md"],
         setup=lambda d: write(d, "docs/b.md", "changed\n"), root_sub="site")
    case("--root inside the repository still names a change below it, from the repository root", [], 1,
         ["site/src/generated/places.json"], setup=modify, root_sub="site")
    case("--quiet is silent when clean", ["--quiet"], 0, [], ["ok"])

    d = tempfile.mkdtemp(prefix="cleantree-nogit-")
    code, text = run(["--root", d])
    bad = code != 2 or "not inside a git repository" not in text
    print("%s  a directory that is not a repository exits 2 and says why" % ("FAIL" if bad else "ok  "))
    if bad:
        FAILS.append("nogit")
        print(code, text)

    if FAILS:
        print("\ncleantree_selftest: %d case(s) failed: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("\ncleantree_selftest: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
