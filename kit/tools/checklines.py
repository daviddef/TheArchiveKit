#!/usr/bin/env python3
"""The gate on a lines file: the data behind the rivers drawing (components/BranchRivers.astro), held to its own claims.

WHY. The drawing is the one place an archive says, for every family of a surname, how far back its evidence reaches
and who is NOT on it. Eight archives were audited on 18 October 2026 and the same gaps recurred: no status per lane,
pens that were uncounted, empty or unlinked, lane nodes that linked to the top of a page rather than to a person,
counts typed into a title and left to go stale, and links that no gate followed (Defranceschi's third bridge pointed
at a page that never existed, and the kit's link check only reads <a href>, never a data-href). Nothing checked the
lines data at all. This does. The contract is kit/docs/lines.md; the words are made in kit/lib/lines.js.

    python3 checklines.py --lines src/data/lines.json --dist dist [--config standard.json] [--living living.json]
    python3 checklines.py --selftest              plant every fault in a fixture, one at a time, and require it be caught

--lines   a rivers object ({lanes, pens|unplaced|loose, bridges, title, caption}), a {sets: [rivers, ...]} file
          (Luwinski, Blazevic) or a list of rivers objects. Each rivers object is one drawing.
--dist    the built site. Every `person`, every member and every internal href is resolved to a built page, and a
          #fragment to an id in it. Pass --no-dist to skip that (the gate then says it did not look).
--config  a JSON file whose "lines" key holds the settings (the same file the linking standard reads is fine):
            exclusive       true: a person appears on exactly one lane or one pen of a drawing (default true)
            sharedAllowed   slugs that may stand on two (a spouse at the join of two lines), each a stated exception
            personBase      where a bare slug is built (default /people/)
            requireStatus   every lane carries a status (default true; --allow-legacy makes a missing one a warning)
            maxStatusLine   the longest status line the drawing can print (default 100 characters)
            titleNumbers    numbers in the chart's own title are held to the data (default true)
--living  a JSON list of slugs (or {"slugs": [...]}) that must never be listed as a member of a pen or lane.

Rules (the code is printed with every finding):
  S1  the drawing has lanes; keys are unique; every lane has a label, a colour, and an href with its read text
  S2  every lane has a status: documented | inferred | origin-unknown | family-lore
  S3  the status is coherent: a family-lore lane has no span; a span runs first to last; the printed status line fits;
      an inferred lane says to what; the old `conf` beside a status is ignored (warned)
  S4  a node's year outside the lane's span is a stale span (warned)
  P1  every person, member and pen item person resolves to a built page
  P2  no member is listed twice in one pen or lane
  P3  nobody on the living list is a member
  E1  every person on a lane or in a pen appears on exactly one lane or pen of the drawing (exclusive)
  K1  a pen has a known kind and holds something: a heading over nothing is a claim nobody made
  K2  a pen's count equals its members; K3 a count with no members cannot be checked (warned)
  K4  a pen with households has a note saying why it is a pen (warned)
  T1  a number in the chart's own title equals a count the data can state (lanes, households, kept apart, bridges)
  T2  the same, for numbers beside a noun in the caption (warned)
  B1  a bridge names a lane or an unplaced household that exists
  H1  an internal href resolves to a built page;  H2  a #fragment names an id that is in it
  N1  a node's evidence is one of the person page's source words
Exit 0 clean (warnings do not fail), 1 on any error, 2 on a file that cannot be read or when nothing was checked.
"""
import argparse, copy, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
STATUSES = ["documented", "inferred", "origin-unknown", "family-lore"]
PEN_KINDS = ["not-yet-placed", "different-stock"]
EVIDENCE = {"read", "indexed", "scanned", "tree", "inferred", "disputed", "none", "register", "record", "doc",
            "documented", "index", "image", "scanned, not read", "family tree", "tree only", "lore", "testimony", "told",
            "family", "inf", "probable", "dis", "disp", "contested", "open", "line", "direct line"}
WORDS = {w: i + 1 for i, w in enumerate("one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                         "fifteen sixteen seventeen eighteen nineteen twenty".split())}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60}


# ---------------------------------------------------------------- the words (mirrors kit/lib/lines.js)
def plain(x):
    s = str(x if x is not None else "")
    s = re.sub(r"\[([^\]\n]{1,120})\]\((?:/|https?://)[^)\s]{1,200}\)", r"\1", s)
    s = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", s, flags=re.S)
    s = re.sub(r"«(.+?)»", r"\1", s, flags=re.S)
    s = s.replace("`", "")
    return re.sub(r"\s+", " ", s).strip()


def year(v):
    m = re.fullmatch(r"\s*(\d{3,4})\s*", str(v)) if v not in (None, "") else None
    return int(m.group(1)) if m else None


def span_text(span):
    if not isinstance(span, list):
        return ""
    a, b = year(span[0] if len(span) > 0 else None), year(span[1] if len(span) > 1 else None)
    if a and b:
        return str(a) if a == b else "%d–%d" % (a, b)
    if a:
        return "from %d" % a
    if b:
        return "to %d" % b
    return ""


def status_line(lane):
    tier = lane.get("status") if lane.get("status") in STATUSES else None
    if not tier:
        return None, str(lane.get("conf") or "")
    sp = span_text(lane.get("span"))
    note = plain(lane.get("statusNote") or "")
    lead = "Family lore" if tier == "family-lore" else ("Documented " + sp if sp else "")
    dflt = {"documented": "", "inferred": "origin inferred", "origin-unknown": "origin not found", "family-lore": "not documented"}[tier]
    tail = note or dflt
    text = (lead + " · " + tail) if (lead and tail) else (lead or tail or "Documented")
    return tier, text


def norm_item(it):
    if isinstance(it, list):
        return {"name": str(it[0]) if it else "", "href": it[1] if len(it) > 1 else "", "why": it[2] if len(it) > 2 else "",
                "person": None, "evidence": None, "year": ""}
    o = it or {}
    return {"name": str(o.get("place") or o.get("name") or ""), "href": o.get("href") or "", "why": o.get("why") or "",
            "person": o.get("person"), "evidence": o.get("evidence"), "year": o.get("year", "")}


def norm_node(n):
    if isinstance(n, list):
        return {"place": str(n[0]) if n else "", "year": n[1] if len(n) > 1 else "", "why": n[2] if len(n) > 2 else "",
                "person": None, "evidence": None, "href": ""}
    o = n or {}
    return {"place": str(o.get("place") or o.get("name") or ""), "year": o.get("year", ""), "why": o.get("why") or "",
            "person": o.get("person"), "evidence": o.get("evidence"), "href": o.get("href") or ""}


def member_slug(m):
    return str(m.get("person") or m.get("slug") or "") if isinstance(m, dict) else str(m or "")


def pens_of(r):
    """Mirror of pensOf(): `pens` wins when it is a list, else the two legacy lists. Returns pens that were DECLARED, kept
    even when empty, so an empty pen heading can be told from an absent pen."""
    if isinstance(r.get("pens"), list):
        raw = r["pens"]
    else:
        raw = []
        if r.get("unplaced") or r.get("unplacedHead"):
            raw.append({"id": "unplaced", "kind": "not-yet-placed", "head": r.get("unplacedHead"), "note": r.get("unplacedNote"),
                        "items": r.get("unplaced") or [], "_legacy": True})
        if r.get("loose") or r.get("looseHead"):
            raw.append({"id": "loose", "kind": "different-stock", "head": r.get("looseHead"), "note": r.get("looseNote"),
                        "items": r.get("loose") or [], "_legacy": True})
    return raw


def counts(r):
    lanes = r.get("lanes") or []
    pens = [p for p in pens_of(r) if (p.get("items") or p.get("members"))]
    hh = sum(len(p.get("items") or []) for p in pens if p.get("kind", "not-yet-placed") == "not-yet-placed")
    other = sum(len(p.get("items") or []) for p in pens if p.get("kind") == "different-stock")
    people = set()
    for l in lanes:
        for n in l.get("nodes") or []:
            s = norm_node(n)["person"]
            if s:
                people.add(str(s))
        for m in l.get("members") or []:
            people.add(member_slug(m))
    pen_people = sum(len(p.get("members") or []) if p.get("members") else (p.get("count") or 0) for p in pens)
    return {"lanes": len(lanes), "households": hh, "other": other, "bridges": len(r.get("bridges") or []),
            "pens": len(pens), "people_lanes": len(people), "people_pens": pen_people}


def number_tokens(text):
    """[(value, word)] for number words and digit runs under 1000 (years are not counts). `one` is skipped: «one surname»."""
    out = []
    toks = re.findall(r"[A-Za-zÀ-ɏ]+|\d+", text)
    for i, t in enumerate(toks):
        lt = t.lower()
        if t.isdigit():
            if int(t) < 1000:
                out.append((int(t), t))
        elif lt in TENS and i + 1 < len(toks) and toks[i + 1].lower() in WORDS and WORDS[toks[i + 1].lower()] < 10:
            out.append((TENS[lt] + WORDS[toks[i + 1].lower()], lt + " " + toks[i + 1].lower()))
        elif lt in WORDS and lt != "one":
            if i > 0 and toks[i - 1].lower() in TENS:
                continue
            out.append((WORDS[lt], lt))
        elif lt in TENS:
            out.append((TENS[lt], lt))
    return out


NOUNS = [(r"households?", ("households", "other")), (r"famil(?:y|ies)|lanes?|lines?|rivers?|roads?", ("lanes",)),
         (r"(?:candidate )?(?:joins?|bridges?)", ("bridges",)), (r"pens?", ("pens",))]


# ---------------------------------------------------------------- resolving links in a built site
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
                    txt = None
                break
        self.cache[p] = txt
        return txt

    def has_id(self, path, frag):
        t = self.page(path)
        return bool(t) and bool(re.search(r"""\b(?:id|name)\s*=\s*["']%s["']""" % re.escape(frag), t))


def person_path(person, base):
    s = str(person or "").strip()
    if not s:
        return ""
    if s.startswith("/"):
        return s
    if "/" in s:
        return "/" + s
    b = base if base.endswith("/") else base + "/"
    return "%s%s/" % (b, s)


# ---------------------------------------------------------------- the checks
class Report:
    def __init__(self):
        self.errors, self.warns, self.looked = [], [], 0

    def err(self, code, where, msg):
        self.errors.append((code, where, msg))

    def warn(self, code, where, msg):
        self.warns.append((code, where, msg))


def check_drawing(r, where, cfg, site, living, rep):
    lanes = r.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        rep.err("S1", where, "no lanes: a drawing with nothing on it is not a lines page")
        return
    rep.looked += 1
    base = cfg["personBase"]
    seen_keys = set()
    # where every person stands, for E1: slug -> [places]
    stands = {}

    def stand(slug, place):
        if slug:
            stands.setdefault(slug, []).append(place)

    def resolve_person(person, place):
        if not person:
            return
        if site is None:
            return
        path = person_path(person, base)
        if site.page(path) is None:
            rep.err("P1", place, "person %r does not resolve to a built page (%s)" % (person, path))
        elif "#" in str(person):
            frag = str(person).split("#", 1)[1]
            if not site.has_id(path, frag):
                rep.err("H2", place, "person %r: the page has no id %r" % (person, frag))

    def resolve_href(href, place):
        h = str(href or "")
        if site is None or not h.startswith("/") or h.startswith("//"):
            return
        if site.page(h) is None:
            rep.err("H1", place, "href %r does not resolve to a built page" % h)
        elif "#" in h and not site.has_id(h, h.split("#", 1)[1].split("?")[0]):
            rep.err("H2", place, "href %r: the page has no id %r" % (h, h.split("#", 1)[1]))

    lane_keys = []
    for i, l in enumerate(lanes):
        lk = str(l.get("key") or "")
        w = "%s lane %r" % (where, lk or "#%d" % (i + 1))
        lane_keys.append(lk)
        if not lk:
            rep.err("S1", w, "no key")
        elif lk in seen_keys:
            rep.err("S1", w, "key used twice")
        seen_keys.add(lk)
        for f in ("label", "colour"):
            if not str(l.get(f) or "").strip():
                rep.err("S1", w, "no %s" % f)
        if not str(l.get("href") or "").strip() or not str(l.get("read") or "").strip():
            rep.err("S1", w, "no href and read text: every lane links to where it is argued")
        resolve_href(l.get("href"), w + " href")
        # status
        st = l.get("status")
        if st is None or st == "":
            (rep.warn if cfg["allowLegacy"] or not cfg["requireStatus"] else rep.err)(
                "S2", w, "no status (documented | inferred | origin-unknown | family-lore)" + (" -- legacy `conf` is drawn instead" if l.get("conf") else ""))
        elif st not in STATUSES:
            rep.err("S2", w, "status %r is not one of %s" % (st, ", ".join(STATUSES)))
        else:
            sp = l.get("span")
            if st == "family-lore" and sp:
                rep.err("S3", w, "a family-lore lane has no span: a span is the documented years, and nothing here is documented")
            if sp is not None:
                if not (isinstance(sp, list) and len(sp) == 2):
                    rep.err("S3", w, "span must be [first, last] (last may be null)")
                else:
                    a, b = year(sp[0]), year(sp[1])
                    if sp[0] is not None and a is None or sp[1] is not None and b is None:
                        rep.err("S3", w, "span years must be years, got %r" % (sp,))
                    elif a and b and a > b:
                        rep.err("S3", w, "span runs backwards: %s" % (sp,))
            if st == "inferred" and not str(l.get("statusNote") or "").strip():
                rep.warn("S3", w, "an inferred lane should say what its origin is inferred to be (statusNote)")
            tier, text = status_line(l)
            if len(text) > cfg["maxStatusLine"]:
                rep.err("S3", w, "the printed status line is %d characters (the drawing fits %d): %r" % (len(text), cfg["maxStatusLine"], text[:60] + "..."))
            if l.get("conf"):
                rep.warn("S3", w, "`conf` is ignored when `status` is present; remove it so two words do not say two things")
            # S4
            if isinstance(sp, list) and len(sp) == 2:
                a, b = year(sp[0]), year(sp[1])
                for n in l.get("nodes") or []:
                    y = norm_node(n)["year"]
                    m = re.search(r"\d{4}", str(y))
                    if m:
                        yy = int(m.group(0))
                        if (a and yy < a) or (b and yy > b):
                            rep.warn("S4", w, "node %r (%s) is outside the span %s: stale span or stale node" % (norm_node(n)["place"], y, span_text(sp)))
        # nodes, ends, members
        for n in l.get("nodes") or []:
            o = norm_node(n)
            nw = "%s node %r" % (w, o["place"])
            if o["person"]:
                resolve_person(o["person"], nw)
                stand(str(o["person"]), "lane " + lk)
            if o["evidence"] is not None and str(o["evidence"]).strip().lower() not in EVIDENCE:
                rep.err("N1", nw, "evidence %r is not one of the person page's source words (read, indexed, scanned, tree, inferred, disputed, none)" % o["evidence"])
        for e in l.get("ends") or []:
            o = norm_item(e)
            resolve_href(o["href"], "%s end %r" % (w, o["name"]))
            if o["person"]:
                resolve_person(o["person"], "%s end %r" % (w, o["name"]))
        ms = [member_slug(m) for m in (l.get("members") or [])]
        if len(set(ms)) != len(ms):
            rep.err("P2", w, "a member is listed twice")
        for m in ms:
            resolve_person(m, "%s member %r" % (w, m))
            stand(m, "lane " + lk)
            if m in living:
                rep.err("P3", w, "member %r is on the living list" % m)
        for n in l.get("nodes") or []:
            p = norm_node(n)["person"]
            if p and str(p) in living:
                rep.err("P3", w, "node person %r is on the living list" % p)

    # pens
    unplaced_names = set()
    declared = pens_of(r)
    if isinstance(r.get("pens"), list) and (r.get("unplaced") or r.get("loose")):
        rep.warn("K1", where, "`pens` is present, so `unplaced` / `loose` are ignored by the drawing; remove them")
    for i, p in enumerate(declared):
        pid = str(p.get("id") or "pen-%d" % (i + 1))
        w = "%s pen %r" % (where, pid)
        kind = p.get("kind", "not-yet-placed")
        if kind not in PEN_KINDS:
            rep.err("K1", w, "kind %r is not one of %s" % (kind, ", ".join(PEN_KINDS)))
        items = [norm_item(x) for x in (p.get("items") or [])]
        members = p.get("members") or []
        if not items and not members:
            if p.get("head") or p.get("note") or p.get("_legacy"):
                rep.err("K1", w, "a heading over nothing: the pen has no items and no members, so the drawing does not print it, and a heading would claim the archive looked and found none")
            else:
                rep.err("K1", w, "an empty pen")
            continue
        if kind == "not-yet-placed":
            unplaced_names.update(it["name"] for it in items)
        for it in items:
            iw = "%s item %r" % (w, it["name"])
            if not it["name"]:
                rep.err("K1", w, "an item with no name")
            resolve_href(it["href"], iw)
            if it["person"]:
                resolve_person(it["person"], iw)
                stand(str(it["person"]), "pen " + pid)
        ms = [member_slug(m) for m in members]
        if len(set(ms)) != len(ms):
            rep.err("P2", w, "a member is listed twice")
        for m in ms:
            resolve_person(m, "%s member %r" % (w, m))
            stand(m, "pen " + pid)
            if m in living:
                rep.err("P3", w, "member %r is on the living list" % m)
        cnt = p.get("count")
        if members:
            if cnt is not None and cnt != len(members):
                rep.err("K2", w, "count is %s but %d members are listed" % (cnt, len(members)))
            elif cnt is None:
                pass
        elif cnt is not None:
            rep.warn("K3", w, "count %s with no members listed: it cannot be checked, and nobody can be reached from it" % cnt)
        if cnt is not None and (not isinstance(cnt, int) or isinstance(cnt, bool) or cnt < 0):
            rep.err("K2", w, "count must be a whole number")
        if items and not str(p.get("note") or "").strip():
            rep.warn("K4", w, "no note: a pen should say why these are in a pen and what would move them out")

    # exclusivity
    if cfg["exclusive"]:
        for slug, places in sorted(stands.items()):
            if len(places) > 1 and slug not in cfg["sharedAllowed"]:
                rep.err("E1", where, "%r stands in %d places (%s): exclusive means one lane or one pen" % (slug, len(places), "; ".join(places)))

    # bridges
    for b in r.get("bridges") or []:
        for end in ("from", "to"):
            v = b.get(end)
            if v not in seen_keys and v not in unplaced_names:
                rep.err("B1", where, "bridge %s %r names no lane and no unplaced household" % (end, v))
        resolve_href(b.get("href"), where + " bridge %r" % (b.get("label") or "")[:30])

    # numbers in the title and caption
    c = counts(r)
    if cfg["titleNumbers"] and r.get("title"):
        allowed = {c["lanes"], c["households"], c["other"], c["bridges"], c["pens"], c["people_lanes"], c["people_pens"]} - {0}
        for v, word in number_tokens(plain(r["title"])):
            if v not in allowed:
                rep.err("T1", where, "the title says %r (%d) and the data can state %s: a count typed into a title goes stale" %
                        (word, v, ", ".join("%s=%d" % (k, c[k]) for k in ("lanes", "households", "other", "bridges") if c[k])))
    if r.get("caption"):
        cap = plain(re.sub(r"<[^>]+>", " ", str(r["caption"])))
        words = re.findall(r"[A-Za-z\u00c0-\u024f]+|\d+", cap)
        for i, w in enumerate(words):
            toks = number_tokens(w)
            if not toks:
                continue
            v = toks[0][0]
            for noun in words[i + 1:i + 5]:
                n = noun.lower()
                if re.fullmatch(r"households?", n):
                    want = ("households", "other")
                elif re.fullmatch(r"famil(?:y|ies)|lanes?", n):
                    want = ("lanes",)
                elif re.fullmatch(r"joins?|bridges?", n):
                    want = ("bridges",)
                else:
                    continue
                if v not in {c[k] for k in want}:
                    rep.warn("T2", where, "the caption says %r before %r and the data has %s" % (w, noun, ", ".join("%s=%d" % (k, c[k]) for k in want)))
                break


def load_drawings(path):
    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, list):
        return [(("set %s" % (s.get("name") or i + 1)), s) for i, s in enumerate(d)]
    if isinstance(d, dict) and isinstance(d.get("sets"), list):
        return [("set %s" % (s.get("name") or s.get("slug") or i + 1), s) for i, s in enumerate(d["sets"])]
    return [("drawing", d)]


def run(lines, dist, cfg, living, rep, no_dist=False):
    try:
        drawings = load_drawings(lines)
    except (OSError, ValueError) as e:
        print("checklines: cannot read %s: %s" % (lines, e))
        return 2
    site = None if no_dist else Site(dist)
    if site is not None and not os.path.isdir(dist):
        print("checklines: no built site at %s (build first, or pass --no-dist)" % dist)
        return 2
    for where, r in drawings:
        check_drawing(r, where, cfg, site, living, rep)
    return 0


def default_cfg():
    return {"exclusive": True, "sharedAllowed": set(), "personBase": "/people/", "requireStatus": True,
            "maxStatusLine": 100, "titleNumbers": True, "allowLegacy": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lines")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--no-dist", action="store_true")
    ap.add_argument("--config")
    ap.add_argument("--living")
    ap.add_argument("--allow-legacy", action="store_true")
    ap.add_argument("--no-exclusive", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.lines:
        ap.error("--lines is required")
    cfg = default_cfg()
    if a.config:
        try:
            c = (json.load(open(a.config, encoding="utf-8")) or {}).get("lines") or {}
        except (OSError, ValueError) as e:
            print("checklines: cannot read config %s: %s" % (a.config, e))
            return 2
        for k, v in c.items():
            if k == "sharedAllowed":
                cfg[k] = set(v)
            elif k in cfg:
                cfg[k] = v
            else:
                print("checklines: unknown setting lines.%s in %s" % (k, a.config))
                return 2
    if a.allow_legacy:
        cfg["allowLegacy"] = True
    if a.no_exclusive:
        cfg["exclusive"] = False
    living = set()
    if a.living:
        try:
            lv = json.load(open(a.living, encoding="utf-8"))
        except (OSError, ValueError) as e:
            print("checklines: cannot read living list %s: %s" % (a.living, e))
            return 2
        living = set(lv.get("slugs", lv.keys()) if isinstance(lv, dict) else lv)
    rep = Report()
    rc = run(a.lines, a.dist, cfg, living, rep, a.no_dist)
    if rc:
        return rc
    for code, where, msg in rep.errors:
        print("FAIL [%s] %s: %s" % (code, where, msg))
    for code, where, msg in rep.warns:
        print("warn [%s] %s: %s" % (code, where, msg))
    if rep.looked == 0 and not rep.errors:
        print("checklines: nothing was checked (no drawing had lanes)")
        return 2
    print("checklines: %d drawing(s), %d error(s), %d warning(s)%s" % (rep.looked, len(rep.errors), len(rep.warns),
                                                                      "; links and persons NOT resolved (--no-dist)" if a.no_dist else ""))
    return 1 if rep.errors else 0


# ---------------------------------------------------------------- self-test
def _fixture():
    """A clean drawing and the built site it points at. Invented names only."""
    r = {
        "title": "Two families of one surname, and the road each of them took",
        "caption": "<strong>Two real households of the name</strong> belong to nobody yet.",
        "lanes": [
            {"key": "a", "colour": "#3a7d6b", "label": "Alder", "href": "/lines/#alder", "read": "Alder chapter →",
             "status": "documented", "span": [1701, 1888], "members": ["ada-alder"],
             "nodes": [{"place": "Ashby", "year": "1701", "why": "Baptism read.", "person": "bea-alder", "evidence": "read"},
                       ["Brook", "1744", "Marriage read."]],
             "ends": [["Dunmore", "/lines/", "Where the last of them went."]]},
            {"key": "b", "colour": "#b0652e", "label": "Birch", "href": "/lines/", "read": "Birch chapter →",
             "status": "inferred", "span": [1755, 1902], "statusNote": "origin inferred Kentish",
             "nodes": [{"place": "Eastry", "year": "1755", "why": "First baptism.", "person": "cal-birch", "evidence": "inferred"}],
             "ends": []},
        ],
        "pens": [
            {"id": "u", "kind": "not-yet-placed", "note": "Real and documented, on no lane.",
             "items": [["Penrith", "/lines/", "Four baptisms."], ["Quorn", "/lines/#alder", "One marriage."]],
             "members": ["dee-penrith", {"person": "eli-quorn", "reason": "the one marriage"}], "count": 2},
            {"id": "o", "kind": "different-stock", "note": "Kept apart on purpose.", "items": [["Brazil", "/lines/", "Another stock."]]},
        ],
        "bridges": [{"from": "a", "to": "Penrith", "conf": "inf", "label": "a candidate join", "href": "/lines/"}],
    }
    return r


def _site(root):
    for p in ("ada-alder", "bea-alder", "cal-birch", "dee-penrith", "eli-quorn", "fay-extra"):
        os.makedirs(os.path.join(root, "people", p))
        open(os.path.join(root, "people", p, "index.html"), "w").write("<h1>%s</h1>" % p)
    os.makedirs(os.path.join(root, "lines"))
    open(os.path.join(root, "lines", "index.html"), "w").write('<h1 id="top">Lines</h1><h2 id="alder">Alder</h2>')


def selftest():
    cases = json.load(open(os.path.join(KIT, "data", "lines-cases.json"), encoding="utf-8"))["status"]
    res = []

    def ok(label, cond, detail=""):
        res.append(bool(cond))
        print("  %s  %s%s" % ("ok  " if cond else "FAIL", label, ("  [%s]" % detail[:300]) if detail and not cond else ""))

    print("status line, the shared cases (the JS reads the same file)")
    for c in cases:
        tier, text = status_line(c["lane"])
        ok(c["id"], text == c["text"], "%r != %r" % (text, c["text"]))
    tmp = tempfile.mkdtemp(prefix="checklines-")
    try:
        dist = os.path.join(tmp, "dist")
        _site(dist)

        def gate(r, extra=None, cfg=None, living=None):
            f = os.path.join(tmp, "lines.json")
            json.dump(r, open(f, "w", encoding="utf-8"), ensure_ascii=False)
            args = ["--lines", f, "--dist", dist] + (extra or [])
            if cfg is not None:
                cf = os.path.join(tmp, "cfg.json")
                json.dump({"lines": cfg}, open(cf, "w"))
                args += ["--config", cf]
            if living is not None:
                lf = os.path.join(tmp, "living.json")
                json.dump(living, open(lf, "w"))
                args += ["--living", lf]
            p = subprocess.run([sys.executable, os.path.abspath(__file__)] + args, capture_output=True, text=True)
            return p.returncode, p.stdout + p.stderr

        print("controls")
        rc, out = gate(_fixture())
        ok("the clean fixture passes", rc == 0 and "0 error(s)" in out, out)
        rc, out = gate({"sets": [_fixture(), _fixture()]})
        ok("a {sets: [...]} file is read, each set held on its own", rc == 0, out)
        rc, out = gate([_fixture()])
        ok("a list of drawings is read", rc == 0, out)

        print("planted faults: each must fail with its own code, and the control above must not")

        def plant(label, code, fn, extra=None, cfg=None, living=None, warn=False, base=None):
            r = copy.deepcopy(base or _fixture())
            fn(r)
            rc, out = gate(r, extra, cfg, living)
            want = ("warn [%s]" % code) if warn else ("FAIL [%s]" % code)
            ok(label, want in out and (rc == 0 if warn else rc == 1), "rc=%s %s" % (rc, out[-400:]))

        plant("a lane with no status", "S2", lambda r: r["lanes"][0].pop("status"))
        plant("a lane with no status, legacy allowed, is a warning only", "S2", lambda r: r["lanes"][0].pop("status"), extra=["--allow-legacy"], warn=True)
        plant("a status that is not a tier", "S2", lambda r: r["lanes"][0].update(status="mostly"))
        plant("a family-lore lane that carries a span", "S3", lambda r: r["lanes"][0].update(status="family-lore"))
        plant("a span that runs backwards", "S3", lambda r: r["lanes"][0].update(span=[1888, 1701]))
        plant("a status line too long to print", "S3", lambda r: r["lanes"][1].update(statusNote="x " * 60))
        plant("an inferred lane that does not say to what", "S3", lambda r: r["lanes"][1].pop("statusNote"), warn=True)
        plant("a stale `conf` beside a status", "S3", lambda r: r["lanes"][0].update(conf="DOCUMENTED"), warn=True)
        plant("a node outside the lane's span", "S4", lambda r: r["lanes"][0]["nodes"].append(["Late", "1999", "x"]), warn=True)
        plant("a lane with no label", "S1", lambda r: r["lanes"][0].update(label=""))
        plant("two lanes with one key", "S1", lambda r: r["lanes"][1].update(key="a"))
        plant("no lanes at all", "S1", lambda r: r.update(lanes=[], pens=[], bridges=[]))
        plant("a node person that is not a built page", "P1", lambda r: r["lanes"][0]["nodes"][0].update(person="nobody-here"))
        plant("a pen member that is not a built page", "P1", lambda r: r["pens"][0]["members"].__setitem__(0, "ghost"))
        plant("a person page given with a fragment it does not have", "H2", lambda r: r["lanes"][0]["nodes"][0].update(person="/people/bea-alder/#nope"))
        plant("a member listed twice in a pen", "P2", lambda r: r["pens"][0].update(members=["dee-penrith", "dee-penrith"], count=2))
        plant("a living person listed in a pen", "P3", lambda r: None, living=["dee-penrith"])
        plant("a person on a lane and in a pen", "E1", lambda r: r["pens"][0]["members"].__setitem__(0, "bea-alder"))
        plant("the same person as a node of one lane and a member of another", "E1", lambda r: r["lanes"][1].update(members=["bea-alder"]))
        # exclusive off, and an allowed exception, must both pass (the control for E1)
        r = _fixture(); r["pens"][0]["members"][0] = "bea-alder"
        rc, out = gate(r, cfg={"exclusive": False})
        ok("exclusive: false lets a person stand twice", rc == 0, out)
        rc, out = gate(r, cfg={"sharedAllowed": ["bea-alder"]})
        ok("sharedAllowed names a stated exception", rc == 0, out)
        plant("a pen with a heading and nothing under it (new form)", "K1", lambda r: r["pens"].append({"id": "e", "kind": "different-stock", "head": "A different stock", "items": []}))
        plant("a legacy heading over an empty list", "K1", lambda r: (r.pop("pens"), r.update(unplaced=[], unplacedHead="Households not yet placed")))
        plant("a pen of an unknown kind", "K1", lambda r: r["pens"][1].update(kind="miscellany"))
        plant("a pen whose count is not its members", "K2", lambda r: r["pens"][0].update(count=5))
        plant("a count with nobody listed", "K3", lambda r: r["pens"][1].update(count=3), warn=True)
        plant("a pen with households and no note", "K4", lambda r: r["pens"][0].pop("note"), warn=True)
        plant("a stale number in the title", "T1", lambda r: r.update(title="Six families of one surname, and the road each of them took"))
        plant("a stale number in the title, in digits", "T1", lambda r: r.update(title="The 9 lines of a name"))
        plant("a stale number in the caption", "T2", lambda r: r.update(caption="There are nine real households of the name."), warn=True)
        plant("a bridge to nowhere", "B1", lambda r: r["bridges"].append({"from": "a", "to": "Atlantis", "label": "x"}))
        plant("a lane link to a page that was never built", "H1", lambda r: r["lanes"][0].update(href="/svetvincenat-line/"))
        plant("a pen item link to a fragment that is not there", "H2", lambda r: r["pens"][0]["items"][0].__setitem__(1, "/lines/#gone"))
        plant("an evidence word the person page does not know", "N1", lambda r: r["lanes"][0]["nodes"][0].update(evidence="hearsay"))
        print("refusals")
        f = os.path.join(tmp, "none.json"); json.dump({"lanes": []}, open(f, "w"))
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--lines", f, "--dist", dist], capture_output=True, text=True)
        ok("an empty drawing is refused, not passed", p.returncode == 1, p.stdout)
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--lines", os.path.join(tmp, "absent.json"), "--dist", dist], capture_output=True, text=True)
        ok("a file that cannot be read exits 2", p.returncode == 2, p.stdout)
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--lines", os.path.join(tmp, "lines.json"), "--dist", os.path.join(tmp, "nodist")], capture_output=True, text=True)
        ok("a missing build exits 2 and says so", p.returncode == 2 and "no built site" in p.stdout, p.stdout)
        r = _fixture()
        f = os.path.join(tmp, "nd.json"); json.dump(r, open(f, "w"))
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--lines", f, "--no-dist"], capture_output=True, text=True)
        ok("--no-dist passes and says links were not resolved", p.returncode == 0 and "NOT resolved" in p.stdout, p.stdout)
        print("number words")
        ok("seven / 7 / twenty-one are counts, one is not", [v for v, _ in number_tokens("Seven families of one surname, 7 and twenty-one")] == [7, 7, 21])
        ok("a year is not a count", number_tokens("The 1628 line") == [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = res.count(False)
    print("\n%d cases, %d failed" % (len(res), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
