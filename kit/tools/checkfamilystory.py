#!/usr/bin/env python3
"""The gate on the family story: the data behind components/StoryBook.astro, held to its own grammar.

(Not kit/tools/checkstory.py, which is older and checks something else: the children's site against the archives.)

WHY. The story is the one page that tells a family as a book, and it is the page most likely to say more than the papers
do, because prose wants to be smooth. Its grammar is what stops that: every paragraph is graded by its weakest claim, the
world around the people is kept apart and sourced, the trees and maps use the same solid/dashed/dotted outline for the same
three grades, and a living person is a relationship and a town and nothing else. A grammar nobody checks is a style, so this
checks it: the data against kit/data/story-schema.json, then the things a schema cannot say (a place outside its map, a living
person beside a year, a link that goes nowhere), then, with --dist, the BUILT page, read back independently of the component.
The contract is kit/docs/story.md.

    python3 checkfamilystory.py --story src/data/story.json --dist dist [--page /story/] [--person-base /people/]
                                [--living living.json] [--extents kit/data/story-extents.json] [--strict]
    python3 checkfamilystory.py --story src/data/story.json --no-dist        data only; says it did not look at the site
    python3 checkfamilystory.py --selftest        build a site around kit/data/story-example.json and plant every fault in it

--dist         the built site. Every person link, every internal link and #fragment, and the built story page itself.
--page         where the story page is built (default /story/). With --dist the page must exist.
--person-base  where a bare person slug is built (default /people/): `person:slug` and every node, card and paper link.
--living       a JSON list of names (or {"names": [...]}) that are living though the story does not say so: an archive's
               private list. A paragraph naming one of them within a hundred characters of a date fails, the same as for
               a node the story itself flags living.
--strict       warnings fail too.

Rules (the code is printed with every finding):
  S0  the data does not match the schema (a missing field, a wrong type, a grade that is not doc, inf or lore)
  S1  ids are unique (chapters, maps, paragraphs, tree nodes within a tree, places within a map) and every reference to a
      chapter (a ribbon card, a map, a place, a leg, a conflict) names a chapter that exists
  P1  every paragraph about the people has a grade of doc, inf or lore
  P2  every paragraph about the world has a source, archive or history, and a link to it
  P3  a documented paragraph links to its document (error); an inferred or family-lore one with no link says nothing to check (warned)
  C1  every chapter ends with at least one `papers` link; C2 each resolves in the built site
  R1  every ribbon card has every field (name, years, origin, originGrade, spouse, spouseOrigin, atPlace, atYear, living, chapter)
  R2  a living card carries no years and no year on its "at" line, and nothing in its text that is a date
  T1  a node flagged living carries no years and no date in its name
  T2  a minor is flagged living, is shown by initials only, has no years and no link to a page
  T3  a tree's thread names a node that is a child of the household (or the person above it)
  M1  every place has coordinates inside its map's extent; M2 the extent is a name from story-extents.json or a box
  M3  every leg's endpoints exist in its map; a leg's grade is doc, inf or lore
  M4  one place id has one set of coordinates on every map
  M5  a place that stands for living people is a country and a leg to or from it carries no years
  L1  no paragraph, card or note names a person who is living within a hundred characters of a date
  H1  every person link resolves to a built page; H2 every internal link resolves, and its #fragment to an id in the page
  V1  the built page has the chapters, in order;  V2 each paragraph is there with the grade or source the data gives it
  V3  the built ribbon has a card per generation, all with the same parts, and a living card shows no date
  V4  a built tree shows a living node with no date;  V5 every built map dot is inside its picture
  V6  the built page has a tree for every chapter that has one and a map for every map
Exit 0 clean (warnings do not fail unless --strict), 1 on any error, 2 on a file that cannot be read or when nothing was checked.
"""
import argparse, copy, json, os, re, shutil, subprocess, sys, tempfile
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
GRADES = ["doc", "inf", "lore"]
CARD_FIELDS = ["name", "years", "origin", "originGrade", "spouse", "spouseOrigin", "atPlace", "atYear", "living", "chapter"]
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
YEAR_RE = re.compile(r"(?<![\d.,-])(?:1[0-9]{3}|20[0-9]{2})(?!\d)")
DATE_RE = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:%s)\b|\b(?:%s)\s+\d{1,2}\b" % (MONTHS, MONTHS))
LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^)\s]+)\)")
WINDOW = 100


def has_date(s):
    s = str(s or "")
    return bool(YEAR_RE.search(s) or DATE_RE.search(s))


def is_initial(name):
    """One to three capital letters, each optionally followed by a stop (mirror of isInitial() in kit/lib/story.js)."""
    n = str(name or "").strip()
    toks = re.findall(r"[^\W\d_]\.?", n)
    return bool(n) and "".join(toks) == n and 1 <= len(toks) <= 3 and all(t[0].isupper() for t in toks)


def plain(s):
    s = LINK_RE.sub(r"\1", str(s or ""))
    s = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", s, flags=re.S)
    s = re.sub(r"«(.+?)»", r"\1", s, flags=re.S)
    return re.sub(r"\s+", " ", s.replace("`", "")).strip()


# ---------------------------------------------------------------- a small JSON-schema validator (the subset the schema uses)
def _type_ok(v, t):
    return {"object": isinstance(v, dict), "array": isinstance(v, list), "string": isinstance(v, str),
            "boolean": isinstance(v, bool), "null": v is None,
            "number": isinstance(v, (int, float)) and not isinstance(v, bool),
            "integer": isinstance(v, int) and not isinstance(v, bool)}.get(t, False)


def _ref(root, ref):
    node = root
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def schema_errors(v, sch, root, path=""):
    """Every way `v` fails `sch`, as (path, message). Empty when it fits."""
    errs = []
    if "$ref" in sch:
        return schema_errors(v, _ref(root, sch["$ref"]), root, path)
    t = sch.get("type")
    if t:
        ts = t if isinstance(t, list) else [t]
        if not any(_type_ok(v, x) for x in ts):
            return [(path, "should be %s, is %s" % (" or ".join(ts), type(v).__name__))]
    if "enum" in sch and v not in sch["enum"]:
        errs.append((path, "%r is not one of %s" % (v, ", ".join(map(str, sch["enum"])))))
    if "const" in sch and v != sch["const"]:
        errs.append((path, "should be %r" % (sch["const"],)))
    if isinstance(v, str):
        if len(v) < sch.get("minLength", 0):
            errs.append((path, "is empty" if sch.get("minLength") == 1 else "is shorter than %d" % sch["minLength"]))
        if "pattern" in sch and not re.search(sch["pattern"], v):
            errs.append((path, "%r does not match %s" % (v, sch["pattern"])))
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in sch and v < sch["minimum"]:
            errs.append((path, "%s is below %s" % (v, sch["minimum"])))
        if "maximum" in sch and v > sch["maximum"]:
            errs.append((path, "%s is above %s" % (v, sch["maximum"])))
    if isinstance(v, dict):
        for k in sch.get("required", []):
            if k not in v:
                errs.append((path, "has no %r" % k))
        props = sch.get("properties", {})
        for k, x in v.items():
            if k in props:
                errs += schema_errors(x, props[k], root, "%s.%s" % (path, k) if path else k)
            elif sch.get("additionalProperties") is False:
                errs.append((path, "has a field %r that the contract does not know" % k))
    if isinstance(v, list):
        if len(v) < sch.get("minItems", 0):
            errs.append((path, "has %d item(s), needs at least %d" % (len(v), sch["minItems"])))
        if "maxItems" in sch and len(v) > sch["maxItems"]:
            errs.append((path, "has %d items, at most %d" % (len(v), sch["maxItems"])))
        if "items" in sch:
            for i, x in enumerate(v):
                errs += schema_errors(x, sch["items"], root, "%s[%d]" % (path, i))
    if "oneOf" in sch or "anyOf" in sch:
        alts = sch.get("oneOf") or sch.get("anyOf")
        tries = [schema_errors(v, a, root, path) for a in alts]
        good = sum(1 for e in tries if not e)
        if good == 0:
            errs += min(tries, key=len)
        elif good > 1 and "oneOf" in sch:
            errs.append((path, "fits more than one alternative"))
    for sub in sch.get("allOf", []):
        errs += schema_errors(v, sub, root, path)
    if "if" in sch:
        cond = not schema_errors(v, sch["if"], root, path)
        if cond and "then" in sch:
            errs += schema_errors(v, sch["then"], root, path)
        if not cond and "else" in sch:
            errs += schema_errors(v, sch["else"], root, path)
    return errs


# ---------------------------------------------------------------- the built site
class Site:
    def __init__(self, dist):
        self.dist = dist
        self.cache = {}

    def page(self, path):
        p = path.split("#")[0].split("?")[0]
        if p in self.cache:
            return self.cache[p]
        rel = p.lstrip("/")
        cands = [os.path.join(self.dist, rel, "index.html")] if (p.endswith("/") or "." not in os.path.basename(rel)) else []
        cands.append(os.path.join(self.dist, rel))
        if rel and not rel.endswith("/"):
            cands.append(os.path.join(self.dist, rel + ".html"))
        txt = None
        for c in cands:
            if os.path.isfile(c):
                try:
                    txt = open(c, encoding="utf-8", errors="replace").read()
                except OSError:
                    pass
                break
        self.cache[p] = txt
        return txt

    def has_id(self, path, frag):
        txt = self.page(path)
        if txt is None:
            return False
        return bool(re.search(r"""\b(?:id|name)\s*=\s*["']%s["']""" % re.escape(frag), txt))


# ---------------------------------------------------------------- a small reader of the built page
class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids, self.text = tag, dict(attrs), parent, [], []

    def cls(self):
        return (self.attrs.get("class") or "").split()

    def all_text(self):
        return "".join(self.text) + "".join(k.all_text() for k in self.kids) + " ".join(
            str(self.attrs.get(a, "")) for a in ("aria-label", "title") if a in self.attrs)

    def walk(self):
        yield self
        for k in self.kids:
            yield from k.walk()


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "path", "line", "circle", "rect", "ellipse", "stop"}


class Doc(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, [(k, v if v is not None else "") for k, v in attrs], self.cur)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(Node(tag, [(k, v if v is not None else "") for k, v in attrs], self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.text.append(data)

    def find(self, pred):
        return [n for n in self.root.walk() if pred(n)]


# ---------------------------------------------------------------- the findings
class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, code, where, msg):
        self.errors.append((code, where, msg))

    def warn(self, code, where, msg):
        self.warnings.append((code, where, msg))


def load_extents(path=None):
    p = path or os.path.join(KIT, "data", "story-extents.json")
    return json.load(open(p, encoding="utf-8"))["extents"]


def resolve_extent(ext, presets):
    """Mirror of resolveExtent() in kit/lib/mapgeom.js."""
    if isinstance(ext, str):
        box = presets.get(ext)
    elif isinstance(ext, dict) and isinstance(ext.get("preset"), str):
        box = dict(presets.get(ext["preset"]) or {}, **ext)
    elif isinstance(ext, dict):
        box = ext
    else:
        box = None
    if not box:
        return None
    try:
        w, e, s, n = (float(box[k]) for k in ("west", "east", "south", "north"))
    except (KeyError, TypeError, ValueError):
        return None
    proj = box.get("projection") or "equirectangular"
    if not (w < e and s < n) or w < -180 or e > 180 or s < -85 or n > 85 or proj not in ("equirectangular", "plate-carree", "mercator"):
        return None
    return {"west": w, "east": e, "south": s, "north": n, "projection": proj}


def para_id(owner, i, p):
    return p.get("id") or "%s-%d" % (owner, i + 1)


def all_paragraphs(story):
    """[(where, owner_id, index, paragraph)] for the prologue and every chapter."""
    out = []
    pro = story.get("prologue") or {}
    for i, p in enumerate(pro.get("paragraphs") or []):
        out.append(("prologue.paragraphs[%d]" % i, "start", i, p))
    for ci, c in enumerate(story.get("chapters") or []):
        for i, p in enumerate(c.get("paragraphs") or []):
            out.append(("chapters[%d].paragraphs[%d]" % (ci, i), c.get("id") or "chapter", i, p))
    return out


def quotes_of(c):
    q = c.get("quote")
    return [q] if isinstance(q, dict) else (q if isinstance(q, list) else [])


def tree_nodes(tree):
    return [n for r in (tree or {}).get("rows") or [] if isinstance(r, dict) and r.get("kind") != "gap" for n in (r.get("nodes") or []) if isinstance(n, dict)]


def prose_strings(story):
    """[(where, text)] of everything that is sentences: where a living person's name must not sit beside a date."""
    out = []
    for where, _, _, p in all_paragraphs(story):
        out.append((where + ".text", p.get("text")))
        if p.get("tbc"):
            out.append((where + ".tbc", p.get("tbc")))
    for ci, c in enumerate(story.get("chapters") or []):
        for qi, q in enumerate(quotes_of(c)):
            for k in ("title", "text", "source", "hardLimit"):
                out.append(("chapters[%d].quote[%d].%s" % (ci, qi, k), q.get(k)))
        out.append(("chapters[%d].hardLimit" % ci, c.get("hardLimit")))
        out.append(("chapters[%d].title" % ci, c.get("title")))
        if isinstance(c.get("tree"), dict):
            out.append(("chapters[%d].tree.note" % ci, c["tree"].get("note")))
    for i, x in enumerate(story.get("conflicts") or []):
        out.append(("conflicts[%d].note" % i, x.get("note")))
    cl = story.get("closing") or {}
    out.append(("closing.after.text", (cl.get("after") or {}).get("text")))
    for i, x in enumerate((cl.get("unknown") or {}).get("items") or []):
        out.append(("closing.unknown.items[%d].text" % i, x.get("text")))
    out.append(("closing.unknown.lead", (cl.get("unknown") or {}).get("lead")))
    for i, x in enumerate((cl.get("notes") or {}).get("items") or []):
        out.append(("closing.notes.items[%d]" % i, "%s %s" % (x.get("claim"), x.get("source"))))
    out.append(("ribbon.note", (story.get("ribbon") or {}).get("note")))
    for i, c in enumerate((story.get("ribbon") or {}).get("cards") or []):
        out.append(("ribbon.cards[%d].title" % i, c.get("title")))
    return [(w, plain(t)) for w, t in out if isinstance(t, str) and t.strip()]


def living_names(story, extra):
    names = set()
    for c in (story.get("chapters") or []):
        for n in tree_nodes(c.get("tree")):
            nm = str(n.get("name") or "").strip()
            if n.get("living") and nm and nm.lower() != "living" and not is_initial(nm) and len(nm) >= 3:
                names.add(nm)
    for c in (story.get("ribbon") or {}).get("cards") or []:
        if c.get("living") and c.get("name"):
            names.add(str(c["name"]))
        if (c.get("spouseLiving") if "spouseLiving" in c else c.get("living")) and c.get("spouse"):
            names.add(re.sub(r"\s+n[ée]e\b.*$", "", str(c["spouse"])).strip())
    names |= {str(x) for x in extra if len(str(x)) >= 3}
    out = set()
    for nm in names:
        out.add(nm)
        t = nm.split()
        if len(t) > 2:
            out.add(t[0] + " " + t[-1])
    return {x for x in out if len(x) >= 3}


# ---------------------------------------------------------------- the rules
def check(story, a):
    R = Report()
    presets = load_extents(a.extents)
    schema = json.load(open(os.path.join(KIT, "data", "story-schema.json"), encoding="utf-8"))
    for path, msg in schema_errors(story, schema, schema):
        R.err("S0", path or "(story)", msg)
    if not isinstance(story, dict):
        return R, None
    chapters = [c for c in story.get("chapters") or [] if isinstance(c, dict)]
    maps = [m for m in story.get("maps") or [] if isinstance(m, dict)]
    cids = [c.get("id") for c in chapters]
    cidset = set(cids)

    # S1 ids
    def dupes(seq):
        seen, d = set(), set()
        for x in seq:
            if x in seen:
                d.add(x)
            seen.add(x)
        return d
    for d in dupes(cids):
        R.err("S1", "chapters", "chapter id %r is used twice" % d)
    for d in dupes([m.get("id") for m in maps]):
        R.err("S1", "maps", "map id %r is used twice" % d)
    reserved = {"start", "after", "unknown", "papers", "world-notes"}
    for c in cids:
        if c in reserved:
            R.err("S1", "chapters", "chapter id %r is the id of a section the page draws itself" % c)
    pids = [para_id(o, i, p) for _, o, i, p in all_paragraphs(story) if isinstance(p, dict)]
    for d in dupes(pids):
        R.err("S1", "paragraphs", "paragraph id %r is used twice" % d)
    for i, c in enumerate((story.get("ribbon") or {}).get("cards") or []):
        if isinstance(c, dict) and c.get("chapter") not in cidset:
            R.err("S1", "ribbon.cards[%d]" % i, "links to chapter %r, which does not exist" % c.get("chapter"))
    for i, x in enumerate(story.get("conflicts") or []):
        if isinstance(x, dict) and x.get("chapter") not in cidset:
            R.err("S1", "conflicts[%d]" % i, "names chapter %r, which does not exist" % x.get("chapter"))

    # P paragraphs
    for where, owner, i, p in all_paragraphs(story):
        if not isinstance(p, dict):
            continue
        reg = p.get("register", "people")
        ev = [e for e in (p.get("evidence") or []) if isinstance(e, dict)]
        if reg == "world":
            if p.get("worldSource") not in ("archive", "history"):
                R.err("P2", where, "a paragraph about the world around the people has no source (worldSource archive or history)")
            if not any(e.get("href") for e in ev):
                R.err("P2", where, "a paragraph about the world has no link to where its detail comes from")
            for e in ev:
                if e.get("kind") not in (None, "archive", "history"):
                    R.err("P2", where, "evidence kind %r is neither archive nor history" % e.get("kind"))
        else:
            if p.get("grade") not in GRADES:
                R.err("P1", where, "a paragraph about the people has no grade (doc, inf or lore): %r" % p.get("grade"))
            if p.get("grade") == "doc" and not any(e.get("href") for e in ev):
                R.err("P3", where, "a documented paragraph links to no document")
            elif p.get("grade") in ("inf", "lore") and not any(e.get("href") for e in ev):
                R.warn("P3", where, "a %s paragraph links to nothing: a reader cannot see what it rests on" % p.get("grade"))
            if p.get("worldSource"):
                R.warn("P2", where, "worldSource on a paragraph about the people is ignored")

    # C chapters end with papers
    for ci, c in enumerate(chapters):
        papers = [x for x in c.get("papers") or [] if isinstance(x, dict) and x.get("href")]
        if not papers:
            R.err("C1", "chapters[%d] (%s)" % (ci, c.get("id")), "a chapter must end with at least one papers link")

    # R ribbon
    cards = [c for c in (story.get("ribbon") or {}).get("cards") or [] if isinstance(c, dict)]
    for i, c in enumerate(cards):
        w = "ribbon.cards[%d] (%s)" % (i, c.get("name"))
        miss = [f for f in CARD_FIELDS if f not in c]
        if miss:
            R.err("R1", w, "has no %s: every card carries every field (empty where it does not apply)" % ", ".join(miss))
        if c.get("living"):
            if c.get("years"):
                R.err("R2", w, "a living card carries years (%r)" % c.get("years"))
            if c.get("atYear"):
                R.err("R2", w, "a living card carries a year on its at-line (%r)" % c.get("atYear"))
            for k in ("name", "origin", "atPlace", "spouseOrigin", "title"):
                if has_date(c.get(k)):
                    R.err("R2", w, "a living card has a date in %s (%r)" % (k, c.get(k)))

    # T trees
    for ci, c in enumerate(chapters):
        tree = c.get("tree")
        if not isinstance(tree, dict):
            continue
        w0 = "chapters[%d] (%s).tree" % (ci, c.get("id"))
        ids = [n.get("id") for n in tree_nodes(tree) if n.get("id")]
        for d in dupes(ids):
            R.err("S1", w0, "node id %r is used twice" % d)
        for n in tree_nodes(tree):
            w = "%s node %r" % (w0, n.get("name"))
            if n.get("living"):
                if n.get("years"):
                    R.err("T1", w, "a living node carries years (%r)" % n.get("years"))
                if has_date(n.get("name")):
                    R.err("T1", w, "a living node has a date in its name")
            if n.get("minor"):
                if not n.get("living"):
                    R.err("T2", w, "a minor must be flagged living")
                if not is_initial(n.get("name")):
                    R.err("T2", w, "a minor is shown by initials only, not %r" % n.get("name"))
                if n.get("years"):
                    R.err("T2", w, "a minor carries years (%r)" % n.get("years"))
                if n.get("person") or n.get("href"):
                    R.err("T2", w, "a minor links to a page")
        th = tree.get("thread")
        if th:
            carriers = [n.get("id") for r in tree.get("rows") or [] if isinstance(r, dict) and r.get("kind") in ("children", "above") for n in (r.get("nodes") or []) if isinstance(n, dict)]
            if th not in carriers:
                R.err("T3", w0, "thread %r is not a child of the household or the person above it" % th)

    # M maps
    coords = {}
    for mi, m in enumerate(maps):
        w0 = "maps[%d] (%s)" % (mi, m.get("id"))
        if m.get("chapter") not in cidset:
            R.err("S1", w0, "is drawn under chapter %r, which does not exist" % m.get("chapter"))
        ext = resolve_extent(m.get("extent"), presets)
        if ext is None:
            R.err("M2", w0, "extent %r is neither a name in story-extents.json nor a box (west < east, south < north, inside the world)" % (m.get("extent"),))
        places = {}
        for pi, p in enumerate(m.get("places") or []):
            if not isinstance(p, dict):
                continue
            w = "%s.places[%d] (%s)" % (w0, pi, p.get("id"))
            if p.get("id") in places:
                R.err("S1", w, "place id %r is used twice on this map" % p.get("id"))
            places[p.get("id")] = p
            if p.get("chapter") not in cidset:
                R.err("S1", w, "links to chapter %r, which does not exist" % p.get("chapter"))
            lat, lon = p.get("lat"), p.get("lon")
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)) or isinstance(lat, bool) or isinstance(lon, bool):
                R.err("M1", w, "has no coordinates")
            elif ext and not (ext["west"] <= lon <= ext["east"] and ext["south"] <= lat <= ext["north"]):
                R.err("M1", w, "(%s, %s) is outside the map's extent (%s to %s east, %s to %s north)" % (lat, lon, ext["west"], ext["east"], ext["south"], ext["north"]))
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and p.get("id") is not None:
                prev = coords.get(p["id"])
                if prev and (abs(prev[0] - lat) > 0.02 or abs(prev[1] - lon) > 0.02):
                    R.err("M4", w, "place %r is at (%s, %s) here and (%s, %s) on another map" % (p["id"], lat, lon, prev[0], prev[1]))
                coords.setdefault(p["id"], (lat, lon))
            if p.get("living") and not p.get("country"):
                R.err("M5", w, "a place that stands for living people must be a country, not a town")
        for li, L in enumerate(m.get("legs") or []):
            if not isinstance(L, dict):
                continue
            w = "%s.legs[%d] (%s to %s)" % (w0, li, L.get("from"), L.get("to"))
            for end in ("from", "to"):
                if L.get(end) not in places:
                    R.err("M3", w, "%s %r is not a place on this map" % (end, L.get(end)))
            if L.get("grade") not in GRADES:
                R.err("M3", w, "grade %r is not doc, inf or lore" % L.get("grade"))
            if L.get("chapter") not in cidset:
                R.err("S1", w, "links to chapter %r, which does not exist" % L.get("chapter"))
            livingish = L.get("living") or any((places.get(L.get(e)) or {}).get("living") for e in ("from", "to"))
            if livingish and L.get("years"):
                R.err("M5", w, "a leg that touches the living carries years (%r)" % L.get("years"))

    # L living beside a date
    names = living_names(story, a.living_names)
    for w, t in prose_strings(story):
        for nm in sorted(names):
            for m in re.finditer(r"(?<![\w])%s(?![\w])" % re.escape(nm), t):
                lo, hi = max(0, m.start() - WINDOW), min(len(t), m.end() + WINDOW)
                near = t[lo:m.start()] + " " + t[m.end():hi]
                if has_date(near):
                    R.err("L1", w, "names %s, who is living, within %d characters of a date: %r" % (nm, WINDOW, near.strip()[:120]))
                    break
    return R, (presets, cids, pids)


# ---------------------------------------------------------------- links, in the built site
def check_links(story, a, R, site, ctx):
    presets, cids, pids = ctx
    story_path = a.page if a.page.endswith("/") else a.page + "/"
    story_html = site.page(story_path)
    if story_html is None:
        R.err("V1", "page", "no built story page at %s under %s" % (story_path, a.dist))
    data_ids = set(cids) | set(pids) | {"start", "after", "unknown", "papers", "world-notes"}
    cl = story.get("closing") or {}
    data_ids |= {"world-%s" % x.get("key") for x in (cl.get("notes") or {}).get("items") or [] if isinstance(x, dict)}
    data_ids |= {"map-%s" % m.get("id") for m in story.get("maps") or [] if isinstance(m, dict)}
    person_base = a.person_base if a.person_base.endswith("/") else a.person_base + "/"

    def person_ok(slug, where, code="H1"):
        if site.page(person_base + slug + "/") is None:
            R.err(code, where, "person %r has no built page at %s%s/" % (slug, person_base, slug))

    def link_ok(href, where):
        if not isinstance(href, str) or not href:
            return
        if re.match(r"^(?:https?:|mailto:|rec:|tel:)", href):
            return
        if href.startswith("person:"):
            return person_ok(href[7:], where)
        if href.startswith("#"):
            frag = href[1:]
            if frag not in data_ids and not (story_html and re.search(r"""\bid\s*=\s*["']%s["']""" % re.escape(frag), story_html)):
                R.err("H2", where, "%s is not an id on the story page" % href)
            return
        path, _, frag = href.partition("#")
        if a.base and path.startswith(a.base):
            path = path[len(a.base):] or "/"
        if path.rstrip("/") == story_path.rstrip("/") and frag:
            return link_ok("#" + frag, where)
        if site.page(path) is None:
            R.err("H2", where, "%s is not a built page" % href)
        elif frag and not site.has_id(path, frag):
            R.err("H2", where, "%s: the page has no id %r" % (href, frag))

    for where, _, _, p in all_paragraphs(story):
        if not isinstance(p, dict):
            continue
        for m in LINK_RE.finditer(str(p.get("text") or "")):
            link_ok(m.group(2), where + ".text link")
        for ei, e in enumerate(p.get("evidence") or []):
            link_ok((e or {}).get("href"), "%s.evidence[%d]" % (where, ei))
    for ci, c in enumerate(story.get("chapters") or []):
        for pi, x in enumerate(c.get("papers") or []):
            if isinstance(x, dict):
                href = x.get("href", "")
                if isinstance(href, str) and href.startswith("person:"):
                    person_ok(href[7:], "chapters[%d].papers[%d]" % (ci, pi), "C2")
                elif isinstance(href, str) and not href.startswith("#") and not re.match(r"^(?:https?:|mailto:)", href):
                    path, _, frag = href.partition("#")
                    if site.page(path) is None or (frag and not site.has_id(path, frag)):
                        R.err("C2", "chapters[%d].papers[%d]" % (ci, pi), "%s does not resolve in the built site" % href)
                else:
                    link_ok(href, "chapters[%d].papers[%d]" % (ci, pi))
        for n in tree_nodes(c.get("tree")):
            if n.get("person"):
                person_ok(n["person"], "chapters[%d].tree node %r" % (ci, n.get("name")))
            if n.get("href"):
                link_ok(n["href"], "chapters[%d].tree node %r" % (ci, n.get("name")))
    for i, c in enumerate((story.get("ribbon") or {}).get("cards") or []):
        for k in ("person", "spousePerson"):
            if isinstance(c, dict) and c.get(k):
                person_ok(c[k], "ribbon.cards[%d].%s" % (i, k))
        if isinstance(c, dict) and c.get("spouseHref"):
            link_ok(c["spouseHref"], "ribbon.cards[%d].spouseHref" % i)
    for mi, m in enumerate(story.get("maps") or []):
        for li, L in enumerate((m or {}).get("legs") or []):
            if isinstance(L, dict) and L.get("evidence"):
                link_ok(L["evidence"], "maps[%d].legs[%d].evidence" % (mi, li))
    for k in ("after", "papers"):
        for li, x in enumerate((cl.get(k) or {}).get("links") or []):
            link_ok(x.get("href"), "closing.%s.links[%d]" % (k, li))
    for ii, x in enumerate((cl.get("unknown") or {}).get("items") or []):
        link_ok(x.get("href"), "closing.unknown.items[%d]" % ii)
    for m in LINK_RE.finditer(str((cl.get("after") or {}).get("text") or "")):
        link_ok(m.group(2), "closing.after.text link")
    for ii, x in enumerate((cl.get("unknown") or {}).get("items") or []):
        for m in LINK_RE.finditer(str(x.get("text") or "")):
            link_ok(m.group(2), "closing.unknown.items[%d].text link" % ii)
    return story_html


# ---------------------------------------------------------------- the built page, read back
def check_built(story, a, R, html):
    d = Doc(html)
    chapters = [c for c in story.get("chapters") or [] if isinstance(c, dict)]

    # V1 chapters in order
    secs = [n.attrs.get("data-chapter") for n in d.find(lambda n: n.tag == "section" and "data-chapter" in n.attrs)]
    want = [c.get("id") for c in chapters]
    if secs != want:
        R.err("V1", "page", "the built chapters are %s, the data has %s" % (secs, want))

    # V2 paragraphs
    byid = {n.attrs["id"]: n for n in d.find(lambda n: "data-register" in n.attrs and n.attrs.get("id"))}
    for where, owner, i, p in all_paragraphs(story):
        if not isinstance(p, dict):
            continue
        pid = para_id(owner, i, p)
        n = byid.get(pid)
        if n is None:
            R.err("V2", where, "paragraph %r is not on the built page" % pid)
            continue
        reg = p.get("register", "people")
        if n.attrs.get("data-register") != reg:
            R.err("V2", where, "paragraph %r is built as %s, the data says %s" % (pid, n.attrs.get("data-register"), reg))
        elif reg == "people" and n.attrs.get("data-grade") != p.get("grade"):
            R.err("V2", where, "paragraph %r is built with grade %s, the data says %s" % (pid, n.attrs.get("data-grade"), p.get("grade")))
        elif reg == "world" and n.attrs.get("data-source") != p.get("worldSource"):
            R.err("V2", where, "paragraph %r is built with source %s, the data says %s" % (pid, n.attrs.get("data-source"), p.get("worldSource")))

    # V3 ribbon
    cards = [c for c in (story.get("ribbon") or {}).get("cards") or [] if isinstance(c, dict)]
    lis = d.find(lambda n: n.tag == "li" and "data-ch" in n.attrs)
    if len(lis) != len(cards):
        R.err("V3", "page", "the built ribbon has %d card(s), the data has %d" % (len(lis), len(cards)))
    parts = [{c for k in li.kids for c in k.cls() if c.startswith("st-rb-") and c not in ("st-rb-note",)} for li in lis]
    core = {"st-rb-top", "st-rb-n", "st-rb-f", "st-rb-s"}
    for i, ps in enumerate(parts):
        if not core <= ps:
            R.err("V3", "built ribbon card %d" % (i + 1), "is missing %s: every card has the same parts" % ", ".join(sorted(core - ps)))
    for i, li in enumerate(lis):
        if li.attrs.get("data-living") == "1":
            t = li.all_text()
            if has_date(t):
                R.err("V3", "built ribbon card %d" % (i + 1), "is living and shows a date: %r" % re.sub(r"\s+", " ", t).strip()[:100])

    # V4 trees
    for n in d.find(lambda n: n.tag == "a" and n.attrs.get("data-node") == "living"):
        t = n.all_text()
        if has_date(t):
            R.err("V4", "built tree", "a living node shows a date: %r" % re.sub(r"\s+", " ", t).strip()[:100])

    # V5 maps
    for svg in d.find(lambda n: n.tag == "svg" and "data-w" in n.attrs):
        w, h = float(svg.attrs["data-w"]), float(svg.attrs["data-h"])
        for dot in [k for k in svg.walk() if k.tag == "a" and "data-place" in k.attrs]:
            x, y = float(dot.attrs["data-x"]), float(dot.attrs["data-y"])
            if not (0 <= x <= w and 0 <= y <= h):
                R.err("V5", "built map", "place %r is drawn at (%s, %s), outside the %sx%s picture" % (dot.attrs["data-place"], x, y, w, h))

    # V6 counts
    nt = len(d.find(lambda n: n.tag == "figure" and "st-tree" in n.cls()))
    nm = len(d.find(lambda n: n.tag == "figure" and "st-map" in n.cls()))
    wt = sum(1 for c in chapters if isinstance(c.get("tree"), dict))
    wm = len([m for m in story.get("maps") or [] if isinstance(m, dict)])
    if nt != wt:
        R.err("V6", "page", "the built page has %d tree(s), the data has %d" % (nt, wt))
    if nm != wm:
        R.err("V6", "page", "the built page has %d map(s), the data has %d" % (nm, wm))


# ---------------------------------------------------------------- main
def run(a):
    try:
        story = json.load(open(a.story, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("checkfamilystory: cannot read %s: %s" % (a.story, e), file=sys.stderr)
        return 2
    extra = []
    if a.living:
        try:
            raw = json.load(open(a.living, encoding="utf-8"))
            extra = raw.get("names", []) if isinstance(raw, dict) else raw
        except (OSError, ValueError) as e:
            print("checkfamilystory: cannot read %s: %s" % (a.living, e), file=sys.stderr)
            return 2
    a.living_names = extra
    R, ctx = check(story, a)
    looked = "the data only"
    if ctx and a.dist and not a.no_dist:
        if not os.path.isdir(a.dist):
            print("checkfamilystory: no such dist %s" % a.dist, file=sys.stderr)
            return 2
        site = Site(a.dist)
        html = check_links(story, a, R, site, ctx)
        if html is not None:
            check_built(story, a, R, html)
        looked = "the data, its links and the built page"
    elif not a.no_dist:
        print("checkfamilystory: pass --dist (or --no-dist, which says plainly that the site was not looked at)", file=sys.stderr)
        return 2
    for code, where, msg in R.errors:
        print("FAIL [%s] %s: %s" % (code, where, msg))
    for code, where, msg in R.warnings:
        print("warn [%s] %s: %s" % (code, where, msg))
    n_ch = len(story.get("chapters") or []) if isinstance(story, dict) else 0
    print("checkfamilystory: %d error(s), %d warning(s) (%d chapters; looked at %s)" % (len(R.errors), len(R.warnings), n_ch, looked))
    if a.no_dist:
        print("checkfamilystory: --no-dist: person links, internal links and the built page were NOT checked")
    return 1 if R.errors or (a.strict and R.warnings) else 0


# ---------------------------------------------------------------- the selftest
def _built_page(story):
    """A built story page of the shape components/StoryBook.astro makes, by hand: the gate's V rules read this."""
    out = ['<html><body><div class="story"><nav class="st-rib"><ol>']
    for c in story["ribbon"]["cards"]:
        out.append('<li data-ch="%s" data-living="%d" class="st-rb"><a class="st-rb-top" href="#%s">Gen.</a><span class="st-rb-n">%s</span>'
                   '%s<span class="st-rb-f">from %s</span><span class="st-rb-s">m. %s</span></li>' % (
                       c.get("chapter"), 1 if c.get("living") else 0, c.get("chapter"), c.get("name"), ("<span class=\"st-rb-y\">%s</span>" % c["years"]) if c.get("years") else "",
                       c.get("origin"), c.get("spouse")))
    out.append("</ol></nav>")
    for i, p in enumerate(story["prologue"]["paragraphs"]):
        out.append('<p id="%s" data-register="people" data-grade="%s">x</p>' % (para_id("start", i, p), p.get("grade")))
    for c in story["chapters"]:
        out.append('<section data-chapter="%s" id="%s">' % (c["id"], c["id"]))
        for i, p in enumerate(c["paragraphs"]):
            if p.get("register") == "world":
                out.append('<div id="%s" data-register="world" data-source="%s"><p>x</p></div>' % (para_id(c["id"], i, p), p.get("worldSource")))
            else:
                out.append('<p id="%s" data-register="people" data-grade="%s">x</p>' % (para_id(c["id"], i, p), p.get("grade")))
        if c.get("tree"):
            out.append('<figure class="st-tree"><svg>')
            for n in tree_nodes(c["tree"]):
                if n.get("living"):
                    out.append('<a data-node="living" aria-label="%s: a living person, with no dates"><text>%s</text></a>' % (n["name"], n["name"]))
                else:
                    out.append('<a data-node="%s"><text>%s %s</text></a>' % (n.get("grade"), n.get("name"), n.get("years", "")))
            out.append("</svg></figure>")
        out.append("</section>")
    for m in story.get("maps") or []:
        out.append('<figure class="st-map"><svg data-w="640" data-h="300"><a data-place="%s" data-x="100" data-y="100"></a></svg></figure>' % m["places"][0]["id"])
    for pid in ("unknown", "papers", "world-H1", "map-valmora"):
        out.append('<h2 id="%s">x</h2>' % pid)
    out.append("</div></body></html>")
    return "".join(out)


def _site(root, story):
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    for slug in ("tomas-arden-1790", "ilse-arden-nee-brandt-1795", "pieter-arden-1822"):
        os.makedirs(os.path.join(root, "people", slug))
        open(os.path.join(root, "people", slug, "index.html"), "w").write("<h1>%s</h1>" % slug)
    for path, ids in (("valmora-line", ["baptism1790", "census1851"]), ("direct-line", ["loom"]), ("port-alder", [])):
        os.makedirs(os.path.join(root, path))
        open(os.path.join(root, path, "index.html"), "w").write("".join('<h2 id="%s">x</h2>' % i for i in ids) or "<h1>x</h1>")
    os.makedirs(os.path.join(root, "story"))
    open(os.path.join(root, "story", "index.html"), "w").write(_built_page(story))


def selftest():
    base = json.load(open(os.path.join(KIT, "data", "story-example.json"), encoding="utf-8"))
    res = []

    def ok(label, cond, detail=""):
        res.append(bool(cond))
        print("  %s  %s%s" % ("ok  " if cond else "FAIL", label, ("  [%s]" % detail[:400]) if detail and not cond else ""))

    cases = json.load(open(os.path.join(KIT, "data", "story-cases.json"), encoding="utf-8"))
    presets = load_extents()
    print("the shared cases (kit/tools/story_logic.mjs answers the same file)")
    bad = [c["text"] for c in cases["dates"] if has_date(c["text"]) != c["date"]]
    ok("what is a date: %d cases" % len(cases["dates"]), not bad, "wrong for %r" % bad)
    bad = [c["name"] for c in cases["initials"] if is_initial(c["name"]) != c["initial"]]
    ok("what is an initial: %d cases" % len(cases["initials"]), not bad, "wrong for %r" % bad)
    bad = [c["extent"] for c in cases["extents"] if (resolve_extent(c["extent"], presets) is not None) != c["ok"]]
    ok("what is an extent: %d cases" % len(cases["extents"]), not bad, "wrong for %r" % bad)
    bad = []
    for c in cases["inside"]:
        r = resolve_extent(c["extent"], presets)
        if (bool(r) and r["west"] <= c["lon"] <= r["east"] and r["south"] <= c["lat"] <= r["north"]) != c["in"]:
            bad.append(c)
    ok("what is inside an extent: %d cases" % len(cases["inside"]), not bad, "wrong for %r" % bad)
    tmp = tempfile.mkdtemp(prefix="checkfamilystory-")
    try:
        dist = os.path.join(tmp, "dist")
        os.makedirs(dist)
        _site(dist, base)

        def gate(story, extra=None, living=None, rebuild=True, args=None):
            f = os.path.join(tmp, "story.json")
            json.dump(story, open(f, "w", encoding="utf-8"), ensure_ascii=False)
            if rebuild:
                shutil.rmtree(dist)
                os.makedirs(dist)
                try:
                    _site(dist, story)
                except Exception:
                    _site(dist, base)
            cmd = [sys.executable, os.path.abspath(__file__), "--story", f] + (args if args is not None else ["--dist", dist])
            if living is not None:
                lf = os.path.join(tmp, "living.json")
                json.dump(living, open(lf, "w"))
                cmd += ["--living", lf]
            p = subprocess.run(cmd + (extra or []), capture_output=True, text=True)
            return p.returncode, p.stdout + p.stderr

        print("controls")
        rc, out = gate(base)
        ok("the example story passes, data, links and built page", rc == 0 and "0 error(s)" in out, out)
        rc, out = gate(base, args=["--no-dist"])
        ok("--no-dist passes and says it did not look", rc == 0 and "NOT checked" in out, out)
        rc, out = gate(base, args=[])
        ok("neither --dist nor --no-dist is a usage error", rc == 2, out)
        rc, out = gate(base, extra=["--strict"])
        ok("--strict: the example has no warnings", rc == 0, out)

        print("planted faults: each must fail with its own code")

        def plant(label, code, fn, warn=False, living=None, built=None, dist_after=None):
            s = copy.deepcopy(base)
            fn(s)
            rc, out = gate(s, living=living)
            want = ("warn [%s]" % code) if warn else ("FAIL [%s]" % code)
            ok(label, want in out and (rc == 0 if warn else rc == 1), "rc=%s %s" % (rc, out[-500:]))

        ch = lambda s, i: s["chapters"][i]
        # schema
        plant("a chapter with no title", "S0", lambda s: ch(s, 0).pop("title"))
        plant("a field the contract does not know", "S0", lambda s: ch(s, 0).update(colour="red"))
        plant("a grade that is not doc, inf or lore", "S0", lambda s: ch(s, 0)["paragraphs"][0].update(grade="proven"))
        plant("a thread that is not an id", "S0", lambda s: ch(s, 0)["tree"].update(thread=5))
        # ids and references
        plant("two chapters with one id", "S1", lambda s: ch(s, 1).update(id="weaver"))
        plant("two paragraphs with one id", "S1", lambda s: ch(s, 0)["paragraphs"][1].update(id="w-1"))
        plant("a chapter named like a section the page draws", "S1", lambda s: ch(s, 2).update(id="unknown"))
        plant("a ribbon card that links to no chapter", "S1", lambda s: s["ribbon"]["cards"][0].update(chapter="nowhere"))
        plant("a conflict on no chapter", "S1", lambda s: s["conflicts"][0].update(chapter="nowhere"))
        plant("two nodes with one id in a tree", "S1", lambda s: ch(s, 0)["tree"]["rows"][1]["nodes"][0].update(id="tomas"))
        # paragraphs
        plant("a people paragraph with no grade", "P1", lambda s: ch(s, 0)["paragraphs"][0].pop("grade"))
        plant("a world paragraph with no source", "P2", lambda s: ch(s, 0)["paragraphs"][1].pop("worldSource"))
        plant("a world paragraph with no link to its source", "P2", lambda s: ch(s, 0)["paragraphs"][1].update(evidence=[{"why": "x"}]))
        plant("a documented paragraph that links to no document", "P3", lambda s: ch(s, 0)["paragraphs"][0].update(evidence=[]))
        plant("a family-lore paragraph that links to nothing", "P3", lambda s: ch(s, 0)["paragraphs"][2].update(evidence=[]), warn=True)
        # chapters
        plant("a chapter with no papers", "C1", lambda s: ch(s, 0).update(papers=[]))
        plant("a papers link to a page that does not exist", "C2", lambda s: ch(s, 0)["papers"].append({"title": "Gone", "href": "/gone/"}))
        plant("a papers link to a person with no page", "C2", lambda s: ch(s, 0)["papers"].append({"title": "Gone", "href": "person:nobody"}))
        # ribbon
        plant("a ribbon card with a field missing", "R1", lambda s: s["ribbon"]["cards"][1].pop("atYear"))
        plant("a living card with years", "R2", lambda s: s["ribbon"]["cards"][2].update(years="1980–"))
        plant("a living card with a year on its at-line", "R2", lambda s: s["ribbon"]["cards"][2].update(atYear="2005"))
        plant("a living card with a date in its origin", "R2", lambda s: s["ribbon"]["cards"][2].update(origin="Port Alder since 1999"))
        # trees
        plant("a living node with years", "T1", lambda s: ch(s, 2)["tree"]["rows"][0]["nodes"][0].update(years="b. 1980"))
        plant("a living node with a year in its name", "T1", lambda s: ch(s, 2)["tree"]["rows"][0]["nodes"][1].update(name="Mira (1981)"))
        plant("a minor with a full name", "T2", lambda s: ch(s, 2)["tree"]["rows"][1]["nodes"][0].update(name="Kira Arden"))
        plant("a minor with years", "T2", lambda s: ch(s, 2)["tree"]["rows"][1]["nodes"][0].update(years="2015"))
        plant("a minor not flagged living", "T2", lambda s: ch(s, 2)["tree"]["rows"][1]["nodes"][0].update(living=False, grade="doc"))
        plant("a minor with a person page", "T2", lambda s: ch(s, 2)["tree"]["rows"][1]["nodes"][0].update(person="pieter-arden-1822"))
        plant("a thread to a node that is not a child", "T3", lambda s: ch(s, 0)["tree"].update(thread="tomas"))
        plant("a node person with no built page", "H1", lambda s: ch(s, 0)["tree"]["rows"][0]["nodes"][0].update(person="ghost-person"))
        plant("a ribbon person with no built page", "H1", lambda s: s["ribbon"]["cards"][0].update(person="ghost-person"))
        plant("a person: link in prose with no built page", "H1", lambda s: ch(s, 0)["paragraphs"][0].update(text="See [him](person:ghost-person)."))
        # maps
        plant("a place outside its map", "M1", lambda s: s["maps"][0]["places"][0].update(lat=10.0, lon=100.0))
        plant("a place with no coordinates", "M1", lambda s: s["maps"][0]["places"][1].pop("lat"))
        plant("an extent that is no name and no box", "M2", lambda s: s["maps"][0].update(extent="atlantis"))
        plant("a box that runs backwards", "M2", lambda s: s["maps"][0].update(extent={"west": 11, "east": 5, "south": 44, "north": 47}))
        plant("a leg to a place that is not on the map", "M3", lambda s: s["maps"][0]["legs"][1].update(to="nowhere"))
        plant("a leg with a grade that is not a grade", "M3", lambda s: s["maps"][0]["legs"][1].update(grade="sure"))
        plant("one place at two sets of coordinates", "M4", lambda s: s["maps"][1]["places"][0].update(lat=44.9, lon=9.5))
        plant("a living place that is a town", "M5", lambda s: s["maps"][1]["places"][1].update(country=False))
        plant("a leg to the living with years", "M5", lambda s: s["maps"][1]["legs"][0].update(years="1999"))
        # living beside a date
        plant("a paragraph naming a living person beside a year", "L1", lambda s: ch(s, 2)["paragraphs"].append(
            {"id": "h-2", "grade": "doc", "text": "Rowan was married to Mira at Port Alder in 2009.", "evidence": [{"href": "/direct-line/"}]}))
        plant("a quote naming a living person beside a date", "L1", lambda s: ch(s, 2).update(quote={"text": "Mira Arden, 4 May, signed.", "source": "x"}))
        plant("a person on the archive's living list beside a year", "L1", lambda s: ch(s, 1)["paragraphs"].append(
            {"id": "s-3", "grade": "doc", "text": "Hanna Voss sold the yard in 1999.", "evidence": [{"href": "/direct-line/"}]}), living=["Hanna Voss"])
        # links
        plant("a prose link to a page that is not built", "H2", lambda s: ch(s, 0)["paragraphs"][0].update(text="See [that](/missing/)."))
        plant("a prose link to an id the page does not have", "H2", lambda s: ch(s, 0)["paragraphs"][0].update(text="See [that](/valmora-line/#nope)."))
        plant("an evidence link to an anchor on the story page that is not there", "H2", lambda s: ch(s, 0)["paragraphs"][1]["evidence"][0].update(href="#world-H9"))
        plant("a leg's evidence to a page that is not built", "H2", lambda s: s["maps"][0]["legs"][1].update(evidence="/gone/"))
        # the built page
        def built_fault(label, code, mutate):
            s = copy.deepcopy(base)
            f = os.path.join(tmp, "story.json")
            json.dump(s, open(f, "w", encoding="utf-8"), ensure_ascii=False)
            shutil.rmtree(dist)
            os.makedirs(dist)
            _site(dist, s)
            pf = os.path.join(dist, "story", "index.html")
            h = open(pf).read()
            open(pf, "w").write(mutate(h))
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "--story", f, "--dist", dist], capture_output=True, text=True)
            out = p.stdout + p.stderr
            ok(label, ("FAIL [%s]" % code) in out and p.returncode == 1, "rc=%s %s" % (p.returncode, out[-400:]))

        built_fault("a built page that lacks a chapter", "V1", lambda h: re.sub(r'<section data-chapter="ship".*?</section>', "", h, flags=re.S))
        built_fault("a built paragraph with another grade than the data's", "V2", lambda h: h.replace('id="w-1" data-register="people" data-grade="doc"', 'id="w-1" data-register="people" data-grade="lore"'))
        built_fault("a built paragraph that is missing", "V2", lambda h: h.replace('id="w-3"', 'id="w-33"'))
        built_fault("a built world paragraph with another source", "V2", lambda h: h.replace('data-source="history"', 'data-source="archive"'))
        built_fault("a built ribbon card missing a part", "V3", lambda h: h.replace('<span class="st-rb-f">from Valmora</span>', "", 1))
        built_fault("a built living card that shows a date", "V3", lambda h: h.replace('<span class="st-rb-n">Rowan Arden</span>', '<span class="st-rb-n">Rowan Arden</span><span class="st-rb-y">b. 1980</span>'))
        built_fault("a built living node that shows a date", "V4", lambda h: h.replace("<text>Mira</text>", "<text>Mira 1981</text>"))
        built_fault("a built map dot outside its picture", "V5", lambda h: h.replace('data-x="100" data-y="100"', 'data-x="900" data-y="100"'))
        built_fault("a built page with a tree fewer", "V6", lambda h: h.replace('<figure class="st-tree">', '<figure class="x">', 1))
        # the missing page is a different shape: remove the file
        s = copy.deepcopy(base)
        gate(s)
        os.remove(os.path.join(dist, "story", "index.html"))
        f = os.path.join(tmp, "story.json")
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--story", f, "--dist", dist], capture_output=True, text=True)
        ok("no built story page at all", "FAIL [V1]" in (p.stdout + p.stderr) and p.returncode == 1, p.stdout[-300:])

        print("the rules must not be too eager")
        s = copy.deepcopy(base)
        s["chapters"][2]["paragraphs"].append({"id": "h-2", "grade": "doc", "text": "Mira and Rowan live at Port Alder, as the archive publishes them.", "evidence": [{"href": "/direct-line/"}]})
        rc, out = gate(s)
        ok("a living name with no date beside it passes", rc == 0, out)
        s = copy.deepcopy(base)
        s["chapters"][0]["paragraphs"][0]["text"] += " The weaver Tomas Arden was baptised in 1790." + " The harbour and its yards went on without him." * 6 + " His great-grandson Rowan came a long time after."
        rc, out = gate(s)
        ok("a dead man's date a long way from a living name passes", rc == 0, out)
        s = copy.deepcopy(base)
        s["ribbon"]["cards"][1]["years"] = "†"
        rc, out = gate(s)
        ok("a dead card's dagger passes", rc == 0, out)
        s = copy.deepcopy(base)
        s["maps"][0]["extent"] = {"preset": "europe"}
        rc, out = gate(s)
        ok("a preset spelled as {preset} is read", rc == 0, out)
        s["maps"][0]["extent"] = {"preset": "british-isles"}
        rc, out = gate(s)
        ok("...and a place outside that preset fails", rc == 1 and "M1" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = len(res) - sum(res)
    print("\ncheckfamilystory selftest: %d/%d ok%s" % (sum(res), len(res), "" if not bad else ", %d FAILED" % bad))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--story")
    ap.add_argument("--dist")
    ap.add_argument("--no-dist", action="store_true")
    ap.add_argument("--page", default="/story/")
    ap.add_argument("--base", default="")
    ap.add_argument("--person-base", default="/people/")
    ap.add_argument("--living")
    ap.add_argument("--extents")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.story:
        ap.error("--story is required")
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
