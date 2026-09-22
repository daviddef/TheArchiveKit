#!/usr/bin/env python3
"""Build the variant-to-canonical map a register search folds spellings with.

WHY. FilterTable has taken a `fold` map since the Blazevic register moved onto
it, and until today five wrapper components dropped the prop, so one page in the
whole estate used it. Measured on the Booyzen register that is not a nicety: the
surname is written six ways across 4,244 tokens, and a reader who types the
canonical spelling reaches 3,504 of them and never learns the other 740 exist.
D'Arcy is worse - its commonest spelling is 46% of its entries.

WHAT IT DOES NOT DO. Folding is a SEARCH rule, not an identity rule. It widens
what a query matches; it never merges two records, never joins two people and
never touches a chart. This estate does not merge on a name and this does not
change that - it is the opposite, a way of SEEING the other spellings rather
than quietly missing them.

HOW THE CLUSTERS ARE FORMED. Every surname token in the archive's own corpus is
reduced by the orthographic rules that actually vary in these records - ij/y,
s/z, doubled letters, diacritics - and tokens reducing to the same key cluster
together. THE CANONICAL FORM IS THE ARCHIVE'S OWN, taken from people.json, never
the commonest spelling: the Master's office spelled this family BOOYZEN and the
parish spelled it BOOYSEN, and which of those an archive answers to is its
decision, not a majority vote.

EVERY CLUSTER IS PRINTED. A fold that quietly joined two families would be the
worst bug this kit could ship, so the tool is loud and the output is meant to be
read before it is committed.

  python3 namefold.py --root site            # writes src/data/namefold.json
  python3 namefold.py --root site --dry      # print the clusters, write nothing
"""
import io, os, re, sys, json, glob, argparse, unicodedata

import os.path as _up, sys as _us
_us.path.insert(0, _up.dirname(_up.abspath(__file__)))
import unread as _unread  # see kit/tools/unread.py
from collections import Counter, defaultdict


def key(w):
    """The spelling rules that vary in these registers, and no others."""
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    w = _unreachable(w)
    w = w.replace("ÿ", "y").replace("ij", "y").replace("ck", "k")
    w = w.replace("z", "s")                       # Booyzen / Booysen
    w = w.replace("y", "i")                       # Booysen / Booisen
    return w


# THERE IS NO DOUBLED-LETTER RULE, and there was one for about ten minutes.
# Collapsing repeats reduces Roos and Ross to the same key, and Roos and Ross are
# two different families in this archive - the first Dutch, the second Scottish,
# 2,030 tokens against 563. It would also have caught Kolbee for Kolbe and
# Grobbelaar for Grobelaar, which is twenty-odd tokens between them. Twenty
# tokens is not worth one wrong family. FOLDING IS ALLOWED TO MISS; IT IS NOT
# ALLOWED TO JOIN.
# LETTERS NFD CANNOT REACH — added 21 September 2026.
#
# unicodedata NFD splits a base letter from its combining mark, so z-with-caron
# folds to z and c-with-acute to c. It does nothing at all for the letters that
# are a single codepoint in their own right: d-with-stroke, l-with-stroke,
# o-with-stroke, eszett. Blazevic's Đurić did not fold to Duric and nothing said so.
#
# ONLY d-with-stroke IS MAPPED HERE, AND ONLY BECAUSE THAT ARCHIVE MEASURED IT.
# Across every file Blazevic ships: 9 words carry one of these letters, 371
# tokens, of which 350 are "Rođeni" — the register's own word for births, not a
# name. The map creates exactly ONE collision, Anđelika with Andelika, and that
# is Angelika Boras, whom the record index spells four ways. It joins her to
# herself. There is no second family for it to reach.
#
# l-with-stroke, o-with-stroke and eszett are NOT mapped: no archive on this
# estate has one in a name. Blazevic has zero of the first two and its only
# eszett is a German street address in a note.
#
# THIS DELIBERATELY DIFFERS FROM kit/components/Search.astro, WHICH MAPS ALL OF
# THEM, and the difference is not an oversight. That fold answers "did the
# reader mean this page", where a generous fold costs nothing and a miss loses a
# reader. This one answers "are these two spellings one family", where a
# generous fold merges houses — which is why there is no doubled-letter rule
# above. FOLDING IS ALLOWED TO MISS; IT IS NOT ALLOWED TO JOIN. Do not sync the
# two lists without measuring the archive that would be joined.
NFD_CANNOT_REACH = {"\u0111": "d"}          # d-with-stroke, lower-cased before use


def _unreachable(w):
    for a, b in NFD_CANNOT_REACH.items():
        w = w.replace(a, b)
    return w


ROMAN = re.compile(r"^[IVXLC]+$")


def bare(w):
    """The same word with its accents and its case taken off, and nothing else.

    THIS IS THE LINE BETWEEN A SPELLING RULE AND A CLAIM ABOUT A FAMILY. Papic
    for Papic-with-an-acute, FRAGALA for Fragala-with-a-grave, BLAZEVIC for the
    one with carons: that is one word two keyboards wrote differently, and
    folding them needs nobody's permission. Sanzone for Sansone changes a
    letter, and whether those are one family in the Falco archive is that
    archive's judgement and not this tool's. The first kind is enabled wherever
    this runs. The second is printed, and waits for --all."""
    w = unicodedata.normalize("NFD", w.lower())
    return _unreachable("".join(c for c in w if unicodedata.category(c) != "Mn"))


# THE ARCHIVE'S RECORDS, NOT THE ARCHIVE'S PROSE. corpus() read every *.json
# in the data directory, which in this estate includes the work list, the
# searched register, the corrections and the change log - the narrative. A
# surname appearing only in a SENTENCE ABOUT a surname then entered the corpus
# with the same standing as a register row.
#
# Raised by the Blazevic session, whose own case is the mild one: «Subrinic,
# Xubrinich and Zubrinicz are zero» is a sentence about a failed search, and
# its two tokens are nobody's name. The dangerous one is theirs too, and it is
# the example this tool already carries - an archive whose work list says «the
# other Roos family, who are not ours» offers that name to the clusterer with
# the confidence of a record, and a fold that JOINS TWO FAMILIES is the worst
# thing this kit could ship.
#
# The counts are what have saved it so far: 2 tokens against 1,059 announces
# itself to anybody reading the output. That is not a guarantee, it is a
# coincidence of scale.
NARRATIVE = {"worklist.json", "searched.json", "corrections.json", "changes.json",
             "log.json", "changelog.json", "research-log.json", "researchlog.json",
             "questions.json", "open-questions.json", "notes.json", "errands.json",
             "letters.json", "method.json", "covers.json", "accounts.json"}


def corpus(data, extra_skip=()):
    """Every word the archive's own records actually contain, with counts."""
    c = Counter()
    skip = NARRATIVE | set(extra_skip)
    for p in glob.glob(os.path.join(data, "*.json")):
        if os.path.basename(p) in skip:
            continue
        try:
            txt = io.open(p, encoding="utf-8").read()
        except Exception as e:
            # This builds the corpus the name-variant work is judged against.
            # A file that never opened makes a rare spelling look rarer than
            # it is, which is the direction that loses a person.
            _unread.note(p, e)
            continue
        for w in re.findall(r"\b[A-Z][A-Za-zÀ-ſ']{3,}\b", txt):
            if not ROMAN.match(w):
                c[w] += 1
    return c


def canon_surnames(data):
    """The names this archive answers to, out of its own people file.

    SEVEN ARCHIVES, SEVEN FILENAMES AND TWO KEYS. This read people.json with a
    key of `n` because that is what the archive it was written in happens to
    use, and it found nothing at all in five of the others and crashed on two,
    where a row carries an integer under the same key. The preference order
    below is the estate as it actually is; the register is last because a
    register row is named after whatever the record said, so its last word is as
    likely to be a forename as a surname.
    """
    PREFER = ["people.json", "roster.json", "ancestors.json", "dossiers.json",
              "family.json", "register.json"]
    for fn in PREFER:
        p = os.path.join(data, fn)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception as e:
            _unread.note(p, e)
            continue
        rows = d if isinstance(d, list) else None
        if rows is None and isinstance(d, dict):
            rows = []
            for v in d.values():
                if isinstance(v, list):
                    rows += [r for r in v if isinstance(r, dict)]
                elif isinstance(v, dict):
                    rows += [r for r in v.values() if isinstance(r, dict)]
        out = []
        for r in rows or []:
            if not isinstance(r, dict):
                continue
            for k in ("n", "name", "who"):
                v = r.get(k)
                if isinstance(v, str) and " " in v.strip():
                    out.append(v.strip().split()[-1].strip("\u201c\u201d\"'.,"))
                    break
        if len(out) >= 20:
            print("  anchored on %s (%d name(s))" % (fn, len(out)))
            return [w for w, _ in Counter(out).most_common()]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="also fold clusters that change a letter, not only an "
                         "accent - for an archive whose own session has read them")
    ap.add_argument("--min", type=int, default=2,
                    help="ignore a variant seen fewer times than this")
    a = ap.parse_args()
    data = os.path.join(a.root, "src", "data")
    if not os.path.isdir(data):
        print("  namefold: no %s" % data); return 1

    words = corpus(data)
    canon = canon_surnames(data)
    if not canon:
        print("  namefold: no people file - nothing to anchor a cluster to"); return 1

    # only cluster around names this archive actually answers to
    # THE TARGET OF A FOLD IS A BUCKET LABEL, NOT A RULING ON SPELLING, and
    # it used to be chosen by frequency, which quietly implied otherwise. The
    # Luwinski session named the flaw: frequency tracks how often an archive
    # PARAPHRASES, not which document is closest to the event. Kurt's second
    # wife is Hostovsky on the 1956 marriage register, the most formal of the
    # three documents, and Hostowski or Hostowsky elsewhere; the commonest
    # form is not the birth form.
    #
    # A FIRST FIX REFUSED TO FOLD ANY CLUSTER THE ARCHIVE SPELLS TWO WAYS, and
    # that was worse than the flaw. It dropped Booijsen / Booijzen / Booysen /
    # Booyzen / Booÿsen in the archive named after them - the single fold that
    # estate most needs - because those five are five real people's surnames.
    # Folding is symmetric: the map is applied to the query AND to the row, so
    # whichever member of a cluster is named as the target, every member finds
    # every other. The target never appears to a reader and changes no
    # display.
    #
    # A SECOND FIX, ALPHABETICAL TARGETS, WAS ALSO WRONG AND WORSE. The
    # safe/proposed split is computed RELATIVE TO THE TARGET: a form is folded
    # on sight only when it differs from the target by an accent alone.
    # Alphabetical made Booijsen the target, so Booyzen, Booysen and eleven
    # other forms became letter-changes from it and stopped folding - the
    # register that had just gone from 59 rows to 1,495 would have gone back.
    # The target is arbitrary, but it is not free: it decides what counts as
    # an accent away.
    #
    # So the selection is left exactly as it was, and what changes is that the
    # tool stops implying the target is a ruling. Where an archive spells a
    # name several ways the output says which label was used and that it is
    # only a label.
    anchors, several = {}, {}
    for c in canon:
        k = key(c)
        if k in anchors:
            if anchors[k].lower() != c.lower():
                several.setdefault(k, {anchors[k]}).add(c)
        else:
            anchors[k] = c

    # A cluster the archive has looked at and REJECTED stays rejected. The
    # place to say "these two never fold" is a file somebody can read, not a
    # rule - and D'Arcy's ZANIGAR is why: it is not a spelling of anything,
    # it is a nonsense control that archive invented to prove TNA Discovery's
    # search was not loosely fuzzy, and folding it would publish a control
    # test as an attested form of the family name.
    denyp = os.path.join(data, "namefold-deny.json")
    deny = set()
    if os.path.exists(denyp):
        deny = {w.lower() for w in
                json.load(io.open(denyp, encoding="utf-8")).get("never", [])}

    groups = defaultdict(Counter)
    for w, n in words.items():
        if len(key(w)) < 4 or w.lower() in deny:
            continue
        k = key(w)
        if k in anchors:
            groups[k][w] += n

    fold, shown, proposed = {}, 0, []
    print("  clusters, anchored on the archive's own spelling:")
    for k, forms in sorted(groups.items(), key=lambda kv: -sum(kv[1].values())):
        c = anchors[k]
        others = {w: n for w, n in forms.items()
                  if w.lower() != c.lower() and n >= a.min}
        if not others:
            continue
        tot = sum(forms.values())
        reach = sum(n for w, n in forms.items() if bare(c) in bare(w))
        print("    %-16s %5d token(s) \u2014 typing %r reaches %d (%.0f%%)"
              % (c, tot, c, reach, 100.0 * reach / tot))
        took = False
        for w, n in sorted(others.items(), key=lambda x: -x[1]):
            same = bare(w) == bare(c)          # one word, two keyboards
            on = same or a.all
            print("      %s %-18s %5d%s"
                  % ("\u00b7" if same else "?", w, n,
                     "" if on else "   proposed \u2014 changes a letter"))
            if on:
                fold[w.lower()] = c.lower()
                took = True
            else:
                proposed.append((c, w, n))
        if took:
            shown += 1
            fold[c.lower()] = c.lower()

    extra = os.path.join(data, "namefold-extra.json")
    if os.path.exists(extra):
        e = json.load(io.open(extra, encoding="utf-8"))
        pairs = e.get("fold", e) if isinstance(e, dict) else {}
        for v, c in pairs.items():
            fold[v.lower()] = c.lower()
        print("  + %d pair(s) from namefold-extra.json (the archive's own, "
              "written not derived)" % len(pairs))

    if several:
        print("  %d name(s) this archive itself spells more than one way. The "
              "fold target below is alphabetical and is only a bucket label \u2014 "
              "the map is applied to the query and the row alike, so every form "
              "finds every other, and nothing here says which spelling is "
              "right:" % len(several))
        for k, forms in sorted(several.items()):
            print("      %s  \u2192  %s" % (" / ".join(sorted(forms)), anchors[k]))
    # AND IS ANYBODY USING IT? A map that is built, committed and passed to no
    # component is the estate's commonest fault wearing a different hat: work
    # that exists, is correct, and never reaches a reader. The D'Arcy session
    # found exactly that - namefold.json generated on every build and consumed
    # by nothing, so the register it was written for searched raw. Five kit
    # wrappers had dropped the prop, which is how it happened, but nothing
    # would have said so.
    src = os.path.join(os.path.dirname(data.rstrip(os.sep)), "pages")
    if os.path.isdir(src):
        used = 0
        for root, _, files in os.walk(src):
            for fn in files:
                if not fn.endswith(".astro"):
                    continue
                try:
                    if "fold=" in io.open(os.path.join(root, fn),
                                          encoding="utf-8", errors="replace").read():
                        used += 1
                except Exception:
                    pass
        if not used:
            print("  note  nothing reads this map. No page passes a `fold=` prop, so "
                  "every search on this archive is still matching raw text. The map "
                  "is built and unread, which is worth more than a silent success.")
        else:
            print("  %d page(s) pass the map to a component." % used)

    print("  %d cluster(s), %d form(s) folded" % (shown, len(fold)))
    if proposed:
        print("  %d form(s) NOT folded: they change a letter rather than an "
              "accent, which is a claim about a family and not a spelling rule."
              % len(proposed))
        print("  Run with --all once this archive's own session has read them:")
        for c, w, n in proposed:
            print("      %s \u2192 %s (%d token(s))" % (w, c, n))
    if a.dry:
        print("  --dry: nothing written"); return 0
    out = os.path.join(data, "namefold.json")
    json.dump({"note": "Variant → canonical, for SEARCH only. Built by "
                       "kit/tools/namefold.py; run it again rather than editing "
                       "it. Folding widens what a query matches and never merges "
                       "a record with another.",
               "fold": dict(sorted(fold.items()))},
              io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  → %s" % out)
    return 0


if __name__ == "__main__":
    # A GENERATOR STILL HAS OUTPUT TO PRODUCE, so this says what it could
    # not read and does not refuse: a fold list missing four files and one
    # missing none look identical once written.
    rc = main()
    _unread.mention("namefold")
    sys.exit(rc)
