#!/usr/bin/env python3
"""Same-person candidates: the pure logic. No file or network access here; samepersoncandidates.py loads the data.

WHAT THIS IS. A way of PROPOSING joins in a family tree, for a person to look at. It reads one archive's tree.json
(the Roots & Routes contract) and, for a person, ranks other people who may be:

  parents   their father or their mother              (an orphan's likely parents)
  spouse    their husband or wife
  same      the same person written twice             (two rows that may be one)

WHAT IT IS NOT. It never joins anyone, never writes to a tree, a roster or the Atlas, and a proposal is never a finding
(the estate's rule: a `lead` is never a finding). A proposal is a place to look, with its reasons written out. A pair a
reader decides against is recorded in a kept-apart list and is not proposed again.

WHAT IT KNOWS, AND FROM WHERE. Spellings of a surname, forms of a given name and dated place names come from the Record
Atlas's own catalogues (data/surname-families.json, data/given-name-families.json, data/place-names.json), read-only:
this file keeps no table of any of them. Without the catalogues it falls back to typography and accents only and says so.

THE SIGNALS (every one is a number with a sentence; the sum is a ranking aid, not a probability):

  relationships   a household that fits (the candidate's other children born where this person was, in the years that
                  fit the spacing; a mother's husband bearing this person's surname) are the strongest
  surname         the Atlas catalogue: same / attested / rule are strong, lead is weak, case-by-case is neutral,
                  not-same blocks. For a MOTHER or a SPOUSE the surname is not evidence (a maiden name differs).
  given name      the Atlas given-name families (Ivan = Johann = Giovanni = Zuane = Joannes). A grandchild is often
                  named for a grandfather (a small plus); a living sibling already bearing the name is a clash.
  place           the Atlas place id, resolved with the name of the year; same place, within 25 km, further; unknown
                  is neutral. A place that was taken from a relative (`bpe`) is never evidence.
  dates           ranges, never points. A parent is 13-60 years older (a mother 13-55); stated ages are off by 3-8
                  years, so an estimated year (`bye`, `dye`) is a wide range, and in strict mode it is no year at all.
  conflicts       BLOCK: a parent dead before the birth, a gap outside 13-60, the person's own descendant,
                  a different register-grade parent, a not-same surname. A sex mismatch is a penalty only: some
                  trees guess sex from a given name.

DECEASED PEOPLE ONLY. A person is eligible only if the kit's living rule (living_rule.is_living) says they are not
living; an estimated death year is not a death record. Nobody living is ever a subject or a candidate.

NAMESAKES. A grandchild named for a grandfather, two cousins of one name in one parish: the traps of this work. Every
proposal carries the number of OTHER candidates within a point of its score (`rivals`) and a `namesakes` count (others
with the same name, plausible age), and the tier `strong` requires a margin over the runner-up.
"""
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import living_rule as lr  # noqa: E402  (the estate's one definition of who is living)

STRONG = ("same", "attested", "rule")
TYPO = re.compile(r"[\s'’\-]+")


# ---------------------------------------------------------------- keys (the same two keys the Atlas catalogues use)
def search_key(s):
    """What an index treats as one: lower case, accents gone, separators gone."""
    s = (s or "").translate(str.maketrans({"đ": "d", "ł": "l", "ø": "o", "ß": "ss", "æ": "ae", "œ": "oe"}))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def form_key(s):
    """One FORM: case, spaces, hyphens and apostrophes only. An accent is a spelling and stays."""
    return TYPO.sub("", unicodedata.normalize("NFC", s or "").lower())


def tokens(given):
    return [t for t in re.split(r"[\s/,.]+", given or "") if t]


# ---------------------------------------------------------------- the Atlas catalogues (read-only inputs)
class Catalogue:
    """Surname and given-name families as the Atlas publishes them. Pass the parsed JSON documents, or None."""

    def __init__(self, surname_doc=None, given_doc=None):
        self.have_surnames = bool(surname_doc)
        self.have_givens = bool(given_doc)
        self.sur, self.sur_notsame = self._index(surname_doc)
        self.giv, _ = self._index(given_doc)

    @staticmethod
    def _index(doc):
        idx, notsame = defaultdict(dict), defaultdict(set)
        for fam in (doc or {}).get("families", []):
            fid = fam["id"]
            for m in fam.get("members", []):
                st = m.get("status")
                if st in ("not-same", "slip"):
                    continue
                idx[form_key(m["form"])][fid] = st
            if fam.get("name"):
                idx[form_key(fam["name"])].setdefault(fid, "same")
            for m in fam.get("notSame", []):
                notsame[fid].add(form_key(m.get("form", "")))
        return idx, notsame

    def surname_relation(self, a, b):
        """(kind, sentence). kinds: unknown, same-form, catalogue, fold, lead, case-by-case, not-same, different."""
        if not a or not b:
            return "unknown", "a surname is missing"
        fa, fb = form_key(a), form_key(b)
        if fa == fb:
            return "same-form", "the same spelling (%s)" % a
        ia, ib = self.sur.get(fa, {}), self.sur.get(fb, {})
        for fam in set(ia) & set(ib):
            sa, sb = ia[fam], ib[fam]
            if sa in STRONG and sb in STRONG:
                return "catalogue", "the Atlas writes %s and %s as one family name (%s / %s)" % (a, b, sa, sb)
        for fam in set(ia) & set(ib):
            sa, sb = ia[fam], ib[fam]
            if "case-by-case" in (sa, sb):
                return "case-by-case", "%s and %s are one name only some of the time (Atlas: case-by-case)" % (a, b)
            return "lead", "the Atlas lists %s and %s as a possible spelling, never seen on a record (lead)" % (a, b)
        for fam, bad in self.sur_notsame.items():
            if (fb in bad and ia.get(fam) in STRONG) or (fa in bad and ib.get(fam) in STRONG):
                return "not-same", "the Atlas records %s and %s as different names" % (a, b)
        if search_key(a) == search_key(b):
            return "fold", "%s and %s differ only by an accent" % (a, b)
        return "different", "%s and %s are not the same name in the Atlas catalogue" % (a, b)

    def given_families(self, given):
        """{family id: best status} over the tokens of a given name."""
        out = {}
        for t in tokens(given):
            for fam, st in self.giv.get(form_key(t), {}).items():
                if st in STRONG or out.get(fam) not in STRONG:
                    out[fam] = st if st in STRONG else out.get(fam, st)
        return out

    def same_full_name(self, a, b):
        """Every token of both names matches in order, as a spelling or as one Atlas family: Giovanni Battista = Joannes Baptista."""
        ta, tb = tokens(a), tokens(b)
        if not ta or len(ta) != len(tb):
            return False
        for x, y in zip(ta, tb):
            if search_key(x) == search_key(y):
                continue
            kx, ky = self.given_families(x), self.given_families(y)
            if not any(kx[f] in STRONG and ky.get(f) in STRONG for f in kx if f in ky):
                return False
        return True

    def given_relation(self, a, b):
        """(kind, sentence). kinds: unknown, identical, same-name, shared-token, lead, different."""
        if not tokens(a) or not tokens(b):
            return "unknown", "a given name is missing"
        if search_key(a) == search_key(b):
            return "identical", "the same given name (%s)" % a
        ta, tb = tokens(a), tokens(b)
        ka, kb = self.given_families(ta[0]), self.given_families(tb[0])
        if any(ka[f] in STRONG and kb.get(f) in STRONG for f in ka if f in kb):
            if len(ta) > 1 and len(tb) > 1 and not self.same_full_name(a, b):
                return "partial", "%s and %s start with the same name but go on differently" % (a, b)
            return "same-name", "%s and %s are one given name in the Atlas (%s)" % (a, b, ", ".join(sorted(set(ka) & set(kb))))
        fa, fb = self.given_families(a), self.given_families(b)
        if any(fa[f] in STRONG and fb.get(f) in STRONG for f in fa if f in fb):
            return "shared-token", "%s and %s share a name once the Atlas forms are read" % (a, b)
        if set(fa) & set(fb):
            return "lead", "%s and %s are possibly one given name (Atlas: lead)" % (a, b)
        if search_key(ta[0]) == search_key(tb[0]):
            return "same-name", "the same first name (%s)" % ta[0]
        return "different", "%s and %s are different given names" % (a, b)


# ---------------------------------------------------------------- places, by the name of the year
def haversine(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742.0 * math.asin(math.sqrt(h))


class Places:
    """place_map.json (name -> coordinates, Atlas id) plus the Atlas's dated names (place-names.json). Both optional."""

    NEAR_KM, MID_KM = 25.0, 150.0

    def __init__(self, place_map=None, place_names_doc=None):
        self.by_name, self.by_id = {}, {}
        for raw, e in (place_map or {}).items():
            ent = {"key": e.get("atlas_id") or "n:" + search_key(e.get("name") or raw), "name": e.get("name") or raw,
                   "lat": e.get("lat"), "lon": e.get("lon")}
            self.by_name[search_key(raw)] = ent
            self.by_name.setdefault(search_key(ent["name"]), ent)
            self.by_id.setdefault(ent["key"], ent)
        self.alias = defaultdict(list)
        for p in (place_names_doc or {}).get("places", []):
            for n in p.get("names", []):
                self.alias[search_key(n["name"])].append((p["id"], n.get("from"), n.get("to")))
        self.have_names = bool(place_names_doc)

    def resolve(self, name, year=None):
        """The place a name means in `year`: the archive's own place map first, then the Atlas's dated names."""
        if not name:
            return None
        k = search_key(name)
        if k in self.by_name:
            return self.by_name[k]
        for pid, f, t in self.alias.get(k, []):
            if (f is None or year is None or year >= f) and (t is None or year is None or year <= t):
                return self.by_id.get(pid) or {"key": pid, "name": name, "lat": None, "lon": None}
        return None

    def relation(self, a, b):
        """('same'|'near'|'mid'|'far'|'unknown', km or None)."""
        if not a or not b:
            return "unknown", None
        if a["key"] == b["key"]:
            return "same", 0.0
        if None in (a.get("lat"), a.get("lon"), b.get("lat"), b.get("lon")):
            return "unknown", None
        km = haversine((a["lat"], a["lon"]), (b["lat"], b["lon"]))
        return ("near" if km <= self.NEAR_KM else "mid" if km <= self.MID_KM else "far"), km


# ---------------------------------------------------------------- people and the graph
def norm_person(p):
    return {
        "id": p["id"], "sex": p.get("sex") or "u", "given": p.get("given") or "", "sur": p.get("sur") or "",
        "by": p.get("by"), "bye": bool(p.get("bye")), "bp": p.get("bp") or "", "bpe": bool(p.get("bpe")),
        "dy": p.get("dy"), "dye": bool(p.get("dye")), "dp": p.get("dp") or "",
        "father": p.get("father"), "mother": p.get("mother"), "spouse": list(p.get("spouse") or []),
        "kids": list(p.get("kids") or []), "fg": p.get("fg"), "mg": p.get("mg"),
        "route": p.get("route") or [], "name": (p.get("given") or "") + (" " + p["sur"] if p.get("sur") else ""),
    }


class Context:
    """Everything a score needs. `strict`: an estimated year or a borrowed place counts as unknown (the honest test)."""

    def __init__(self, people, catalogue=None, places=None, strict=False, today_year=None, block_with_estimates=True):
        self.P = {p["id"]: norm_person(p) for p in people}
        self.cat = catalogue or Catalogue()
        self.pl = places or Places()
        self.strict = strict
        # strict scoring ignores estimated years; BLOCKING (a gross contradiction) may still use them as wide ranges.
        # The leave-one-out test turns this off: an estimate worked out from the hidden relative would flatter the truth.
        self.block_est = block_with_estimates
        self.today = today_year or lr.this_year()
        self.hide = None
        self._kids = defaultdict(set)
        for p in self.P.values():
            for k in p["kids"]:
                if k in self.P:
                    self._kids[p["id"]].add(k)
            for par in (p["father"], p["mother"]):
                if par in self.P:
                    self._kids[par].add(p["id"])
        self._sp = defaultdict(set)
        for p in self.P.values():
            for s in p["spouse"]:
                if s in self.P:
                    self._sp[p["id"]].add(s)
                    self._sp[s].add(p["id"])
        self._el = {}

    # --- links, with one person's links removed (leave-one-out: that person is an orphan)
    def kids(self, x):
        if self.hide == x:
            return []
        return [k for k in sorted(self._kids.get(x, ())) if k != self.hide]

    def parents(self, x):
        if self.hide == x:
            return []
        p = self.P[x]
        return [q for q in (p["father"], p["mother"]) if q in self.P and q != self.hide]

    def spouses(self, x):
        out = set() if self.hide == x else {s for s in self._sp.get(x, ()) if s != self.hide}
        if self.hide != x:
            for k in self.kids(x):
                for q in self.parents(k):
                    if q != x:
                        out.add(q)
        return sorted(out)

    def descendants(self, x):
        seen, todo = set(), list(self.kids(x))
        while todo:
            c = todo.pop()
            if c not in seen:
                seen.add(c)
                todo.extend(self.kids(c))
        return seen

    # --- years as ranges
    def birth(self, x, blocking=False):
        p = self.P[x]
        if p["by"] is None or (p["bye"] and self.strict and not (blocking and self.block_est)):
            return None
        return (p["by"] - 8, p["by"] + 8) if p["bye"] else (p["by"], p["by"])

    def death(self, x):
        p = self.P[x]
        if p["dy"] is None or p["dye"]:
            return None  # an estimated death year is not a death record: it never blocks and never scores
        return (p["dy"], p["dy"])

    # --- places as (resolved place, year, what)
    def points(self, x, include_children=True):
        p, pts = self.P[x], []
        if p["bp"] and not (p["bpe"] and self.strict) and p["by"] is not None:
            pts.append((self.pl.resolve(p["bp"], p["by"]), p["by"], "born"))
        for st in p["route"]:
            try:
                pts.append((self.pl.resolve(st[0], st[1]), st[1], "lived"))
            except (IndexError, TypeError):
                pass
        if p["dp"] and p["dy"] is not None and not p["dye"]:
            pts.append((self.pl.resolve(p["dp"], p["dy"]), p["dy"], "died"))
        if include_children:
            for k in self.kids(x):
                c = self.P[k]
                if c["bp"] and c["by"] is not None and not (c["bpe"] and self.strict):
                    pts.append((self.pl.resolve(c["bp"], c["by"]), c["by"], "a child born"))
        return [t for t in pts if t[0] is not None]

    # --- who may be named at all
    def eligible(self, x):
        if x in self._el:
            return self._el[x]
        p = self.P[x]
        recorded = p["dy"] is not None and not p["dye"]
        kids = [self.P[k]["by"] for k in self._kids.get(x, ()) if self.P[k]["by"] is not None]
        ok = not lr.is_living(p["by"], recorded, (), self.today, youngest_child_year=max(kids) if kids else None)
        self._el[x] = ok
        return ok


# ---------------------------------------------------------------- signals
def sig(w, why, kind=""):
    return {"w": round(float(w), 2), "why": why, "kind": kind}


def tent(m, bands):
    """bands: [(lo, hi, w), ...] in order; the first that holds wins; default 0."""
    for lo, hi, w in bands:
        if lo <= m <= hi:
            return w
    return 0.0


def year_gap(ctx, older, younger, blocking=False):
    """(lo, hi) of how many years `older` was born before `younger`, or None."""
    a, b = ctx.birth(older, blocking), ctx.birth(younger, blocking)
    if not a or not b:
        return None
    return b[0] - a[1], b[1] - a[0]


def place_signal(ctx, s_points, c_points, year, w_same=2.0, w_near=1.2, window=12):
    """The candidate's point nearest in time to `year`, compared with the subject's place at that year."""
    if not s_points or not c_points:
        return None
    best = None
    for place, y, what in c_points:
        d = abs((y if y is not None else year + 99) - year)
        if best is None or d < best[0]:
            best = (d, place, y, what)
    d, place, y, what = best
    if d > 40:
        return None   # a place from another age says nothing
    rel = None
    for sp, sy, swhat in s_points:
        r, km = ctx.pl.relation(sp, place)
        if rel is None or ("same", "near", "mid", "far", "unknown").index(r) < ("same", "near", "mid", "far", "unknown").index(rel[0]):
            rel = (r, km, sp)
    r, km, sp = rel
    near_in_time = d <= window
    if r == "same":
        return sig(w_same if near_in_time else w_same * 0.7, "%s: the same place (%s) as %s%s" % (what, place["name"], sp["name"], "" if near_in_time else ", but %d years apart" % d), "place")
    if r == "near":
        return sig(w_near if near_in_time else w_near * 0.7, "%s: %s is %d km from %s" % (what, place["name"], round(km), sp["name"]), "place")
    if r == "mid":
        return sig(-0.2, "%s: %s is %d km from %s" % (what, place["name"], round(km), sp["name"]), "place")
    if r == "far":
        return sig(-1.2 if near_in_time else -0.4, "%s: %s is %d km from %s" % (what, place["name"], round(km), sp["name"]), "place")
    return None


def parent_signals(ctx, s, c, role):
    """Score `c` as the father or mother (role 'father'|'mother') of `s`. -> (signals, blocks)."""
    S, C = ctx.P[s], ctx.P[c]
    sg, bl = [], []
    if c == s:
        return sg, ["is the person themself"]
    # sex may be a GUESS from a given name (tree.json: "u" is the honest value): a penalty, not a block
    if role == "father" and C["sex"] == "f":
        sg.append(sig(-2.5, "is recorded as a woman (a tree may guess sex from a given name)", "sex"))
    if role == "mother" and C["sex"] == "m":
        sg.append(sig(-2.5, "is recorded as a man (a tree may guess sex from a given name)", "sex"))
    if c in ctx.descendants(s):
        bl.append("is this person's own descendant")
    # register-grade parent already named for the other slot is not touched: only THIS slot is open
    # --- dates
    gap = year_gap(ctx, c, s)
    hi_ok = 60 if role == "father" else 55
    gb = year_gap(ctx, c, s, True)
    if gb:
        if gb[1] < 13:
            bl.append("would be %s years older at most: under 13 at the birth" % gb[1])
        if gb[0] > hi_ok:
            bl.append("would be %s years older at least: over %d at the birth" % (gb[0], hi_ok))
    if gap:
        lo, hi = gap
        if not bl:
            m, wide = (lo + hi) / 2.0, (hi - lo) > 8
            f = 0.5 if wide else 1.0
            bands = ([(20, 45, 1.5), (17, 19.99, .7), (45.01, 52, .7), (13, 16.99, -.3), (52.01, 60, -.3)] if role == "father"
                     else [(19, 36, 1.5), (15, 18.99, .7), (36.01, 42, .7), (13, 14.99, -.3), (42.01, 55, -.3)])
            w = tent(m, bands) * f
            sg.append(sig(w, "born about %d years before them%s" % (round(m), " (an estimate)" if wide else ""), "dates"))
    else:
        sg.append(sig(0.4, "no usable birth year for one of them (neither for nor against)", "dates"))
    d = ctx.death(c)
    b = ctx.birth(s, True)
    if d and b:
        need = b[0] - (1 if role == "father" else 0)
        if d[1] < need:
            bl.append("died in %d, before the birth" % d[1])
    # --- surname (a mother's maiden name is not evidence)
    if role == "father":
        kind, why = ctx.cat.surname_relation(S["sur"], C["sur"])
        w = {"same-form": 3.0, "catalogue": 2.5, "fold": 1.8, "lead": .8, "case-by-case": .3, "unknown": 0.0, "different": -3.0}.get(kind)
        if kind == "not-same":
            bl.append(why)
        elif w is not None and kind != "unknown":
            sg.append(sig(w, "surname: " + why, "surname"))
    # --- place
    s_pts = [t for t in ctx.points(s, include_children=False) if t[2] == "born"]
    ps = place_signal(ctx, s_pts, ctx.points(c), S["by"] if S["by"] is not None else 0)
    if ps and S["by"] is not None:
        sg.append(ps)
    # --- the household: the candidate's other children
    sibs = [k for k in ctx.kids(c) if k != s]
    if sibs:
        spts = s_pts
        same_place = 0
        for k in sibs:
            for place, y, what in ctx.points(k, include_children=False):
                if what == "born" and spts and ctx.pl.relation(spts[0][0], place)[0] == "same":
                    same_place += 1
        if same_place:
            sg.append(sig(min(0.4 * same_place, 1.2), "%d of the candidate's other children were born in the same place" % same_place, "household"))
        yrs = [ctx.P[k]["by"] for k in sibs if ctx.P[k]["by"] is not None and not (ctx.P[k]["bye"] and ctx.strict)]
        if yrs and S["by"] is not None and not (S["bye"] and ctx.strict):
            lo, hi = min(yrs), max(yrs)
            span_end = S["by"] if S["by"] > hi else hi
            span_start = S["by"] if S["by"] < lo else lo
            limit = 26 if role == "mother" else 40
            if span_end - span_start > limit + 4:
                sg.append(sig(-1.0, "the children would then be born over %d years" % (span_end - span_start), "household"))
            elif lo - 3 <= S["by"] <= hi + 5:
                sg.append(sig(0.6, "born within the years of the candidate's other children (%d-%d)" % (lo, hi), "household"))
            if role == "mother":
                gaps = [abs(S["by"] - y) for y in yrs]
                if 0 in gaps:
                    sg.append(sig(-1.5, "another child was born the same year (twins, or not this mother)", "household"))
                elif 1 in gaps:
                    sg.append(sig(-0.4, "another child was born the year before or after", "household"))
        for k in sibs:
            K = ctx.P[k]
            if K["given"] and S["given"] and ctx.cat.same_full_name(S["given"], K["given"]):
                if K["dy"] is not None and not K["dye"] and S["by"] is not None and K["dy"] < S["by"]:
                    continue   # the earlier child of that name had died: families gave the name again
                known = K["dy"] is not None and not K["dye"]
                sg.append(sig(-1.0 if known else -0.4, "a sibling already bears the name %s%s" % (K["given"], " and was living at the birth" if known else ""), "namesake"))
                break
    # --- the household's surname, seen from the mother
    if role == "mother":
        husbands = [h for h in ctx.spouses(c) if ctx.P[h]["sex"] != "f"]
        if husbands and S["sur"]:
            rel = [ctx.cat.surname_relation(S["sur"], ctx.P[h]["sur"])[0] for h in husbands if ctx.P[h]["sur"]]
            if rel:
                if any(r in ("same-form", "catalogue", "fold") for r in rel):
                    sg.append(sig(1.2, "her husband bears this person's surname", "household"))
                elif all(r in ("different", "not-same") for r in rel):
                    sg.append(sig(-1.5, "her husband bears another surname", "household"))
    # --- named for a grandfather
    gf = ctx.P[C["father"]] if C["father"] in ctx.P and ctx.hide != c and C["father"] != ctx.hide else None
    if gf and S["given"] and gf["given"] and ctx.cat.same_full_name(S["given"], gf["given"]):
        sg.append(sig(0.5, "named like the candidate's father (a grandchild named for a grandfather)", "naming"))
    return sg, bl


def spouse_signals(ctx, s, c):
    S, C = ctx.P[s], ctx.P[c]
    sg, bl = [], []
    if c == s:
        return sg, ["is the person themself"]
    if S["sex"] != "u" and C["sex"] != "u" and S["sex"] == C["sex"]:
        sg.append(sig(-2.5, "is of the same recorded sex (a tree may guess sex from a given name)", "sex"))
    gap = year_gap(ctx, c, s)
    if gap:
        d = abs((gap[0] + gap[1]) / 2.0)
        wide = (gap[1] - gap[0]) > 8
        w = tent(d, [(0, 10, 1.0), (10.01, 15, .5), (15.01, 25, -.3), (25.01, 99, -1.2)]) * (0.5 if wide else 1.0)
        sg.append(sig(w, "born about %d years apart" % round(d), "dates"))
    else:
        sg.append(sig(0.3, "no usable birth year for one of them (neither for nor against)", "dates"))
    bs, bc = ctx.birth(s, True), ctx.birth(c, True)
    if bs and bc:
        lo = max(bs[0], bc[0]) + 17
        ds, dc = ctx.death(s), ctx.death(c)
        hi = min(ds[1] if ds else 9999, dc[1] if dc else 9999)
        if hi < lo:
            bl.append("one had died before the other was grown")
        elif hi - lo < 5 and hi < 9999 and ctx.birth(s) and ctx.birth(c):
            sg.append(sig(-1.0, "only %d years of adult lives overlap" % max(0, hi - lo), "dates"))
    s_pts = [t for t in ctx.points(s, include_children=False)]
    c_pts = ctx.points(c, include_children=True)
    year = (S["by"] + 25) if S["by"] is not None else None
    if year is not None:
        ps = place_signal(ctx, s_pts, c_pts, year, window=15)
        if ps:
            sg.append(ps)
    for sp in ctx.spouses(c):
        if sp != s:
            D = ctx.death(sp)
            if not D or (bs and D[1] > bs[0] + 18):
                sg.append(sig(-0.8, "the candidate already has a recorded spouse", "household"))
                break
    return sg, bl


def same_signals(ctx, a, b):
    """Score a pair as ONE person written twice."""
    A, B = ctx.P[a], ctx.P[b]
    sg, bl = [], []
    if a == b:
        return sg, ["is the same row"]
    if A["sex"] != "u" and B["sex"] != "u" and A["sex"] != B["sex"]:
        sg.append(sig(-3.0, "recorded as different sexes (a tree may guess sex from a given name)", "sex"))
    kind, why = ctx.cat.surname_relation(A["sur"], B["sur"])
    if kind == "not-same":
        bl.append(why)
    elif kind != "unknown":
        w = {"same-form": 2.0, "catalogue": 1.6, "fold": 1.2, "lead": .5, "case-by-case": 0.0, "different": -3.0}[kind]
        sg.append(sig(w, "surname: " + why, "surname"))
    kind, why = ctx.cat.given_relation(A["given"], B["given"])
    if kind != "unknown":
        w = {"identical": 2.0, "same-name": 1.4, "partial": .2, "shared-token": .8, "lead": .2, "different": -4.0}[kind]
        sg.append(sig(w, "given name: " + why, "given"))
        if kind == "different":
            bl.append("the given names are different")
    xa, xb = ctx.birth(a, True), ctx.birth(b, True)
    if xa and xb:
        dd = abs((xa[0] + xa[1]) / 2.0 - (xb[0] + xb[1]) / 2.0)
        if dd > (20 if (A["bye"] or B["bye"]) else 15):
            bl.append("born %d years apart" % round(dd))
    ba, bb = ctx.birth(a), ctx.birth(b)
    if ba and bb and not bl:
        d = abs((ba[0] + ba[1]) / 2.0 - (bb[0] + bb[1]) / 2.0)
        est = A["bye"] or B["bye"]
        if True:
            if est:
                w = tent(d, [(0, 3, 1.0), (3.01, 10, .3), (10.01, 20, -.8)])
            else:
                w = tent(d, [(0, 1, 2.0), (1.01, 3, 1.2), (3.01, 8, .2), (8.01, 15, -2.5)])
            sg.append(sig(w, "birth years %s apart" % (("%d" % round(d)) if d else "0"), "dates"))
    da, db = ctx.death(a), ctx.death(b)
    if da and db:
        d = abs(da[0] - db[0])
        sg.append(sig(1.5 if d <= 1 else (-2.5 if d > 3 else 0), "death years %d apart" % d, "dates"))
    for X, Y, other in ((a, b, "died before"), (b, a, "died before")):
        d, bth = ctx.death(X), ctx.birth(Y, True)
        if d and bth and d[1] < bth[0] - 1:
            bl.append("one %s the other was born" % other)
    pa = [t for t in ctx.points(a, False) if t[2] == "born"]
    pb = [t for t in ctx.points(b, False) if t[2] == "born"]
    if pa and pb:
        r, km = ctx.pl.relation(pa[0][0], pb[0][0])
        if r == "same":
            sg.append(sig(1.5, "born in the same place (%s)" % pa[0][0]["name"], "place"))
        elif r == "near":
            sg.append(sig(0.8, "birth places %d km apart" % round(km), "place"))
        elif r in ("far", "mid"):
            sg.append(sig(-2.0 if r == "far" else -0.6, "birth places %d km apart" % round(km), "place"))
    for role in ("father", "mother"):
        pa_, pb_ = A[role], B[role]
        if pa_ in ctx.P and pb_ in ctx.P and ctx.hide not in (a, b):
            if pa_ == pb_:
                sg.append(sig(3.0, "the same %s" % role, "relationship"))
            else:
                gk, _ = ctx.cat.given_relation(ctx.P[pa_]["given"], ctx.P[pb_]["given"])
                if gk in ("identical", "same-name", "shared-token"):
                    sg.append(sig(1.5, "the %s has the same given name in both" % role, "relationship"))
                elif gk == "different":
                    g = min(A["fg"] if role == "father" else A["mg"] or 0, 2)
                    sg.append(sig(-2.5 if g >= 2 else -1.0, "different %ss" % role, "relationship"))
                    if g >= 2:
                        bl.append("a register names a different %s" % role)
    sa, sb = set(ctx.spouses(a)), set(ctx.spouses(b))
    if sa and sb:
        if sa & sb:
            sg.append(sig(3.0, "the same spouse", "relationship"))
        else:
            sg.append(sig(-1.0, "different spouses recorded", "relationship"))
    if set(ctx.kids(a)) & set(ctx.kids(b)):
        sg.append(sig(3.0, "a child in common", "relationship"))
    return sg, bl


# ---------------------------------------------------------------- ranking and tiers
TIERS = {"strong": 6.0, "possible": 3.0}   # score floors; strong also needs a margin (see tier())
MARGIN = 1.0
NAMESAKE_TOP = 10   # the namesake count is worked out for the top of the list only


def tier(score, margin, thr=None):
    t = thr or TIERS
    if score >= t["strong"] and margin >= MARGIN:
        return "strong"
    if score >= t["possible"]:
        return "possible"
    return "weak"


def candidates_for(ctx, s, mode, pool=None):
    """The people who could be tried against `s`: eligible, not the person themself."""
    out = []
    for x in (pool if pool is not None else ctx.P):
        if x != s and ctx.eligible(x):
            out.append(x)
    return out


def rank(ctx, s, mode, kept_apart=None, thr=None, pool=None, top=None):
    """mode: 'father' | 'mother' | 'spouse' | 'same'. Returns {'subject','mode','candidates':[...], 'blocked':n, 'considered':n}.
    Each candidate: id, score, tier, margin, rivals, namesakes, signals (strongest first)."""
    if not ctx.eligible(s):
        return {"subject": s, "mode": mode, "candidates": [], "blocked": 0, "considered": 0, "skipped": "living or possibly living"}
    kept = kept_apart or set()
    rows, blocked, considered = [], 0, 0
    for c in candidates_for(ctx, s, mode, pool):
        if (s, c, mode) in kept or (c, s, mode) in kept or (s, c, "any") in kept or (c, s, "any") in kept:
            continue
        considered += 1
        if mode in ("father", "mother"):
            sg, bl = parent_signals(ctx, s, c, mode)
        elif mode == "spouse":
            sg, bl = spouse_signals(ctx, s, c)
        else:
            sg, bl = same_signals(ctx, s, c)
        if bl:
            blocked += 1
            continue
        rows.append({"id": c, "score": round(sum(x["w"] for x in sg), 2), "signals": sorted(sg, key=lambda x: -abs(x["w"]))})
    rows.sort(key=lambda r: (-r["score"], r["id"]))
    for i, r in enumerate(rows):
        nxt = rows[i + 1]["score"] if i + 1 < len(rows) else None
        prv = rows[i - 1]["score"] if i else None
        r["margin"] = round(r["score"] - nxt, 2) if nxt is not None else 99.0
        r["rivals"] = sum(1 for o in rows if o is not r and abs(o["score"] - r["score"]) <= 1.0)
        r["tier"] = tier(r["score"], r["margin"] if i == 0 else 0.0, thr)
    for r in rows[:NAMESAKE_TOP]:
        r["namesakes"] = _namesakes(ctx, r["id"], rows)
    if top:
        rows = rows[:top]
    return {"subject": s, "mode": mode, "candidates": rows, "blocked": blocked, "considered": considered}


def _namesakes(ctx, c, rows):
    """How many OTHER candidates carry the same name (given name family + surname) as `c`: the namesake trap."""
    C = ctx.P[c]
    n = 0
    for o in rows:
        if o["id"] == c:
            continue
        O = ctx.P[o["id"]]
        if ctx.cat.surname_relation(C["sur"], O["sur"])[0] in ("same-form", "catalogue", "fold") and \
                ctx.cat.same_full_name(C["given"], O["given"]):
            n += 1
    return n
