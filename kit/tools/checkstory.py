#!/usr/bin/env python3
"""Hold the children's site to what the archives actually say.

WHY. Our-Family is the story the seven archives are told through, written for
the four cousins - read aloud to a child of six, read alone by a child of ten.
It is one level up from the research and it drifts silently, because nothing
downstream of an archive notices when that archive changes its mind.

It had drifted in three ways at once, and every one of them made the story
sound MORE certain than its sources:

  · Four generations above 1785 in the Prostamo line are marked on the Mazza
    archive as resting on the family tree alone. The children's site called
    1697 «the oldest anybody can name» in fifteen places and said the line was
    «one unbroken chain».
  · Four pages said no photograph of that family existed. The Mazza archive had
    since published its picture store, and ten people standing on those very
    ladders are in it.
  · A whole generation was missing: the Lerena archive found Juan Carlos in
    September 2026, off an army card filed under a misspelling, and the story
    still stopped one rung below him.

So this compares the two, per family. It does not write anything: what a child
should be told is an editorial matter and stays with whoever writes it.

  python3 checkstory.py --root <estate dir> [--strict]
"""
import argparse, io, json, os, re, subprocess, sys

import os.path as _up, sys as _us
_us.path.insert(0, _up.dirname(_up.abspath(__file__)))
import outdir as _outdir  # ARCHIVE_OUT; see kit/tools/outdir.py

# the umbrella's family slug -> the repo whose spine and pictures it draws on
ARCHIVE = {
    "defranceski": "Defranceski Family", "falco": "Falco Family",
    "blazevic": "Blazevic Family", "lerena": "Lerena Family",
    "booyzen": "Booyzen Family", "darcy": "D'Arcy Family",
    "mazza": "Mazza Family", "prostamo": "Mazza Family",
    "arena": "Mazza Family", "polistena": "Mazza Family",
}
# LUWINSKI IS DELIBERATELY NOT HERE, and this is the note that stops somebody
# adding it. There are eight archives in the estate and ten families on the
# children's site, and the eighth archive is not one of them: the four cousins
# are not descended from the Luwinskis. A page that exists to tell four children
# where they come from is the wrong place for a family they did not come from,
# however much research it holds. The absence is the decision, not an oversight.

# the four families that share one archive draw on one spine between them, so a
# rung count cannot be compared for those; only the photograph claim can.
SHARES_A_SPINE = {"mazza", "prostamo", "arena", "polistena"}


def families(story):
    """The umbrella's own data, read by running it rather than parsing it."""
    out = subprocess.run(
        ["node", "--input-type=module", "-e",
         'import {families} from "./src/data/families.js";'
         'console.log(JSON.stringify(families.map(f=>({slug:f.slug,name:f.name,'
         'told:f.ladder.filter(g=>g.told).length,rungs:f.ladder.length,'
         'photos:f.photos.length,noPhotos:f.noPhotos||""}))))'],
        cwd=os.path.join(story, "site"), capture_output=True, text=True)
    if out.returncode:
        raise SystemExit("  could not read families.js:\n" + out.stderr[:400])
    return json.loads(out.stdout)


def weak_joints(root, repo):
    """How many joints that archive marks as not bearing weight."""
    # A HARD-WIRED `dist` GRADES WHOEVER BUILT LAST. Several sessions share
    # this tree, and a chain that builds to a directory of its own was being
    # checked against the shared one — which is how one archive reported
    # «spouse fell 585 to 489» about a build that had lost nothing.
    p = os.path.join(root, repo, "site", _outdir.resolve("dist"), "direct-line", "index.html")
    if not os.path.exists(p):
        return None
    h = io.open(p, encoding="utf-8", errors="ignore").read()
    return len(re.findall(r'<li class="sp-g sp-weak"', h))


def has_pictures(root, repo):
    """Whether that archive publishes photographs anywhere a reader can see."""
    n = 0
    for page in ("gallery", "documents"):
        p = os.path.join(root, repo, "site", _outdir.resolve("dist"), page, "index.html")
        if os.path.exists(p):
            n += len(re.findall(r'class="gy-p"', io.open(p, encoding="utf-8", errors="ignore").read()))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--story", default="Our Family")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    story = os.path.join(root, a.story)
    if not os.path.isdir(story):
        print("  no %s at %s" % (a.story, root)); return 1

    said = []
    for f in families(story):
        repo = ARCHIVE.get(f["slug"])
        if not repo:
            said.append("%s: the story carries it and no archive is mapped to it" % f["slug"])
            continue
        weak = weak_joints(root, repo)
        pics = has_pictures(root, repo)

        if weak is None:
            print("  %-11s (%s not built — cannot compare)" % (f["slug"], repo.split()[0]))
            continue

        note = ""
        if f["slug"] not in SHARES_A_SPINE:
            if weak and not f["told"]:
                said.append("%s: the archive marks %d joint(s) that will not bear weight and the "
                            "story marks none" % (f["slug"], weak))
            elif f["told"] and not weak:
                said.append("%s: the story marks %d rung(s) as only told, and the archive marks "
                            "none — the story is less certain than its source"
                            % (f["slug"], f["told"]))
            note = "archive %d unproven / story %d told" % (weak, f["told"])
        else:
            note = "shares the %s spine" % repo.split()[0]

        # a page claiming no face exists, on an archive that publishes faces
        if not f["photos"] and pics and re.search(r"\b(no|nothing|not one|none)\b",
                                                  f["noPhotos"][:60], re.I):
            said.append("%s: says no photograph exists; %s publishes %d"
                        % (f["slug"], repo.split()[0], pics))
        print("  %-11s %-34s %s" % (f["slug"], note,
                                    "%d pictures in %s" % (pics, repo.split()[0]) if pics else ""))

    print()
    if said:
        for s in said:
            print("  DRIFT  %s" % s)
        print("\n  %d place(s) where the story and the archives disagree" % len(said))
        return 1 if a.strict else 0
    print("  ok    the story says what the archives say")
    return 0


if __name__ == "__main__":
    sys.exit(main())
