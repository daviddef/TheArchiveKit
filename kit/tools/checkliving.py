#!/usr/bin/env python3
"""Refuse to ship a build that names a living person.

David's rule for these sites is absolute and it is the reason the children's
site exists in the form it does: LIVING PEOPLE ARE INITIALS AND NOTHING MORE.
No given name, no year of birth, no place of birth. Public figures are the
only exception, and they are declared. A name is unlocked when its owner dies,
one at a time, by editing the declaration — never by a code change.

The Falco archive learned this the hard way: the same date leaked three times,
twice from code that read correctly in the source, and every one was found by
reading the BUILT HTML rather than the source. So this reads site/dist.

It is driven by a declaration the site owns, so unlocking a name is a one-line
data edit and the guard follows:

    {
      "note": "...",
      "living": [
        {"initials": "ADD", "forbid": ["Alessio", "Alessio Dominic"], "born": "2016"},
        {"initials": "CAL", "forbid": ["Cheryl"], "born": "1958"}
      ],
      "allow": ["David Attenborough"],
      "allowFiles": ["credits/index.html"]
    }

Every string in `forbid`, and every `born` year, must not appear in any built
page. `allow` carries the exceptions — a public figure, or a phrase that
legitimately contains the word — and is matched before the forbidden terms.

Usage:  python3 checkliving.py --dist dist --living src/data/living.json
Exit 1 on any leak, so it can gate a deploy.
"""
import os, re, sys, json, html, argparse


def visible_text(src):
    """What a reader actually sees. Script and style are stripped, because a
    name in a JSON blob inside <script> is still a leak but is reported
    separately — see raw_text."""
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", src, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--living", default="src/data/living.json")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.dist):
        print(f"checkliving: no {a.dist} — build first")
        return 1
    if not os.path.exists(a.living):
        print(f"checkliving: no declaration at {a.living}. This guard is only as "
              f"good as its list, so a missing list is a failure, not a pass.")
        return 1

    decl = json.load(open(a.living, encoding="utf-8"))
    people = decl.get("living", [])
    allow = [x.lower() for x in decl.get("allow", [])]
    allow_files = set(decl.get("allowFiles", []))

    terms = []   # (pattern, label)
    for p in people:
        who = p.get("initials") or "?"
        for n in p.get("forbid", []):
            if n:
                terms.append((re.compile(r"\b" + re.escape(n) + r"\b", re.I),
                              f"{who}: the name «{n}»"))
        if p.get("born"):
            terms.append((re.compile(r"\b" + re.escape(str(p["born"])) + r"\b"),
                          f"{who}: the birth year {p['born']}"))
    if not terms:
        print("checkliving: the declaration forbids nothing — nothing to check.")
        return 1

    pages = 0
    leaks = []
    for root, _, files in os.walk(a.dist):
        for f in files:
            if not f.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(root, f), a.dist).replace(os.sep, "/")
            if rel in allow_files:
                continue
            pages += 1
            raw = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
            for scope, text in (("on the page", visible_text(raw)),
                                ("in the markup", raw)):
                low = text.lower()
                for rx, label in terms:
                    for m in rx.finditer(text):
                        ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 45):m.end() + 45]).strip()
                        if any(x in ctx.lower() for x in allow):
                            continue
                        leaks.append((rel, label, scope, ctx))
                        break
                if scope == "on the page" and leaks and leaks[-1][0] == rel:
                    break   # don't report the same page twice

    if leaks:
        seen = set()
        print(f"  FAIL  living      {len(leaks)} leak(s) across {pages} pages")
        for rel, label, scope, ctx in leaks:
            k = (rel, label)
            if k in seen:
                continue
            seen.add(k)
            print(f"          /{rel}  →  {label}, {scope}")
            print(f"              …{ctx}…")
        print("\n  A living person is initials and nothing more. If one of these "
              "people has died,\n  unlock the name in the declaration — do not "
              "silence the check.")
        return 1

    if not a.quiet:
        who = ", ".join(p.get("initials", "?") for p in people)
        print(f"  ok    {pages} pages carry no name and no birth year for {who}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
