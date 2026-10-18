"""The Python half of kit/lib/era.js: the same rules, for erasnap.py and checkera.py.

THE TWO HALVES MUST AGREE and nothing but the shared cases holds them together: kit/data/era-cases.json is run through
kit/lib/era.js by kit/tools/era_logic.mjs and through THIS file by kit/tools/era_selftest.py. Change a rule in one and the
other's run of the cases fails. See kit/docs/era-notes.md for what each rule is and why.
"""
import re
import unicodedata

VERSION = 1
SRC_ATLAS = "per the Record Atlas"
SRC_OWN = "per this archive's own research"


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
    return "%s--%s" % (region, frm)


def region_href(snap, region):
    base = ((snap or {}).get("atlas") or {}).get("base")
    if not isinstance(base, str):
        return None
    base = base.rstrip("/")
    if re.match(r"^https://[^/?#\s]+$", base, re.I) and re.match(r"^[a-z0-9][a-z0-9-]*$", str(region)):
        return "%s/region/%s/" % (base, region)
    return None


def _label(snap, e):
    regimes = snap.get("regimes")
    r = e.get("regime")
    if not isinstance(regimes, dict) or not isinstance(r, str) or r not in regimes:
        return ""
    v = regimes[r]
    return v.strip() if isinstance(v, str) else ""


def numeric(e):
    return isinstance(e, dict) and is_year(e.get("from")) and is_year(e.get("to")) and e["from"] < e["to"]


def why_not(snap, place, year):
    """Why a place and a year give no note, or "ok". Same reasons, same order as whyNot in era.js."""
    if not isinstance(snap, dict) or snap.get("version") != VERSION:
        return "snapshot"
    if not is_year(year):
        return "year"
    if not isinstance(place, str) or not fold(place):
        return "place"
    key = fold(place)
    places = snap.get("places")
    if not isinstance(places, dict) or key not in places:
        return "no-region"
    region = places[key]
    regions = snap.get("regions")
    if not isinstance(region, str) or not isinstance(regions, dict) or not isinstance(regions.get(region), list):
        return "no-region"
    eras = regions[region]
    touching = [e for e in eras if numeric(e) and e["from"] <= year <= e["to"]]
    if not touching:
        refused = any(isinstance(d, dict) and d.get("region") == region and is_year(d.get("from")) and is_year(d.get("to"))
                      and d["from"] <= year <= d["to"] for d in (snap.get("dropped") or []))
        return "era-refused" if refused else "no-era"

    def overlapped(e):
        return any(o is not e and numeric(o) and o["from"] < e["to"] and e["from"] < o["to"] for o in eras)

    inside = [e for e in touching if e["from"] < year < e["to"]]
    if len(inside) > 1 or any(e.get("contested") is True or overlapped(e) for e in touching):
        return "contested"
    if not inside:
        return "boundary"
    e = inside[0]
    if "approx" in e and e["approx"] is not False:
        return "approx"
    if "contested" in e and e["contested"] is not False:
        return "contested"
    if not _label(snap, e):
        return "no-label"
    return "ok"


def era_at(snap, place, year):
    if why_not(snap, place, year) != "ok":
        return None
    region = snap["places"][fold(place)]
    e = next(x for x in snap["regions"][region] if numeric(x) and x["from"] < year < x["to"])
    seeded = e.get("seeded_from_archive") is True
    return {"region": region, "id": era_id(region, e["from"]), "label": _label(snap, e), "from": e["from"], "to": e["to"],
            "year": year, "source": SRC_OWN if seeded else SRC_ATLAS, "seeded": seeded, "href": region_href(snap, region)}
