#!/usr/bin/env python3
"""Refuse the build when a reading the archive has WITHDRAWN is stated as fact.

DESIGNED IN THE FALCO ARCHIVE and ported with permission. The estate has tried
a general prose check before - four designs, roughly 100% false positives, all
abandoned - and this one works for a reason worth stating in one sentence,
because without it this drifts back into a prose checker and gets switched off:

    A RETIRED PHRASE IS THE ARCHIVE'S OWN WORDING, NEVER A DOCUMENT'S, SO AN
    UNQUOTED HIT IS A CLAIM AND A QUOTED ONE IS A QUOTATION.

«act 26 of 15 December 1814» is not something a register says. It is something
an archive said, and then withdrew. That is why the mark around a quotation can
separate the two, and why the same trick CANNOT be used for a retired surname:
the documents themselves contain the surname, so an unquoted hit there is
ordinary. Falco keeps its surname rules separate and narrow for that reason,
and so should anybody adopting this.

THE MARK IS A PARAMETER, NOT GUILLEMETS. Falco writes a dead reading inside
«…»; another archive may use <del>, a strikethrough, or a "was:" field. The
mark is whatever that archive uses to mean "this is the version we no longer
believe", and hardcoding one house style would fire on another archive's honest
withdrawals. Declare it beside the phrases.

    site/src/data/retired.json
    { "mark": [["«", "»"]],
      "phrases": [ {"phrase": "...", "why": "...", "since": "2026-09-20"} ] }

ONLY A PROPOSITION WITHDRAWN IN EVERY CONTEXT BELONGS IN THE LIST. From the
D'Arcy session, which put ten phrases in and took two straight back out: «no
record has been found for them» is false about thirty people and TRUE ABOUT
FOUR HUNDRED, so the gate was flagging correct pages. A phrase that is only
withdrawn about one person is a trap waiting for the day the archive records
somebody it IS true of - «BURIED AT VOLKSRUST» is withdrawn about Martha
Angeline Kolbe and would be right about the next person actually buried there.
Declare the narrowest wording that cannot be true anywhere, or accept that the
gate will one day refuse a fact.

A QUOTATION IS A SPAN, NOT AN ADJACENCY. Their first implementation looked a
couple of characters either side of the hit and missed «not published at all -
absent from the build», where the closing mark is nine words on. This strips
whole marked spans before searching, which is the same conclusion reached from
the other direction. It matters most in an archive whose house rule is that an
error stays on the page where it was made: that GUARANTEES retired phrases
appear in live prose, inside the sentence withdrawing them.

WHO IT CATCHES FIRST. The Falco session was caught by it within the hour, in
its own work-list note describing the correction - the phrase written in bold
and unquoted. That is correct behaviour and it is the failure mode to expect:
the person most likely to trip this is the person writing the withdrawal. The
fix is to wrap it in the mark, which is what the house style wanted anyway.

  python3 checkretired.py --root site
"""
import io, os, re, sys, json, argparse

# Generated artefacts: a retired phrase surviving in one of these is a fault in
# the builder that wrote it, and it will be rewritten on the next build anyway.
SKIP = {"searchindex.json", "changes.json", "researchlog.json", "research-log.json",
        "people.json", "register.json", "living.json", "married-in.json",
        "people-register.json", "corrections.json", "retired.json",
        "dossiers.json", "atlas-data.json", "namefold.json"}
EXTS = (".json", ".tsv", ".md")


def strip_marks(text, marks):
    """Everything inside a withdrawal mark is a quotation of the dead reading."""
    for a, b in marks:
        text = re.sub(re.escape(a) + r".*?" + re.escape(b), " ", text, flags=re.S)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site")
    ap.add_argument("--also", action="append", default=[],
                    help="another directory to scan, e.g. ../data")
    a = ap.parse_args()

    decl = os.path.join(a.root, "src", "data", "retired.json")
    if not os.path.exists(decl):
        print("  note  retired     no retired.json here, so nothing is declared "
              "withdrawn and there is nothing to check. This gate only knows what "
              "an archive tells it.")
        return 0
    d = json.load(io.open(decl, encoding="utf-8"))
    marks = [tuple(m) for m in d.get("mark") or [["«", "»"]]]
    phrases = [p for p in (d.get("phrases") or []) if p.get("phrase")]
    if not phrases:
        print("  note  retired     retired.json declares no phrases yet.")
        return 0

    # A DATED LOG IS NOT A CLAIM. An archive that keeps a searched register or
    # a work list is recording what it did and believed ON A DATE, and a log
    # edited whenever the belief changes is not a log - it is the same reason a
    # struck work-list row is struck and not deleted. Those files can be named
    # here, by the archive, with its reason. Everything else is checked.
    skip_files = set(SKIP) | set(d.get("skip") or [])
    dirs = [os.path.join(a.root, "src", "data")] + list(a.also)
    bad, scanned = [], 0
    for base in dirs:
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for fn in files:
                if not fn.endswith(EXTS) or fn in skip_files:
                    continue
                p = os.path.join(root, fn)
                try:
                    body = io.open(p, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                scanned += 1
                clean = strip_marks(body, marks)
                for ph in phrases:
                    if ph["phrase"].lower() in clean.lower():
                        bad.append((os.path.relpath(p, a.root), ph))

    if bad:
        seen = set()
        for rel, ph in bad:
            k = (rel, ph["phrase"])
            if k in seen:
                continue
            seen.add(k)
            print("  FAIL  %s" % rel)
            print("          states «%s» as fact, and it was withdrawn%s"
                  % (ph["phrase"], (" on " + ph["since"]) if ph.get("since") else ""))
            if ph.get("why"):
                print("          %s" % ph["why"])
        print("\n  FAIL  retired    %d withdrawn reading(s) stated as fact. Wrap a "
              "quotation of the dead version in the archive's own withdrawal mark; "
              "an unquoted one is a claim." % len(seen))
        return 1
    print("  ok    retired    %d withdrawn reading(s), none stated as fact in %d file(s)"
          % (len(phrases), scanned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
