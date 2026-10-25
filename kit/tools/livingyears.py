#!/usr/bin/env python3
"""THE PRINTED-YEAR GATE: no year or date on or after the living line is printed for a person with no death.

    python3 checkliving.py --dist dist --data src/data --years [--config standard.json]
                           [--allow-file data/living-year-allow.json] [--allow-prefix /x/ ...]
                           [--today-year N] [--strict-allow] [--years-only]

    THE LINE  =  living_rule.cutoff_year(): this year minus LIVING_YEARS (1946 in 2026, 1947 in 2027). Derived, never typed.
    Born on or after the line with no death RECORD is a living person: named with relationships and town and country,
    and nothing more. This gate fails when ANY built page or data file prints a year or date on or after the line for
    such a person.

WHY IT EXISTS, AND WHY checkliving's DATE GATE DID NOT CATCH IT (25 October 2026). The older gate harvests the FULL
dates the data attaches to a person flagged living and looks for those exact strings. That guards the people the rule
calls living, and the rule had two holes (a public-source citation, and an undated "deceased" flag, each made a person
born in 1948 "not living", so nobody was looking for their year); and a bare year is not a date, so a year typed into
prose, a list, a newspaper transcription or a search index was in nobody's harvest. This gate does not start from a
flag. It starts from what is PRINTED, and from a person set it derives itself with living_rule (birth year inside the
window, no death record), whatever the row's own living flag says.

THREE DETECTORS, over every built .html (visible text, JSON-LD and the text attributes), .json, .xml and .txt:

  BIRTH-SHAPE  the SHAPE of a birth: «b. 1949», «born 24 April 1949», «(1950-)», "birthDate": "1949-04-24", with a year
               in [line, this year] and NO DEATH BESIDE IT. A death beside it is a death word within 90 characters
               after the year (d., died, dead, buried, deceased...), a closed span «1950-1999», or the name of a
               person the data records dead whose birth year is within three of it. A bare year is never screened by
               this detector (every year appears somewhere on a genealogy site): the shape of a birth is.
  NAME-YEAR    (needs the people data) a living person's NAME PHRASE followed within 80 characters, or preceded within
               40, by that person's own birth year. Exact namesakes of a dead person are subtracted (the phrase cannot
               tell them apart), and a name inside a longer published name is not a hit.
  JSON-ROW     a row in a built .json that carries a birth field (born, birth, birthYear, byear...) with a year on or
               after the line and no death field. A flag-only death field ("deceased", true) counts as NO death.

The person set is read from the archive's own data the way the kit's other gates read it (checkliving.rows_of: name, born
and died keys, a living flag, "living" written where a date goes). A row is a LIVING person here when its birth year is on
or after the line and death_kind(...) is not a record; a row with a death record is a dead person (its name is subtracted
as a namesake and its birth year excuses a nearby birth).

ESCAPES, each one a decision (a reason of at least 8 characters, or the gate refuses to run):
  --allow-file / standard.json "living_years": {"allow_file": ...}   a registry of entries {text|contains, file?, why|reason}.
        The four archives' data/living-year-allow.json files are read as they stand ({"allow": [{text, why}]} and
        {"snippets": [{file, contains, reason}]}). The text is removed from what the gate reads. An entry that matched
        nothing is STALE and is counted (a failure with --strict-allow).
  --allow-prefix /x/ (repeatable) / "living_years": {"allow_prefixes": [...]}   built files that are not people (a feed, a
        sitemap, a gazetteer), matched against the file's address.

A GATE THAT CAN ONLY PASS PROVES NOTHING. Before the verdict the gate runs its own detectors over a planted fault (`probe`)
and refuses to pass if they miss it; kit/tools/livingyears_selftest.py plants one fault per detector in a copy of a build.
Nothing is printed about a person except the file and a short context: counts first.

EXIT CODES: 0 pass; 1 breach, or a run that could not look (no pages, an unreadable data file, no people read).
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import living_rule as lr  # noqa: E402

SERVED_EXT = (".html", ".json", ".xml", ".txt", ".webmanifest")
MIN_PHRASE = 7
CONTEXT = 100

BORN_KEYS = ("born", "b", "birth", "byear", "b_date", "birthYear", "bornYear", "birthDate", "dob", "yob")
DIED_KEYS = ("died", "d", "death", "dyear", "d_date", "deathYear", "deathDate", "dod", "buried", "burial")
DEATH_PLACE_KEYS = ("deathPlace", "death_place", "dplace")
DEAD_FLAG_KEYS = ("dead", "deceased", "isDead")
RECORD_KEYS = ("deathRecorded",)
NAME_KEYS = ("name", "n", "who", "t")
LIVING_KEYS = ("living", "presumedLiving", "alive", "isLiving")

Y = r"(1[0-9]{3}|20[0-9]{2})"
YEAR_RX = re.compile(r"(?<!\d)" + Y + r"(?!\d)")
# How a BIRTH is written. {Y} is tested against the line; a bare year is not screened.
BIRTH = [
    ("b.", re.compile(r"(?<![\w])b\.?\s?(?:c\.?\s?|ca\.?\s?)?(?:\d{1,2}\s+[A-Za-z]{3,9}\.?\s+)?" + Y + r"(?!\d)")),
    ("born", re.compile(r"\b[Bb][Oo][Rr][Nn](?: on| in| at)?(?: [A-Za-z]+){0,3}? (?:\d{1,2} )?(?:[A-Za-z]{3,9}\.? )?(?:c\. )?" + Y + r"(?!\d)")),
    ("open", re.compile(r"\((?:b\. ?)?" + Y + r"\s?[–—-]\s?\)")),
    ("birthDate", re.compile(r"birthDate\W{1,6}" + Y)),
]
DEATH = re.compile(r"(?<![A-Za-z])(?:d\.|died|dies|dead|death|deaths|buried|burial|killed|deceased|murdered|funeral|"
                   r"obituary|estate notice|widow)(?![a-z])|†|[–—-]\s*(?:\d{1,2}\s+\w+\s+)?(?:1[0-9]{3}|20[0-9]{2})", re.I)
SAID_LIVING = ("living", "alive", "still living", "presumed living", "vivente")


# ---- text helpers -----------------------------------------------------------

def fold(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or ""))
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip().lower()


def norm(name):
    name = re.sub(r"\s*\(.*?\)", " ", name or "")
    name = re.sub(r"[\"“”]", " ", name)
    return " ".join(name.split())


def phrases_of(full):
    parts = norm(full).split()
    if len(parts) < 2:
        return set()
    return {" ".join(parts), parts[0] + " " + parts[-1]}


_ATTR = re.compile(r'\b(?:content|alt|title|aria-label|datetime)\s*=\s*"([^"]*)"', re.I)


def text_of(path, raw):
    """What a reader or a crawler is given. HTML: the visible text, the JSON-LD and the text attributes; else as written."""
    if not path.lower().endswith(".html"):
        return re.sub(r"\s+", " ", raw.replace("\\n", " "))
    ld = " ".join(re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', raw, re.S | re.I))
    attrs = " ".join(_ATTR.findall(raw))
    body = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", raw)
    vis = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return re.sub(r"\s+", " ", vis + " " + html.unescape(attrs) + " " + ld)


def year_of(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        v = int(v)
        return v if 1000 <= v <= 2999 else None
    m = YEAR_RX.search(str(v))
    return int(m.group(1)) if m else None


# ---- the people (the archive's own data, read the way checkliving reads it) ----

class Person:
    __slots__ = ("name", "born", "kind", "flagged")

    def __init__(self, name, born, kind, flagged):
        self.name, self.born, self.kind, self.flagged = name, born, kind, flagged


def _first(r, keys):
    for k in keys:
        v = r.get(k)
        if v not in (None, "", "—", "-", False):
            return v
    return None


def person_of_row(r):
    """-> Person or None. kind is lr.death_kind: "record", "flag" or None."""
    name = norm(str(_first(r, NAME_KEYS) or ""))
    if len(name) < 3:
        return None
    died = _first(r, DIED_KEYS)
    buried = r.get("buried") if "buried" in r else None
    place = _first(r, DEATH_PLACE_KEYS)
    flag = any(r.get(k) is True for k in DEAD_FLAG_KEYS)
    rec = any(r.get(k) is True for k in RECORD_KEYS)
    kind = lr.death_kind(died, buried, place, flag, rec)
    bv = _first(r, BORN_KEYS)
    flagged = any(r.get(k) is True for k in LIVING_KEYS) or str(r.get("conf", "")).lower() == "living" \
        or str(bv or "").strip().lower() in SAID_LIVING
    return Person(name, year_of(bv), kind, flagged)


def rows_deep(obj, depth=0):
    """Every dict anywhere in a parsed JSON document (a people file, a search index, an atlas)."""
    if depth > 12:
        return
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            if isinstance(v, (dict, list)):
                yield from rows_deep(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, (dict, list)):
                yield from rows_deep(v, depth + 1)


def load_people(data_dir, unreadable):
    """[Person] from every .json under data_dir (non-recursive, like checkliving.from_data)."""
    people = []
    if not os.path.isdir(data_dir):
        return None
    for f in sorted(os.listdir(data_dir)):
        if not f.endswith(".json"):
            continue
        try:
            j = json.load(open(os.path.join(data_dir, f), encoding="utf-8"))
        except Exception as e:
            unreadable.append((f, str(e).split("\n")[0][:90]))
            continue
        for r in rows_deep(j):
            p = person_of_row(r)
            if p and (p.born is not None or p.kind or p.flagged):
                people.append(p)
    return people


# ---- the registry of exceptions ----------------------------------------------

class Allow:
    def __init__(self):
        self.entries = []        # {text, file, reason, used}
        self.prefixes = []

    def add(self, text, reason, file=None):
        self.entries.append({"text": text, "file": file, "reason": reason, "used": 0})

    def load(self, path):
        """Read an archive's registry as it stands. Raises ValueError (exit 1) on an entry with no reason."""
        j = json.load(open(path, encoding="utf-8"))
        rows = []
        for k in ("allow", "snippets"):
            for e in (j.get(k) or []) if isinstance(j, dict) else []:
                rows.append(e)
        for e in rows:
            text = e.get("text") or e.get("contains")
            why = str(e.get("why") or e.get("reason") or "").strip()
            if not text or len(why) < 8:
                raise ValueError("%s: an allow entry needs its text and a reason of at least 8 characters" % path)
            self.add(text, why, e.get("file"))

    def strip(self, rel, text):
        for e in self.entries:
            if e["file"] and e["file"] not in ("*", rel) and not rel.endswith(e["file"]):
                continue
            if e["text"] in text:
                e["used"] += 1
                text = text.replace(e["text"], " ")
        return text

    def exempt(self, rel):
        a = "/" + rel
        return any(a.startswith(p) for p in self.prefixes)

    def stale(self):
        return [e for e in self.entries if not e["used"]]


# ---- the detectors -------------------------------------------------------------

class Finder:
    """The person set reduced to what the detectors need, for one cutoff."""

    def __init__(self, people, today_year):
        self.today = int(today_year)
        self.cut = lr.cutoff_year(self.today)
        self.living = [p for p in (people or []) if p.born is not None and p.born >= self.cut and p.born <= self.today
                       and p.kind != "record"]
        self.dead_young = [p for p in (people or []) if p.born is not None and p.born >= self.cut and p.kind == "record"]
        dead_phr = set()
        for p in people or []:
            if p.kind == "record" or (p.born is not None and p.born < self.cut):
                dead_phr |= {x.lower() for x in phrases_of(p.name)}
        self.dead_phrases = dead_phr
        self.dead_forms = []
        for p in self.dead_young:
            for ph in phrases_of(p.name) | {fold(p.name)}:
                if len(ph) > 5:
                    self.dead_forms.append((fold(ph), p.born))
        forbidden = {}
        for p in self.living:
            for ph in phrases_of(p.name):
                low = ph.lower()
                if len(low) < MIN_PHRASE or low in dead_phr:
                    continue                      # an exact namesake of a dead person: indistinguishable
                forbidden.setdefault(low, set()).add(p.born)
        self.forbidden = forbidden
        dead_full = [n for n in (norm(p.name) for p in (people or []) if p.kind == "record" or (p.born is not None and p.born < self.cut))
                     if len(n.split()) >= 2]
        self.covers = {ph: sorted((n for n in dead_full if ph in n.lower() and len(n) > len(ph)), key=len, reverse=True)
                       for ph in forbidden}
        self.rx = re.compile(r"\b(" + "|".join(sorted(map(re.escape, forbidden), key=len, reverse=True)) + r")\b", re.I) \
            if forbidden else None

    def named_dead(self, window, y):
        w = fold(window)
        return any(abs(by - y) <= 3 and re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", w) for n, by in self.dead_forms)

    def births(self, text):
        """[(start, end, year, shape)] for every birth-shaped year in [cut, today]."""
        hits = []
        for shape, rx in BIRTH:
            for m in rx.finditer(text):
                y = int(m.group(1))
                if self.cut <= y <= self.today:
                    hits.append((m.start(), m.end(), y, shape))
        return hits

    def scan_text(self, rel, text):
        """-> [(rel, detector, context)]"""
        out, seen = [], set()
        for s, e, y, shape in self.births(text):
            after, before = text[e:e + 90], text[max(0, s - 160):s]
            if DEATH.search(after) or DEATH.search(text[s:e]) or self.named_dead(before + " " + text[s:e] + after[:30], y):
                continue
            ctx = text[max(0, s - 60):e + 40].strip()[:CONTEXT]
            if (rel, ctx) in seen:
                continue
            seen.add((rel, ctx))
            out.append((rel, "birth-shape", "a birth (%d) with no death beside it: «%s»" % (y, ctx)))
        if self.rx:
            low = text
            for m in self.rx.finditer(low):
                ph = m.group(1).lower()
                years = self.forbidden.get(ph, ())
                window = low[max(0, m.start() - 40):m.end() + 40].lower()
                if any(longer.lower() in window for longer in self.covers.get(ph, ())):
                    continue                      # part of a longer published name
                tail = low[m.end():m.end() + 80]
                head = low[max(0, m.start() - 40):m.start()]
                hit = None
                ym = YEAR_RX.search(tail)
                if ym and int(ym.group(1)) in years:
                    hit = ym.group(1)
                else:
                    ys = list(YEAR_RX.finditer(head))
                    if ys and int(ys[-1].group(1)) in years and not re.search(r"\d", head[ys[-1].end():]):
                        hit = ys[-1].group(1)
                if hit:
                    ctx = low[max(0, m.start() - 30):m.end() + 70].strip()[:CONTEXT]
                    if (rel, "n", ctx) in seen:
                        continue
                    seen.add((rel, "n", ctx))
                    out.append((rel, "name-year", "a living person's name beside their own birth year (%s): «%s»" % (hit, ctx)))
        return out

    def scan_json_rows(self, rel, doc):
        out = []
        for r in rows_deep(doc):
            bv = None
            for k in BORN_KEYS:
                if k in r and not isinstance(r[k], (dict, list)):
                    bv = r[k]
                    break
            if isinstance(bv, str) and len(bv) > 40:
                continue                          # prose in a short key (a body, a description): the text detectors read it
            y = year_of(bv)
            if y is None or not (self.cut <= y <= self.today):
                continue
            died = _first(r, DIED_KEYS)
            place = _first(r, DEATH_PLACE_KEYS)
            flag = any(r.get(k) is True for k in DEAD_FLAG_KEYS)
            rec = any(r.get(k) is True for k in RECORD_KEYS)
            if lr.death_kind(died, None, place, flag, rec) == "record":
                continue
            # a closed span in a combined field («1950–1999») is a death beside the year
            if isinstance(bv, str) and DEATH.search(bv):
                continue
            who = norm(str(_first(r, NAME_KEYS) or "")) or "unnamed"
            out.append((rel, "json-row", "a data row carries a birth year (%d) and no death record (%s)" % (y, who)))
        return out


def probe(today_year):
    """A planted fault, through the REAL detectors. Returns (ok, why). A gate that cannot catch this must not pass."""
    cut = lr.cutoff_year(today_year)
    people = [Person("Probe Livingperson", cut, None, False), Person("Probe Deadperson", cut, "record", False)]
    f = Finder(people, today_year)
    miss = []
    if not f.scan_text("p.html", "He was b. %d in Testville." % cut):
        miss.append("birth-shape")
    if not f.scan_text("p.html", "Probe Livingperson, Testville, %d" % cut):
        miss.append("name-year")
    if not f.scan_json_rows("p.json", [{"name": "x", "born": cut}]):
        miss.append("json-row")
    if f.scan_text("p.html", "He was b. %d and d. %d." % (cut, cut + 1)) or f.scan_text("p.html", "He was b. %d in Testville." % (cut - 1)):
        miss.append("a death or an older birth was reported")
    return (not miss), ("detectors missed or over-fired on the planted fault: " + ", ".join(miss)) if miss else "ok"


# ---- the run ---------------------------------------------------------------------

def served_files(dist):
    vanished = 0
    files = []
    for root, _, fns in os.walk(dist):
        for fn in fns:
            if fn.lower().endswith(SERVED_EXT):
                files.append(os.path.join(root, fn))
    return files, vanished


def run(dist, data_dir, today_year=None, allow=None, quiet=False, min_pages=5, strict_allow=False, say=print):
    """-> (exit_code, fails, info). fails: [(rel, detector, message)]."""
    today = int(today_year or lr.this_year())
    allow = allow or Allow()
    info = {}
    if not os.path.isdir(dist):
        say("  FAIL  living-years  no %s: build first" % dist)
        return 1, [], info
    files, _ = served_files(dist)
    pages = [f for f in files if f.lower().endswith(".html")]
    if len(pages) < min_pages:
        say("  FAIL  living-years  only %d page(s) under %s: refusing to pass on an unfinished or empty build" % (len(pages), dist))
        return 1, [], info
    unreadable = []
    people = load_people(data_dir, unreadable)
    if people is None:
        say("  FAIL  living-years  the data directory %s does not exist, so this gate does not know who is living. "
            "Pass --data, or run from the site directory." % data_dir)
        return 1, [], info
    if unreadable:
        say("  FAIL  living-years  %d data file(s) could not be read, so this gate does not know who is living" % len(unreadable))
        for f, why in unreadable:
            say("          %s: %s" % (f, why))
        return 1, [], info
    if not people:
        say("  FAIL  living-years  no person with a name and a birth year or a death was read from %s: the people are not where "
            "this gate looks (a file it cannot see is not an archive with nobody in it)" % data_dir)
        return 1, [], info
    ok, why = probe(today)
    if not ok:
        say("  FAIL  living-years  the gate's own probe failed, so a pass would mean nothing: " + why)
        return 1, [], info
    finder = Finder(people, today)
    fails = []
    scanned = 0
    for path in sorted(files):
        rel = os.path.relpath(path, dist).replace(os.sep, "/")
        if allow.exempt(rel):
            continue
        try:
            raw = open(path, encoding="utf-8", errors="replace").read()
        except FileNotFoundError:
            say("  FAIL  living-years  %s disappeared while this ran: another build is in flight. Refusing to pass on a partial read." % rel)
            return 1, [], info
        raw = allow.strip(rel, raw)
        scanned += 1
        text = text_of(path, raw)
        fails += finder.scan_text(rel, text)
        if path.lower().endswith(".json"):
            try:
                doc = json.loads(raw)
            except Exception:
                doc = None
            if doc is not None:
                fails += finder.scan_json_rows(rel, doc)
    stale = allow.stale()
    info.update(cut=finder.cut, today=today, files=scanned, living=len(finder.living), dead_young=len(finder.dead_young),
                stale=len(stale), allow_used=sum(1 for e in allow.entries if e["used"]))
    uniq = list(dict.fromkeys(fails))
    if uniq:
        say("  FAIL  living-years  %d breach(es): a year on or after %d (the living line for %d) printed for a person with no death:"
            % (len(uniq), finder.cut, today))
        for rel, det, msg in uniq[:40]:
            say("          /%s  [%s]  %s" % (rel, det, msg))
        if len(uniq) > 40:
            say("          ... and %d more" % (len(uniq) - 40))
        say("\n  A living person (born %d or later, no death recorded) shows a name, relationships and a town and country: no year, no date.\n"
            "  If this person has died, record the death in the data; do not silence the check. A year that is not a person's birth\n"
            "  goes in the registry (--allow-file) with its reason; a file that is not about people takes --allow-prefix." % finder.cut)
        return 1, uniq, info
    if stale and strict_allow:
        say("  FAIL  living-years  %d registry entr%s matched nothing (stale): delete %s" % (
            len(stale), "y" if len(stale) == 1 else "ies", "it" if len(stale) == 1 else "them"))
        return 1, [], info
    if not quiet:
        say("  ok    living-years  line %d (= %d - %d); %d files read; %d living by the rule and %d dead-young in %d data rows; no year on or after the "
            "line without a death beside it; %d registry entr%s used, %d stale · detectors: birth-shape, name-year, json-row"
            % (finder.cut, today, lr.LIVING_YEARS, scanned, len(finder.living), len(finder.dead_young), len(people),
               info["allow_used"], "y" if info["allow_used"] == 1 else "ies", len(stale)))
    return 0, [], info


def load_config(path):
    """standard.json "living_years": {"allow_file", "allow_prefixes", "data"} -> dict (paths resolved against the file)."""
    if not path:
        return {}
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError("the config %s cannot be read (%s)" % (path, type(e).__name__))
    c = raw.get("living_years") or {}
    if not isinstance(c, dict):
        raise ValueError("config: 'living_years' must be an object")
    base = os.path.dirname(os.path.abspath(path))
    out = {}
    if c.get("allow_file"):
        p = c["allow_file"]
        out["allow_file"] = p if os.path.isabs(p) else os.path.join(base, p)
    if c.get("data"):
        p = c["data"]
        out["data"] = p if os.path.isabs(p) else os.path.join(base, p)
    pre = c.get("allow_prefixes") or []
    if not isinstance(pre, list) or not all(isinstance(x, str) and x.startswith("/") for x in pre):
        raise ValueError("config: living_years.allow_prefixes must be a list of root-relative prefixes such as \"/feed/\"")
    out["allow_prefixes"] = pre
    return out


def run_cli(dist, data, today_year=None, config=None, allow_file=None, allow_prefixes=(), strict_allow=False, quiet=False,
            say=print):
    try:
        cfg = load_config(config)
        allow = Allow()
        af = allow_file or cfg.get("allow_file")
        if af:
            if not os.path.exists(af):
                say("  FAIL  living-years  the registry %s does not exist" % af)
                return 1
            allow.load(af)
        allow.prefixes = list(cfg.get("allow_prefixes", [])) + list(allow_prefixes or [])
    except ValueError as e:
        say("  FAIL  living-years  " + str(e))
        return 1
    rc, _fails, _info = run(dist, data or cfg.get("data") or "src/data", today_year, allow, quiet, strict_allow=strict_allow, say=say)
    return rc
