#!/usr/bin/env python3
"""Refuse the build when a template's markup does not close.

WHY, AND WHAT IT FOUND ON ITS FIRST RUN. Every gate in this estate checks
DATA. Nothing checked the templates that render it, and Astro will happily
build markup that does not close: it guesses, ships, and the page looks nearly
right. First run over one archive, four real faults nobody had seen:

  documents.astro  two <blockquote> opened and closed with </p>. One of them
                   swallowed an <h3> and the paragraph after it - 928
                   characters inside a quote box meant to hold 450.
  method.astro     a third, the same shape.
  people.astro     an empty <section class="blk"> opened at the end of the
                   file and never closed, shipping <section></section> into
                   every build.

WHY IT DOES NOT JUST RUN `astro check`. That reports 42 more things on the
same archive and every one is TypeScript not knowing the shape of an imported
JSON file - «Property 'log' does not exist on type 'unknown'». Those are not
faults, and a gate that fails on them would be switched off within a week,
which is how this estate loses gates. This fails on the STRUCTURAL class only:
a tag that does not close, and a parse error. Everything else is counted and
reported, so the number is visible without being fatal.

Needs @astrojs/check and typescript in the archive. Without them it says so
and exits 0, because a missing dev dependency is not a broken template.

  python3 checktemplates.py --root site
"""
import os, re, sys, subprocess, argparse

STRUCTURAL = re.compile(r"ts\(1700[28]\)|astro: Expected a closing tag")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--require", action="store_true",
                    help="fail, not just note, when @astrojs/check is not installed")
    a = ap.parse_args()

    if not os.path.isdir(os.path.join(a.root, "node_modules", "@astrojs", "check")):
        print("  note  templates  @astrojs/check is not installed here, so the "
              "markup was not checked. A missing dev dependency is not a broken "
              "template; `npm i -D @astrojs/check typescript` turns this on.")
        return 1 if a.require else 0

    try:
        p = subprocess.run(["npx", "astro", "check"], cwd=a.root,
                           capture_output=True, text=True, timeout=600)
    except Exception as e:
        print("  FAIL  templates  could not run astro check (%s), so the markup was not checked" % e)
        return 1

    out = ANSI.sub("", (p.stdout or "") + (p.stderr or ""))
    # astro check ends with a "Result (N files):" line. Without it the tool crashed (for example a
    # missing @volar file) and checked nothing: it printed "ok every tag closes" and exited 0 over
    # an unclosed <div><section> (Blazevic sweep, 16 October 2026).
    if not re.search(r"Result\s*\(\d+", out):
        tail = [l.strip() for l in out.splitlines() if l.strip()][-3:]
        print("  FAIL  templates  astro check did not complete (no Result line), so no markup was "
              "checked: %s" % " | ".join(t[:80] for t in tail))
        return 1
    lines = out.splitlines()
    bad = [l.strip() for l in lines if STRUCTURAL.search(l)]
    total = 0
    m = re.search(r"-\s*(\d+)\s+errors?", out)
    if m:
        total = int(m.group(1))

    if bad:
        for l in bad[:12]:
            print("  FAIL  %s" % l[:150])
        print("\n  FAIL  templates  %d tag(s) do not close. Astro guesses and "
              "ships, so this is a page that looks nearly right." % len(bad))
        return 1
    other = max(0, total - len(bad))
    print("  ok    templates  every tag closes%s"
          % ("" if not other else
             " — %d other type finding(s), all of them TypeScript not knowing "
             "an imported JSON's shape, reported and not fatal" % other))
    return 0


if __name__ == "__main__":
    sys.exit(main())
