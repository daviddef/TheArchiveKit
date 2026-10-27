#!/usr/bin/env python3
"""Make src/data/direct-line.json from the story, or check that the file is what the story makes.

The file says who is on our direct line (kit/docs/family-ribbon.md, "The direct line"): one entry for every story ribbon card
with a person, one for each card with none (`unlinked`), and a partner for every spouse a card marks `spouseDirect`. It is
PRODUCED, never typed, so the tint cannot drift from the story. (kit/lib/directline.js fromStory() makes the same file in JS;
kit/tools/checkfamilyribbon.py D1-D3 hold the two to each other.)

    python3 directline.py --story src/data/story.json --write src/data/direct-line.json [--label generation]
    python3 directline.py --story src/data/story.json --check src/data/direct-line.json
"""
import argparse, json, sys


def from_story(story, label="generation"):
    people, partners, unlinked = [], [], []
    for i, c in enumerate((story.get("ribbon") or {}).get("cards") or []):
        if c.get("person"):
            people.append({"slug": c["person"], "generation": i + 1, "storyChapter": c.get("chapter", ""), "name": c.get("name", "")})
        else:
            unlinked.append({"generation": i + 1, "storyChapter": c.get("chapter", ""), "name": c.get("name", "")})
        if c.get("spouseDirect") and c.get("spousePerson"):
            partners.append({"slug": c["spousePerson"], "generation": i + 1, "storyChapter": c.get("chapter", ""),
                             "partnerOf": c.get("person", ""), "name": c.get("spouse", "")})
    return {"generationLabel": label, "people": people, "partners": partners, "unlinked": unlinked}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--story", required=True)
    ap.add_argument("--write")
    ap.add_argument("--check")
    ap.add_argument("--label", default="generation")
    a = ap.parse_args()
    story = json.load(open(a.story, encoding="utf-8"))
    out = from_story(story, a.label)
    if a.write:
        out = dict({"_note": "Made by kit/tools/directline.py from the story's ribbon; do not edit by hand."}, **out)
        json.dump(out, open(a.write, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        open(a.write, "a").write("\n")
        print("directline: wrote %s (%d people, %d partners, %d unlinked)" % (a.write, len(out["people"]), len(out["partners"]), len(out["unlinked"])))
        return 0
    if a.check:
        have = json.load(open(a.check, encoding="utf-8"))
        have = {k: v for k, v in have.items() if not k.startswith("_")}
        have.setdefault("partners", []); have.setdefault("unlinked", [])
        out["generationLabel"] = have.get("generationLabel", out["generationLabel"])
        for k in ("people", "partners", "unlinked"):
            strip = lambda rows: [{x: y for x, y in r.items() if x != "name"} for r in rows]
            if strip(have[k]) != strip(out[k]):
                print("directline: %s differs from the story's ribbon; run --write" % k)
                return 1
        print("directline: %s is what the story makes" % a.check)
        return 0
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
