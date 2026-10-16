#!/usr/bin/env python3
"""Refuse a hand-written page or data file that says more about a living person than the standard allows.

WHY. The living standard (kit/tools/living_rule.py, David 16 October 2026) lets a living person
appear by NAME, RELATIONSHIPS and FULL TOWN AND COUNTRY, and nothing else. checkliving.py guards the
built pages against the exact dates the data attaches to a living person. It cannot see a sentence
somebody typed: two Blazevic pages carry the full dates of two living-aged people, and a Lerena
paragraph says more about its living person than the standard allows. The generators scrub at the
source, but hand-written pages, sources.json, corrections.json and notes are not generated.

WHAT IT DOES. It reads the archive's TRACKED text files (git ls-files, not the working tree: a gate
that scans only what is tracked misses the file you have not added yet, so an untracked file that
matches is itself a failure). Wherever one of them names a living person it checks the block of text
or the JSON record the name sits in:

    a full date, an ISO date, a slash date, or a year (1800-2099)         fail
    a life-event word: died, buried, baptised, christened, funeral,
    obituary, aged                                                         fail
    a DNA result (cM, haplogroup, DNA match / result / kit, 23andMe ...)    fail
    JSON only: a record whose name field is a living person's and that
    carries any field outside --allow-keys                                 fail

A year inside a URL or id (".../person/anna-rossi-1846/") is not read as prose, but is counted and
printed: for a living person it still tells a reader their birth year.

WHO IS LIVING is the archive's question, answered with living_rule.py. The archive writes a feed to
a file OUTSIDE the repo (a living person's name never goes in a tracked file for a gate):

    {"living":    [{"id": "p123", "names": ["Given Family", "Given Middle Family"]}, ...],
     "deadNames": ["Given Family", ...]}          # published dead people, to subtract homonyms

or calls checkprose.run(...) from Python.

A NAME SHARED WITH A DEAD PERSON cannot be told apart by a phrase, so it is skipped and counted, never
guessed at (the same subtraction checkliving.py makes). A phrase must be two words and 7 characters.

THE GATE CAN FAIL, AND SAYS WHAT IT EXAMINED. Before the real scan it plants a living name beside the
year 1899 in a temporary file and refuses to run if it does not catch it. It refuses an empty feed
(unless --allow-none), an empty file set, and untracked matching files. The summary prints how many
files were read, how many living phrases were searched for, and how many places named a living
person: a count of zero names found is printed as a number, not as "ok".

ALLOWANCES. A true false positive (a living person's name beside a year that is about somebody else)
goes in an allow file, never in a loosened pattern. Each entry needs a reason and is printed; an entry
that matches nothing fails, so the list cannot go stale.

    [{"file": "site/src/pages/about.astro", "phrase": "given family", "year": "1905",
      "reason": "the year is a 1905 emigration of his grandfather, named in the same sentence"}]

    python3 checkprose.py --root . --feed ../private/living-feed.json [--allow prose-allow.json] \\
        [--include site/src/data/sources.json --include site/src/data/corrections.json]

WHICH FILES. By default the hand-written pages (site/src/pages, site/src/content), notes/ and docs/
markdown and the top-level *.md. A hand-EDITED data file is named with --include. Generated data is
guarded by its generator's own scrub gate. Code comments (/* */ and whole-line //) are not read: they
are not published. HTML comments are, so they are.
"""
import os
import re
import sys
import json
import html
import fnmatch
import argparse
import tempfile
import unicodedata
import subprocess

MIN_CHARS = 7
WINDOW = 150      # characters either side of a name that count as "beside it", inside one block

# Hand-written prose only. A hand-EDITED data file (sources.json, corrections.json, errands.json,
# worklist.json, a notes file) is named with --include; generated data is guarded by its generator's own
# scrub gate, and scanning it here only meets the homonyms of a family that reuses its names.
DEFAULT_INCLUDE = [
    "site/src/pages/**/*.astro", "site/src/pages/**/*.md", "site/src/pages/**/*.mdx",
    "site/src/pages/**/*.html", "site/src/content/**/*.md", "site/src/content/**/*.mdx",
    "notes/**/*.md", "docs/**/*.md", "*.md",
]
DEFAULT_EXCLUDE = ["**/node_modules/**", "**/dist/**", "**/.git/**", "**/package-lock.json",
                   "**/decisions.json"]
TEXT_EXT = {".astro", ".md", ".mdx", ".html", ".txt", ".json", ".tsv", ".psv", ".csv", ".js",
            ".mjs", ".ts", ".yml", ".yaml"}
# Fields a living person's JSON record may carry: name, relationships, place. Anything else fails.
DEFAULT_ALLOW_KEYS = {
    "id", "pid", "slug", "url", "href", "name", "n", "who", "title", "label", "sex", "gender",
    "father", "mother", "parents", "spouse", "spouses", "partner", "partners", "children",
    "child", "siblings", "sibling", "rel", "relation", "relations", "relationship",
    "place", "town", "city", "country", "region", "line", "living", "support", "href",
    "fid", "fam", "family", "surname", "given", "forename", "first", "last", "kin", "link",
}

MONTHS = (r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|"
          r"June|July|August|September|October|November|December|Gennaio|Febbraio|Marzo|Aprile|"
          r"Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre")
FULL_DATE = re.compile(r"\b\d{1,2}\s+(?:" + MONTHS + r")[a-z]*\.?\s+(?:1[89]\d\d|20\d\d)\b", re.I)
MONTH_YEAR = re.compile(r"\b(?:" + MONTHS + r")[a-z]*\.?,?\s+(?:1[89]\d\d|20\d\d)\b", re.I)
ISO_DATE = re.compile(r"\b(?:1[89]\d\d|20\d\d)-\d{2}-\d{2}\b")
SLASH_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/(?:1[89]\d\d|20\d\d)\b")
YEAR = re.compile(r"(?<![\w/])(?<![A-Za-z]-)(?:1[89]\d\d|20\d\d)(?![\w/]|-[A-Za-z])")
SLUG_YEAR = re.compile(r"[A-Za-z]+-(?:[A-Za-z]+-)*(?:1[89]\d\d|20\d\d)\b")
EVENT = re.compile(r"\b(?:died|buried|baptis(?:ed|m)|baptiz(?:ed|m)|christened|funeral|obituary|aged)\b", re.I)
# A living person's DNA result is a detail the standard does not allow (it says more than name, relationships and
# place, and a match or a haplogroup identifies a living relative). Lerena found /dna/ discussing exactly that.
DNA = re.compile(r"\b(?:\d+(?:\.\d+)?\s*cM|centimorgans?|haplogroups?|mtDNA|Y-?DNA|autosomal|shared DNA|"
                 r"DNA\s+(?:match(?:es)?|results?|tests?|kits?|segments?|cousins?)|ethnicity estimates?|"
                 r"AncestryDNA|23andMe|FamilyTreeDNA|GEDmatch)\b", re.I)
URLISH = re.compile(r"(?:https?://\S+|/[A-Za-z][\w%.~-]*(?:/[\w%.~-]*)*)")
BLOCK_BREAK = re.compile(r"(?:\n|</?(?:p|li|tr|td|th|h[1-6]|div|section|article|figure|dd|dt|blockquote|br)\b[^>]*>)", re.I)


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().replace("’", "'").split())


def phrases(names):
    out = set()
    for n in names:
        f = fold(re.sub(r"\s*\(.*?\)", " ", n or ""))
        parts = f.split()
        if len(parts) < 2:
            continue
        for p in (" ".join(parts), parts[0] + " " + parts[-1]):
            if len(p) >= MIN_CHARS:
                out.add(p)
    return out


def name_regex(phrase):
    return re.compile(r"(?<![\w])" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"(?![\w])")


# ---- what a block says ------------------------------------------------------------------------

def flags_in(text):
    """What a block of text says that the standard does not allow: ([(kind, value)], slug_year_count).
    The value is kept for allowances and is NEVER printed (a log must not carry a living person's date).
    A year inside a URL or id is not prose; it is counted apart."""
    bare = URLISH.sub(" ", text)
    slug_years = len(SLUG_YEAR.findall(text))
    why = []
    for rx, label in ((FULL_DATE, "a full date"), (MONTH_YEAR, "a month and year"),
                      (ISO_DATE, "an ISO date"), (SLASH_DATE, "a slash date")):
        m = rx.search(bare)
        if m:
            why.append((label, m.group(0)))
    if not why:
        for y in sorted(set(YEAR.findall(bare))):
            why.append(("a year", y))
            break
    m = EVENT.search(bare)
    if m:
        why.append(("a life-event word", m.group(0).lower()))
    m = DNA.search(bare)
    if m:
        why.append(("a DNA result", m.group(0).lower()))
    return why, slug_years


def blocks_with(text, rx, folded=None):
    """Yield (start, end, block) for each block of `text` containing a match of rx. A block runs between
    paragraph / list / row / heading breaks and is capped to WINDOW characters either side of the name."""
    breaks = sorted({0, len(text)} | {x for m in BLOCK_BREAK.finditer(text) for x in (m.start(), m.end())})
    for m in rx.finditer(folded if folded is not None else fold_keep(text)):
        s, e = m.start(), m.end()
        lo = max([b for b in breaks if b <= s] or [0])
        hi = min([b for b in breaks if b >= e] or [len(text)])
        lo, hi = max(lo, s - WINDOW), min(hi, e + WINDOW)
        yield s, text[lo:hi]


def fold_keep(text):
    """Fold to lower case without accents, keeping every offset the same as in `text`."""
    out = []
    for c in text:
        d = unicodedata.normalize("NFKD", c)
        d = "".join(x for x in d if not unicodedata.combining(x))
        r = (d[:1] or c).lower()
        out.append(r if len(r) == 1 else c)
    return "".join(out).replace("’", "'")


# ---- JSON -------------------------------------------------------------------------------------

NAME_KEYS = ("name", "n", "who", "title", "label")


def walk_json(node, rxs, allow_keys, found, path=""):
    """found: list of (phrase, reasons, slugyears, where)."""
    if isinstance(node, dict):
        named = None
        for k in NAME_KEYS:
            v = node.get(k)
            if isinstance(v, str):
                fv = fold(v)
                for ph, rx in rxs:
                    if rx.search(fv):
                        named = ph
                        break
            if named:
                break
        if named:
            extra = [k for k, v in node.items() if k not in allow_keys and v not in (None, "", [], {}, False)]
            blob = json.dumps({k: v for k, v in node.items() if k not in NAME_KEYS}, ensure_ascii=False)
            why, sy = flags_in(blob)
            if extra:
                why.append(("fields beyond the standard", ", ".join(sorted(extra)[:6])))
            found.append((named, why, sy, path or "$"))
            return
        for k, v in node.items():
            walk_json(v, rxs, allow_keys, found, path + "/" + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_json(v, rxs, allow_keys, found, path + "[%d]" % i)
    elif isinstance(node, str):
        folded = fold_keep(node)         # once per string, not once per phrase
        for ph, rx in rxs:
            if ph.split(" ", 1)[0] not in folded:
                continue
            for pos, block in blocks_with(node, rx, folded):
                why, sy = flags_in(block)
                found.append((ph, why, sy, path))


def strip_code_comments(text):
    """Blank out /* ... */ and whole-line // comments (not published), keeping every offset. HTML comments stay:
    they ARE published."""
    text = re.sub(r"(?s)/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    return re.sub(r"(?m)^(\s*)//.*$", lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), text)


def scan_text(raw, rel, rxs, allow_keys):
    """Return a list of (phrase, reasons, slug_years, where) for one file's text."""
    found = []
    if rel.endswith(".json"):
        try:
            walk_json(json.loads(raw), rxs, allow_keys, found)
            return found
        except ValueError:
            pass                      # not valid JSON: read it as text
    if rel.endswith((".tsv", ".psv", ".csv")):
        for ln, line in enumerate(raw.splitlines(), 1):
            fl = fold_keep(line)
            for ph, rx in rxs:
                if rx.search(fl):
                    why, sy = flags_in(line)
                    found.append((ph, why, sy, "line %d" % ln))
        return found
    text = html.unescape(raw)
    if rel.endswith((".astro", ".js", ".mjs", ".ts")):
        text = strip_code_comments(text)
    folded = fold_keep(text)             # once per file, not once per phrase
    for ph, rx in rxs:
        if ph.split(" ", 1)[0] not in folded:
            continue
        for pos, block in blocks_with(text, rx, folded):
            why, sy = flags_in(block)
            found.append((ph, why, sy, "offset %d" % pos))
    return found


# ---- the files --------------------------------------------------------------------------------

def match(rel, pats):
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, p.replace("**/", "")) for p in pats)


def git(root, *a):
    return subprocess.run(["git", "-C", root] + list(a), capture_output=True, text=True)


def list_files(root, include, exclude, use_git):
    untracked = []
    if use_git:
        r = git(root, "ls-files", "-z")
        if r.returncode != 0:
            raise SystemExit("checkprose: %s is not a git checkout (use --no-git to scan the working tree)" % root)
        files = [f for f in r.stdout.split("\0") if f]
        u = git(root, "ls-files", "-z", "--others", "--exclude-standard")
        untracked = [f for f in u.stdout.split("\0") if f and match(f, include) and not match(f, exclude)]
    else:
        files = []
        for d, ds, fs in os.walk(root):
            ds[:] = [x for x in ds if x not in ("node_modules", ".git", "dist")]
            for f in fs:
                files.append(os.path.relpath(os.path.join(d, f), root))
    keep = [f for f in files if match(f, include) and not match(f, exclude)
            and os.path.splitext(f)[1].lower() in TEXT_EXT]
    return sorted(keep), sorted(untracked)


def run(root, living, dead_names, include=None, exclude=None, allow=None, allow_keys=None,
        use_git=True, allow_none=False, allow_untracked=False, quiet=False):
    """Return (failures, summary). living: list of name lists. dead_names: published dead people.
    NOTE: `include` REPLACES the default file set here (the command line's --include ADDS to it). A caller
    that wants the defaults plus its own files passes DEFAULT_INCLUDE + [...]; passing only its own list
    reads no pages or notes and undercounts (found by the D'Arcy session, 17 Oct 2026)."""
    include = include or DEFAULT_INCLUDE
    exclude = exclude or DEFAULT_EXCLUDE
    allow_keys = set(allow_keys or DEFAULT_ALLOW_KEYS)
    dead = {fold(re.sub(r"\s*\(.*?\)", " ", n)) for n in dead_names or []}
    dead_phr = set()
    for n in dead_names or []:
        dead_phr |= phrases([n])
    ph_all = set()
    for names in living:
        ph_all |= phrases(names)
    ambiguous = sorted(p for p in ph_all if p in dead_phr)
    searched = sorted(ph_all - set(ambiguous))
    fails = []
    if not searched and not allow_none:
        return (["the feed gave no living phrase to search for (%d name lists, %d shared with dead people); refusing "
                 "to pass on nothing. Use --allow-none only for an archive that publishes no living person" %
                 (len(living), len(ambiguous))], {})
    files, untracked = list_files(root, include, exclude, use_git)
    if not files:
        return (["no tracked file matched --include under %s; refusing to pass on nothing" % root], {})
    if untracked and not allow_untracked:
        for u in untracked[:20]:
            fails.append("%s: matches --include but is not tracked, so this gate never read it (git add it)" % u)
    rxs = [(p, name_regex(p)) for p in searched]
    allow = list(allow or [])
    used = [0] * len(allow)
    places = slug_total = 0
    per_file = {}
    for rel in files:
        try:
            raw = open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
        except OSError as e:
            fails.append("%s: unreadable (%s)" % (rel, e))
            continue
        for ph, why, sy, where in scan_text(raw, rel, rxs, allow_keys):
            places += 1
            slug_total += 1 if sy else 0
            if not why:
                continue
            hit = None
            for i, a in enumerate(allow):
                if a.get("file") == rel and fold(a.get("phrase", "")) == ph and \
                   (not a.get("year") or any(a["year"] in v for _, v in why)):
                    hit = i
                    break
            if hit is not None:
                used[hit] += 1
                continue
            per_file.setdefault(rel, []).append((where, "; ".join(sorted({k for k, _ in why}))))
    for rel, items in sorted(per_file.items()):
        # never print the name itself: the file, the place in it, and what is wrong
        fails.append("%s: names a living person with %s (%d place%s: %s)" % (
            rel, items[0][1], len(items), "" if len(items) == 1 else "s", ", ".join(w for w, _ in items[:4])))
    for i, a in enumerate(allow):
        if not a.get("reason"):
            fails.append("allow entry %d (%s) has no reason" % (i, a.get("file")))
        if not used[i]:
            fails.append("allow entry %d (%s) matches nothing and must be removed" % (i, a.get("file")))
    summary = {"files": len(files), "phrases": len(searched), "ambiguous": len(ambiguous),
               "places": places, "slug_years": slug_total, "allowed": sum(used),
               "untracked": len(untracked)}
    return fails, summary


# ---- the self-proof: the gate must be able to fail --------------------------------------------

PLANT_NAME = "Fixtura Zzyzx"          # invented; no living person has it
PLANT_YEAR = "1899"                   # impossible for a living person


def prove():
    """Plant a living name beside an impossible year, and a clean control. Returns '' or what is wrong."""
    with tempfile.TemporaryDirectory(prefix="checkprose-") as t:
        os.makedirs(os.path.join(t, "site", "src", "pages"))
        bad = os.path.join(t, "site", "src", "pages", "bad.astro")
        ok = os.path.join(t, "site", "src", "pages", "ok.astro")
        open(bad, "w").write("<p>%s, son of Aurelia Qqvox, born %s in Zagreb.</p>" % (PLANT_NAME, PLANT_YEAR))
        open(ok, "w").write("<p>%s, son of Aurelia Qqvox, of Zagreb, Croatia.</p>" % PLANT_NAME)
        f, s = run(t, [[PLANT_NAME]], [], use_git=False)
        if not any("bad.astro" in x for x in f):
            return "a living name beside the year %s was not caught" % PLANT_YEAR
        if any("ok.astro" in x for x in f):
            return "a living name with only a relationship and a place was refused (a false positive)"
        if s.get("places") != 2:
            return "the gate found %s places naming the planted person, expected 2" % s.get("places")
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--feed", help="JSON feed of living names, kept OUTSIDE the repo")
    ap.add_argument("--include", action="append", default=[],
                    help="a hand-edited file or glob to read as well as the default pages and notes, repeatable")
    ap.add_argument("--exclude", action="append")
    ap.add_argument("--allow", help="JSON list of reasoned allowances")
    ap.add_argument("--allow-keys", help="comma-separated JSON fields a living record may carry (adds to the default)")
    ap.add_argument("--no-git", action="store_true", help="scan the working tree, not tracked files (tests only)")
    ap.add_argument("--allow-none", action="store_true")
    ap.add_argument("--allow-untracked", action="store_true")
    a = ap.parse_args()

    why = prove()
    if why:
        print("checkprose: FAIL, the gate's own self-proof did not hold: " + why)
        return 1
    if not a.feed:
        print("checkprose: not run (no --feed: the archive has not said who is living)")
        return 2
    try:
        feed = json.load(open(a.feed, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("checkprose: FAIL, cannot read the feed %s (%s)" % (a.feed, e))
        return 1
    living = [x.get("names", []) for x in feed.get("living", [])]
    allow = json.load(open(a.allow, encoding="utf-8")) if a.allow else []
    keys = set(DEFAULT_ALLOW_KEYS) | set(filter(None, (a.allow_keys or "").split(",")))
    fails, s = run(a.root, living, feed.get("deadNames", []), DEFAULT_INCLUDE + a.include, a.exclude, allow, keys,
                   not a.no_git, a.allow_none, a.allow_untracked)
    if fails:
        print("checkprose: FAIL (%d)" % len(fails))
        for f in fails:
            print("  - " + f)
        if s:
            print("  examined: %(files)d tracked files read, %(phrases)d living phrases searched "
                  "(%(ambiguous)d skipped as shared with a dead person), %(places)d places name a living person" % s)
        return 1
    print("checkprose: ok. %(files)d tracked files read, %(phrases)d living phrases searched "
          "(%(ambiguous)d skipped as shared with a dead person), %(places)d places name a living person, "
          "none says more than the standard allows; %(slug_years)d name a year only inside a url/id; "
          "%(allowed)d reasoned allowance(s) used." % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
