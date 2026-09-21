#!/usr/bin/env python3
"""A page that eight archives all have, and all eight draw differently.

`checkshared.py` watches duplicated COMPONENTS. Nothing watched pages, and
pages are where the estate actually diverges: every archive has `dna`, every
archive has `sources`, and until 21 September 2026 no two of them rendered
either the same way. Eight bespoke sources pages came to 1,331 lines with no
two sharing one; six bespoke dna pages come to 3,681.

The rule this encodes is the one the estate already works to. A page name
carried by THREE OR MORE archives is a shared idea, and a shared idea should
be drawn by a shared component — with each archive keeping its own data, its
own ordering and its own prose, because those are the argument and the
rendering is not. Two archives having the same page is a coincidence; three
is a pattern.

WHAT THIS DOES NOT SAY. It does not say a bespoke page is wrong. Booyzen's
sources page is four tables of holdings rather than a bibliography, and
forcing it onto the shared component would measure the wrong object. So an
archive can EXEMPT a page, in writing, and the exemption is printed every run
rather than hidden — an exemption nobody reads is an exemption nobody
revisits.

  .harmonise-exempt   one page name per line at the archive root, optionally
                      "name: reason". The reason is printed. No reason is
                      itself reported, because "we exempted it and nobody
                      remembers why" is the state this is meant to prevent.

WHERE THIS CAN RUN, WHICH IS NOT EVERYWHERE. This check reads OTHER
REPOSITORIES. It needs the estate on disk beside the archive, and a GitHub
Actions runner checks out one repository and nothing else — so on a runner
the comparison set does not exist and never will. The first version failed
there, by design rather than by accident, and broke the deploy of every
archive it had been wired into within eleven minutes.

So: fewer than two archives found means the check CANNOT RUN, which is not
the same as finding nothing wrong. It says so and exits 0. It still fails
loudly when the estate IS present and an archive has gone backwards.

The general rule, worth more than this file: a check that reads outside its
own repository is a dev-machine check, not a build gate. If it must sit in
the build chain, it has to know the difference between "nothing is wrong"
and "I could not look".

THE RATCHET. --max-bespoke N fails when an archive's bespoke count goes UP.
It is not a wall: no archive starts at zero and several cannot reach it this
year. It exists so the number can only fall, and so that ADDING a new bespoke
page to an idea three other archives already share breaks the build that adds
it — which is the only moment anyone will fix it cheaply.

  python3 checkpages.py --root . [--estate ..] [--max-bespoke N] [--quiet]
  python3 checkpages.py --estate .. --report     # the whole estate, ranked
"""

import argparse, os, re, sys, glob, collections

# An archive is a directory with site/src/pages in it. Discovered rather than
# listed, because components.py kept a hand-written list and spent two months
# counting seven archives in an estate of eight.
def archives(estate):
    out = []
    for d in sorted(glob.glob(os.path.join(estate, "*", "site", "src", "pages"))):
        out.append((os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(d)))), d))
    return out


KIT = re.compile(r"archive-kit/components/([A-Za-z]+)\.astro")
# Pages that are the archive's front door or its own argument, not a shared
# idea rendered eight ways. These are never counted.
NEVER = {"index", "404", "about", "method", "colophon", "privacy", "credits"}


def exemptions(root):
    p = os.path.join(root, ".harmonise-exempt")
    out = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.split("#")[0].strip()
            if not line:
                continue
            name, _, why = line.partition(":")
            out[name.strip()] = why.strip()
    return out


def scan(estate, threshold):
    """page name -> {archive: (lines, kit components used)}"""
    pages = collections.defaultdict(dict)
    for arch, d in archives(estate):
        for f in glob.glob(os.path.join(d, "**", "*.astro"), recursive=True):
            name = os.path.relpath(f, d)[:-6].replace(os.sep, "/")
            if name in NEVER or name.startswith("_"):
                continue
            try:
                src = open(f, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            pages[name][arch] = (len(src.splitlines()), set(KIT.findall(src)))
    return {n: v for n, v in pages.items() if len(v) >= threshold}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--estate", default=None,
                    help="the directory holding every archive; default is --root/../..")
    ap.add_argument("--threshold", type=int, default=3,
                    help="how many archives make a page a shared idea (default 3)")
    ap.add_argument("--max-bespoke", type=int, default=None)
    ap.add_argument("--report", action="store_true", help="the whole estate, ranked")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    estate = a.estate or os.path.abspath(os.path.join(a.root, "..", ".."))
    found = archives(estate)
    if len(found) < 2:
        # Not a pass and not a failure: there is nothing here to compare
        # against. One checkout on a CI runner looks exactly like this, and
        # so does a wrong --estate. Both mean the same thing to this tool.
        print("  --    pages      not run: %d archive(s) beside %s, and comparing pages "
              "needs the estate. This check only works where the other archives are."
              % (len(found), os.path.abspath(estate)))
        return 0
    shared = scan(estate, a.threshold)
    if not shared:
        print("  ok    pages      %d archives found, no page carried by %d or more of them"
              % (len(found), a.threshold))
        return 0

    if a.report:
        # The report must subtract exemptions or its headline is a lie. The
        # first version did not, and reported 56 bespoke pages on an afternoon
        # when six of them had been examined and written off in writing —
        # which is the same fault as a check that cannot find its subject,
        # pointing the other way.
        ex = {arch: exemptions(os.path.join(estate, arch)) for arch, _ in archives(estate)}
        rows = []
        for n, v in shared.items():
            bes = [arch for arch, (_, k) in v.items() if not k and n not in ex.get(arch, {})]
            exe = [arch for arch, (_, k) in v.items() if not k and n in ex.get(arch, {})]
            rows.append((len(bes), len(v), n, sum(l for l, _ in v.values()), bes, exe))
        rows.sort(reverse=True)
        tot_b = sum(r[0] for r in rows)
        tot_e = sum(len(r[5]) for r in rows)
        print("%-18s %8s %6s %8s %7s %8s   still bespoke"
              % ("page", "archives", "kit", "bespoke", "exempt", "lines"))
        for bes, tot, n, L, who, exe in rows:
            if bes or exe:
                print("%-18s %8d %6d %8d %7d %8d   %s"
                      % (n, tot, tot - bes - len(exe), bes, len(exe), L, ", ".join(sorted(who)) or "—"))
        print("\n%d shared page(s) carried by %d+ archives; %d archive-pages still bespoke, "
              "%d exempt in writing." % (len(rows), a.threshold, tot_b, tot_e))
        return 0

    # One archive: which shared pages does IT still draw by hand?
    arch = os.path.basename(os.path.abspath(os.path.join(a.root, "..")))
    ex = exemptions(os.path.abspath(os.path.join(a.root, "..")))
    mine, exempt, noreason = [], [], []
    for n, v in sorted(shared.items()):
        if arch not in v:
            continue
        _, kit = v[arch]
        if kit:
            continue
        if n in ex:
            exempt.append((n, ex[n]))
            if not ex[n]:
                noreason.append(n)
        else:
            mine.append((n, len(v)))

    if not a.quiet:
        for n, carried in mine:
            print("        drawn by hand here, and %d archive(s) share the page — %s" % (carried, n))
        for n, why in exempt:
            print("        exempt — %s%s" % (n, (": " + why) if why else "  (NO REASON GIVEN)"))

    tail = ""
    if noreason:
        tail = " · %d exemption(s) with no reason: %s" % (len(noreason), ", ".join(noreason))
    n = len(mine)
    if a.max_bespoke is not None and n > a.max_bespoke:
        print("  FAIL  pages      %d shared page(s) still drawn by hand, and the ratchet is %d — "
              "this number may only go down%s" % (n, a.max_bespoke, tail))
        return 1
    if n:
        print("  ok    pages      %d shared page(s) still drawn by hand, %d exempt%s"
              % (n, len(exempt), tail))
    else:
        print("  ok    pages      every shared page drawn by the kit, %d exempt%s"
              % (len(exempt), tail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
