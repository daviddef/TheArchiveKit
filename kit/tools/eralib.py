"""The Python half of kit/lib/era.js: the same rules, for erasnap.py and checkera.py.

THE TWO HALVES MUST AGREE and nothing but the shared cases holds them together: kit/data/era-cases.json is run through
kit/lib/era.js by kit/tools/era_logic.mjs and through THIS file by kit/tools/era_selftest.py. Change a rule in one and the
other's run of the cases fails. See kit/docs/era-notes.md for what each rule is and why.
"""
import math
import re
import unicodedata

VERSION = 4
SRC_ATLAS = "per the Record Atlas"
SRC_OWN = "per this archive's own research"
PRE_NORMAL = "· At the time: "
PRE_BOUNDARY = "· From that year: "
RECENT_FROM = 1990
EDGE_KM = 15
MARGIN_YEARS = 5      # PROVISIONAL: the margin for an approx era whose contract carries none (erasnap.py --margin-years)
VALID_SILENT = ("edge", "marked-edge", "ring-conflict")
EDGE_KINDS = ("edge", "ring-conflict")
ERA_CSS_KEY = "kit:era-css"


def fold(s):
    """A place as it is compared: case, accents and apostrophes gone, every other run of punctuation and spaces one space."""
    s = unicodedata.normalize("NFKD", "" if s is None else str(s))
    s = "".join(c for c in s if not "̀" <= c <= "ͯ").lower()
    s = s.replace("'", "").replace("’", "").replace("`", "")
    out = []
    for c in s:
        out.append(c if unicodedata.category(c)[0] in ("L", "N") else " ")
    return " ".join("".join(out).split())


_MONTHS = ("(?:january|february|march|april|may|june|july|august|september|october|november|december|"
           "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)")
_PLAIN = re.compile(r"^(?:(?:\d{1,2}\s+)?" + _MONTHS + r"\.?\s+)?(\d{4})$", re.I)
_ISO = re.compile(r"^(\d{4})(?:-\d{2}(?:-\d{2})?)?$")


def is_year(n):
    return isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= 9999


def plain_year(date, year):
    """The year of an event, only where the page's own date is a plain one and agrees with the number held."""
    if not is_year(year) or not isinstance(date, str):
        return None
    s = " ".join(date.split())
    m = _PLAIN.match(s) or _ISO.match(s)
    if not m or int(m.group(1)) != year:
        return None
    return year


def era_id(region, frm):
    return "%s--era-%s" % (region, frm)


def _base(snap):
    base = ((snap or {}).get("atlas") or {}).get("base")
    if not isinstance(base, str):
        return None
    base = base.rstrip("/")
    return base if re.match(r"^https://[^/?#\s]+$", base, re.I) else None


def region_href(snap, region):
    b = _base(snap)
    if b and re.match(r"^[a-z0-9][a-z0-9-]*$", str(region)):
        return "%s/region/%s/" % (b, region)
    return None


def era_href(snap, region, e):
    """The link to the ERA: the contract's own `url`, accepted only if it is the path the id implies."""
    b = _base(snap)
    if not b or not isinstance(e, dict) or not isinstance(e.get("url"), str) or not re.match(r"^[a-z0-9][a-z0-9-]*$", str(region)):
        return None
    return b + e["url"] if e["url"] == "/region/%s/#era-%s" % (region, e.get("from")) else None


def _label(e):
    v = e.get("label")
    return v.strip() if isinstance(v, str) else ""


def is_open(e):
    """`to` is present and null: the era is still running. A MISSING `to` is not that (it is an era with no end year)."""
    return isinstance(e, dict) and "to" in e and e["to"] is None


def numeric(e):
    """A whole-number start, and either a later whole-number end or null (still running)."""
    if not isinstance(e, dict) or not is_year(e.get("from")):
        return False
    return is_open(e) or (is_year(e.get("to")) and e["from"] < e["to"])


def drop_ok(d):
    return isinstance(d, dict) and is_year(d.get("from")) and (is_open(d) or (is_year(d.get("to")) and d["from"] < d["to"]))


def covers(e, year):
    """from <= year < to; to null runs on."""
    return e["from"] <= year and (is_open(e) or year < e["to"])


def meets(a, b):
    inf = math.inf
    return a["from"] < (inf if is_open(b) else b["to"]) and b["from"] < (inf if is_open(a) else a["to"])


def flag(v):
    if v is True:
        return "yes"
    if v is False:
        return "no"
    return "unassessed" if v is None else "yes"


def is_margin(m):
    """A margin is a whole number of years >= 0 (rule l)."""
    return isinstance(m, int) and not isinstance(m, bool) and m >= 0


MARGIN_KINDS = ("approx", "contested", "both", "margin")
SCOPES = ("none", "bounds", "regime", "part")


def floor_of(pol):
    """N, the floor of every margin: the snapshot's policy.margin_years, else 5."""
    return pol["margin_years"] if isinstance(pol, dict) and is_margin(pol.get("margin_years")) else MARGIN_YEARS


def _reach(m, n, soft):
    return max(n, m) + (n if soft else 0) if is_margin(m) else None


def margin_span(e, n):
    """What the era's own margins allow (kit/lib/era.js marginSpan): {kind, first, last} (inclusive years; last None = still running),
    or None where the era is clean and carries no margin. A year must be MORE than max(N, margin) (+N where marginSourced is false)
    from each numeric bound."""
    ap, co = flag(e.get("approx")) == "yes", flag(e.get("contested")) == "yes"
    soft = e.get("margin_sourced") is False
    rf = _reach(e.get("from_margin"), n, soft)
    rt = None if is_open(e) else _reach(e.get("to_margin"), n, soft)
    if not ap and not co and rf is None and rt is None:
        return None
    return {"kind": "both" if ap and co else "approx" if ap else "contested" if co else "margin",
            "first": e["from"] + (rf + 1 if rf is not None and rf > 0 else 0), "last": None if is_open(e) else e["to"] - 1 - (rt if rt is not None else 0)}


def margin_gate(e, year, pol):
    """Usable in this year as far as flags, scope and margins go? None: yes. Else the reason: "approx" / "contested" (policy or scope
    refuses the era), "margin" (within the reach of a bound), "bad-margin" (the snapshot's record disagrees with the margins). Same as marginGate."""
    ap, co = flag(e.get("approx")), flag(e.get("contested"))
    if ap == "yes" and pol.get("approx") != "margin":
        return "approx"
    sc = e.get("contested_scope")
    if sc in ("regime", "part"):
        return "contested"
    if co == "yes":
        cp = pol.get("contested")
        if cp not in ("scope", "margin"):
            return "contested"
        # only "none" and "bounds" are used; no scope at all only under the explicit what-if policy "margin"
        if sc not in ("bounds", "none") and not (sc is None and cp == "margin"):
            return "contested"
    span = margin_span(e, floor_of(pol))
    if span is None:
        return None
    if (ap == "yes" or co == "yes") and not (is_margin(e.get("from_margin")) and (is_open(e) or is_margin(e.get("to_margin")))):
        return "approx" if ap == "yes" else "contested"
    r = e.get("margin_ok")
    if not isinstance(r, dict) or "last" not in r or r.get("kind") != span["kind"] or r.get("first") != span["first"] or r.get("last") != span["last"]:
        return "bad-margin"
    return None if year >= span["first"] and (span["last"] is None or year <= span["last"]) else "margin"


def _has_predecessor(snap, region, eras, e):
    if any(o is not e and numeric(o) and o.get("to") == e["from"] for o in eras):
        return True
    return any(drop_ok(d) and d.get("region") == region and d.get("to") == e["from"] for d in (snap.get("dropped") or []))


def _neighbour_agrees(snap, nb, year, mine, boundary, pol):
    """Rule j (kit/lib/era.js neighbourAgrees): the neighbouring region has, for this year, exactly one kept era that is not contested,
    approximate or overlapped, no refused era over the year, and the SAME label as the place's own era. Every doubt is a no."""
    regions = snap.get("regions")
    if not isinstance(nb, str) or not isinstance(regions, dict) or not isinstance(regions.get(nb), list):
        return False
    eras = regions[nb]
    dropped = [d for d in (snap.get("dropped") or []) if drop_ok(d) and d.get("region") == nb]
    if any(covers(d, year) for d in dropped):
        return False
    covering = [x for x in eras if numeric(x) and covers(x, year)]
    if len(covering) != 1:
        return False
    x = covering[0]
    if any(o is not x and numeric(o) and meets(x, o) for o in eras):
        return False
    if margin_gate(x, year, pol) is not None:
        return False
    if (flag(x.get("approx")) == "unassessed" or flag(x.get("contested")) == "unassessed") and pol.get("unassessed") != "allow":
        return False
    if _label(x) != _label(mine):
        return False
    if not boundary and year == x["from"]:
        if any(d.get("to") == year for d in dropped):
            return False
        before = [o for o in eras if o is not x and numeric(o) and o.get("to") == year]
        if not before or any(_label(o) != _label(mine) or flag(o.get("approx")) == "yes" or flag(o.get("contested")) == "yes" for o in before):
            return False
    return True


def _decide(snap, place, year, recent_from=None):
    def no(why):
        return {"why": why}

    if not isinstance(snap, dict) or snap.get("version") != VERSION:
        return no("snapshot")
    if not is_year(year):
        return no("year")
    if not isinstance(place, str) or not fold(place):
        return no("place")
    key = fold(place)
    silent = snap.get("places_silent")
    if isinstance(silent, dict) and silent.get(key) in VALID_SILENT:
        return no(silent[key])
    places = snap.get("places")
    if not isinstance(places, dict) or key not in places:
        return no("no-region")
    region = places[key]
    regions = snap.get("regions")
    if not isinstance(region, str) or not isinstance(regions, dict) or not isinstance(regions.get(region), list):
        return no("no-region")
    eras = regions[region]
    pol = snap.get("policy") if isinstance(snap.get("policy"), dict) else {}
    refused = [d for d in (snap.get("dropped") or []) if drop_ok(d) and d.get("region") == region and covers(d, year)]
    covering = [e for e in eras if numeric(e) and covers(e, year)]
    if not covering:
        return no("era-refused" if refused else "no-era")
    if len(covering) > 1 or refused or any(any(o is not e and numeric(o) and meets(e, o) for o in eras) for e in covering):
        return no("contested")
    e = covering[0]
    if recent_from is None:
        recent_from = pol["recent_from"] if is_year(pol.get("recent_from")) else RECENT_FROM
    if is_open(e) and year >= recent_from:
        return no("recent")
    boundary = False
    if year == e["from"] and _has_predecessor(snap, region, eras, e):
        if pol.get("boundary") != "newer":
            return no("boundary")
        boundary = True
    mg = margin_gate(e, year, pol)
    if mg is not None:
        return no(mg)
    unassessed = flag(e.get("approx")) == "unassessed" or flag(e.get("contested")) == "unassessed"
    if unassessed and pol.get("unassessed") != "allow":
        return no("unassessed")
    if not _label(e):
        return no("no-label")
    if e.get("id") != era_id(region, e["from"]):
        return no("bad-id")
    edge_agree = False
    en_all = snap.get("edge_neighbours")
    if isinstance(en_all, dict) and key in en_all:
        en = en_all[key]
        kind = en.get("kind") if isinstance(en, dict) and en.get("kind") in EDGE_KINDS else None
        lst = en.get("regions") if isinstance(en, dict) and isinstance(en.get("regions"), list) else []
        if kind is None or not lst or any(nb == region or not _neighbour_agrees(snap, nb, year, e, boundary, pol) for nb in lst):
            return no(kind or "edge")
        edge_agree = True
    return {"why": "ok", "region": region, "e": e, "boundary": boundary, "key": key, "unassessed": unassessed, "edge_agree": edge_agree}


def why_not(snap, place, year, recent_from=None):
    """Why a place and a year give no note, or "ok". Same reasons, same order as whyNot in era.js. recent_from overrides the
    snapshot's quiet-rule year (math.inf: off)."""
    return _decide(snap, place, year, recent_from)["why"]


def era_at(snap, place, year, recent_from=None):
    d = _decide(snap, place, year, recent_from)
    if d["why"] != "ok":
        return None
    region, e = d["region"], d["e"]
    seeded = e.get("seeded_from_archive") is True
    return {"region": region, "id": e["id"], "label": _label(e), "from": e["from"], "to": e.get("to"), "year": year,
            "source": SRC_OWN if seeded else SRC_ATLAS, "seeded": seeded, "href": era_href(snap, region, e),
            "boundary": d["boundary"], "unchecked": d["key"] in (snap.get("unchecked_edge") or []),
            "unassessed": d["unassessed"], "assessed": not d["unassessed"],
            "approx": flag(e.get("approx")) == "yes", "contested": flag(e.get("contested")) == "yes",
            "unsourced": e.get("margin_sourced") is False and margin_span(e, floor_of(snap.get("policy"))) is not None, "edgeAgree": d["edge_agree"], "basis": e.get("basis") if isinstance(e.get("basis"), str) else None}


# ---- geometry, shared by erasnap.py (the builder) ------------------------------------------------------------------------

def pip(lat, lon, ring):
    """Is the point inside the ring ([lat, lon] vertices)? Ray casting."""
    inside = False
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        if (a[1] > lon) != (b[1] > lon):
            x = a[0] + (lon - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if lat < x:
                inside = not inside
    return inside


def edge_km(lat, lon, ring):
    """Distance in km from the point to the nearest EDGE of the ring (inside or outside; the ring is a closed polygon whose edges are
    straight lines between [lat, lon] vertices). Flat local projection around the point (1 deg lat = 111.195 km, 1 deg lon =
    111.195 km x cos(lat)): a ring edge is hundreds of km at most and the question is whether the point is within ~15 km."""
    k = 111.195
    cl = math.cos(math.radians(lat))
    pts = [((p[1] - lon) * cl * k, (p[0] - lat) * k) for p in ring]
    best = math.inf
    for i in range(len(pts)):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L2))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best
