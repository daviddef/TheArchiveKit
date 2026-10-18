#!/usr/bin/env python3
"""Build the era snapshot an archive keeps: the Record Atlas's versioned context contract, cut down to what a note may say, committed.

WHY A SNAPSHOT. The sites are static and the Atlas's files change daily. A note that fetched the Atlas at build time would
make the same page say different things on different days, and a note an archive cannot reproduce is a claim it cannot stand
behind. So the archive commits `era-snapshot.json`, refreshes it by running THIS, deliberately, and reviews the diff. Nothing
in a build ever reads the Atlas. kit/lib/era.js reads the snapshot; kit/tools/checkera.py holds the built pages to it.

    python3 erasnap.py --contract <Record Atlas>/site/public/context.json --places era-places.json --out era-snapshot.json
    python3 erasnap.py ... --check          # rebuild in memory and compare with --out (ignores `built`); exit 1 if it differs
    python3 erasnap.py ... --report drops.json      # also write, per region, the eras refused and why (counts, for the Atlas)

THE CONTRACT is https://recordatlas.org/context.json (documented at /data/#context): region eras with a permanent id
(`<region>--era-<from>`), a half-open interval (from <= year < to; `to` null = still running), a display label (`regimeLabel`),
a `basis` (where the region's bands came from), `contested` and `approx` (null = nobody has assessed it; false = looked at and
clean; true carries a `why`), and a `quality` block listing gaps and overlaps. It is read as the SOURCE: the snapshot records its
version, its `generated` stamp and the sha256 of the file's bytes. Major version 1 only; any other is refused (a renamed field is
what a major version is for).

THE RINGS are in the contract from 1.8.0: each region carries `ring` ([lat, lon] vertices, approximate by design) and `bbox`
([south, west, north, east]). They are read from there by default (atlas.rings_source = "contract"), the bbox is held to the ring
(a bbox that is not the ring's extent stops the build), and a contract older than 1.8.0 is refused unless the rings are given.
`--rings <file>` is an optional OVERRIDE (the Atlas's regions.json: its ring and its `regimes.existed` dates, which the contract
does not carry, so the "era outside the dates the Atlas holds for its regime" refusal runs only with it); the file must describe the
same regions and eras as the contract, and the snapshot records atlas.rings_source = "file" and the file's sha256. `--no-rings`
says so explicitly: no place is edge-checked, and all are counted unchecked.

THE PLACE TABLE is the ARCHIVE's, never the Atlas's: a JSON object (or {"places": {...}}) from a place exactly as the archive
prints it to a region id, either `"Briatico, Vibo Valentia, Calabria": "calabria"` or an entry with coordinates the archive holds
`"...": {"region": "calabria", "lat": 38.72, "lon": 16.03}`, and optionally `"edge": true` (the archive says this place is on the
edge of its region: it gets no note). A null region (or "-") says "looked at, and no region covers it". A place is folded
(kit/lib/era.js fold) to a key, so spellings that differ only in case, accents or punctuation are one place.

THE EDGE RULE. The rings are 4-11 vertex shapes, "approximate by design". With coordinates, a place is NEAR AN EDGE if it is
within --edge-km (default 15) of its own region's ring edge (inside or outside), and is IN CONFLICT if it is inside another
region's ring and not its own. Such a place may belong to a NEIGHBOUR: the regions (other than its own) whose ring contains it or
lies within --edge-km of it. With `--edge agree` (the default) the place is kept, with those neighbours recorded
(edge_neighbours: {kind: "edge"|"ring-conflict", regions: [...]}), and the library keeps the note only in a year when every
neighbour has the SAME regime label as the place's own era (kit/lib/era.js, rule j); anything unknown is silence. A near-edge place
with NO neighbour to compare, or when some region of the contract has no usable ring (so the neighbours cannot be known), is refused
as before ("edge" / "ring-conflict" in places_silent). `--edge strict` is the old rule for every near-edge place.
  - a point outside its own ring, more than --edge-km from it and not inside another's ring, is kept (the archive's table is its
    own statement) unless --outside-ring refuse, and is counted;
  - a place with no coordinates cannot be checked: it is kept, listed in `unchecked_edge`, and counted.
  - a place the table marks edge is refused ("marked-edge").
Refused places are listed in `places_silent` so an archive can count them; they get no note.

WHAT IT REFUSES, and counts (rule b, g; kit/docs/era-notes.md); an era refused is listed in `dropped` with its reason
  words-only or non-numeric start; an end that is neither a year nor null; an open end on an era not marked present; a start not
    before its end; an id or url that is not the one the region and start imply
  a regime without a label; a regime the Atlas itself calls "this project's own shorthand for a situation rather than the name of
    a state" (`feudal`, `german`: --refuse-regimes); a regime that is a bare shorthand ("Napoleonic": --qualify-regimes) on an
    era that has no polity to qualify it; an era outside the dates the ring file holds for its regime (`existed`)
  an era the contract's quality block lists in a gap or an overlap
  an era the contract marks approximate (true) under --approx refuse; contested (true) under --contested refuse, or whose contestedScope is
    regime or part (or, without --contested margin, absent); an era with a margin that is null (unknowable) or not a whole number of years;
    an era flagged true with no margin to hold the year to (a contested era from a contract with no margin fields); and, unless
    --unassessed allow, one it has not assessed (null). RULE L (kit/docs/era-notes.md): an approx era, or a contested one about its
    bounds (contestedScope none or bounds), is KEPT with from_margin / to_margin / margin_sourced / margin_src / contested_scope and
    the recorded decision margin_ok, and the library uses it only for a year MORE than max(N, margin) from each numeric bound
    (N = --margin-years, default 5; N more where marginSourced is false). A contract before 1.10.0 has no margin fields: an approx
    era then gets margin 0 and margin_src "fallback" (the floor N alone: PROVISIONAL, not an Atlas fact). --margins widens, never narrows.
    An era is ASSESSED when neither flag is null; the snapshot carries `assessed` and the contract's `why` on every kept era, the
    note says whether it rests on an assessed era (data-era-assessed) and the gate counts both. In contract 1.7.0 every region era was
    null; from 1.8.0 some regions are assessed. --unassessed allow is a deliberate choice an archive makes, recorded in the
    snapshot's policy, printed by the gate, and refused by the gate's --strict-unassessed.
It KEEPS BOTH eras of any pair of eras of one region that overlap (it does not flag them; era.js stays silent about every year they
touch). The display label is the contract's regimeLabel; for a --qualify-regimes regime (default napo) it is the era's polity
(when that already begins with the label) or "<label> - <polity>", never invented.
A region whose `basis` begins "seeded:" (the Atlas took its bands from this estate's own research) carries seeded_from_archive true
on every era, so a note says "per this archive's own research" and does not pretend the Atlas is a second source.
The boundary policy comes from the contract's own `rule` text: "newer" only if it says a year equal to a boundary belongs to the
newer era; otherwise "silent". --boundary silent can make it stricter, never looser.

THE RULERS (rule m; contract 1.11.0 and later, today for one region). A region the contract marks `hasRulers: true` carries `rulers`, one row per
reign: `name` (the Atlas's own words), `polityId` (a stable slug), `from` / `to` as the source states them, numeric `fromYear` / `toYear`
(`toYear` null: the reign goes on), `fromMargin` / `toMargin` (0 where a page gives a day, 1 where only a year), `marginWhy`, `q` (a
Wikidata id or null) and `source`. They are carried into the snapshot under `rulers[<region>]` = {has, why, reigns}, for the regions the
snapshot holds: `has` is true only where the contract says so AND every row is usable (a name, a slug, whole-number years, whole-number
margins; a margin that is null is unknowable). One unusable row refuses the whole region's rulers (the row may be the one that overlaps a
year); `why` then says so. `hasRulers` false, or a contract that has no such field (before 1.11.0), is `has` false / null: a missing field is
never read as "none". The row's `note` and `language` are not carried (the language of administration is not used). The snapshot's policy
carries `ruler_polities` {regime id: [polityId]}: which polities an era of that regime may name a ruler of (default RULER_POLITIES below:
twosicilies and italy only; `--ruler-polities <file>` replaces it). A regime not in the table gets no ruler.

Prints counts only; never a place or a person.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eralib  # noqa: E402

DEFAULT_REFUSE = "feudal,german"
DEFAULT_QUALIFY = "napo"
DEFAULT_BASE = "https://recordatlas.org"
CONTRACT_NAME = "recordatlas-context"
# Which polities (the Atlas's polityId slugs on a reign) an era of a regime may name a ruler of. Only the regimes whose label IS one polity
# or the unbroken line of two (Italy: the Kingdom, then the Republic); an era of any other regime (the shorthand "Napoleonic", a regime the
# Atlas files several states under) gets no ruler. An archive replaces it with --ruler-polities, on the record.
RULER_POLITIES = {"twosicilies": ["kingdom-of-the-two-sicilies"], "italy": ["kingdom-of-italy", "italian-republic"]}

R_START = "start is words-only or not a year"
R_END = "end is neither a year nor null"
R_OPEN = "open end on an era not marked present"
R_ORDER = "start not before end"
R_ID = "id or url is not the one the region and start imply"
R_NOLABEL = "regime has no label"
R_SHORT = "regime is the project's own shorthand, not a state"
R_NOPOLITY = "bare shorthand regime with no polity to qualify it"
R_EXISTED = "era outside the dates the Atlas holds for its regime"
R_GAP = "listed in the contract's quality gaps"
R_OVERLAP = "listed in the contract's quality overlaps"
R_APPROX = "marked approximate (true)"
R_CONTESTED = "marked contested (true)"
R_CSCOPE = "contested about its regime or a part, not its bounds only (contestedScope)"
R_CNOSCOPE = "contested (true) with no contestedScope in the contract"
R_NOMARGIN = "flagged approximate or contested with no margin to hold the year to"
R_MARGINNULL = "a bound whose margin is unknowable (null) or not a whole number of years"
R_UNASSESSED = "contested or approx not assessed (null)"


def load_json_bytes(path):
    raw = open(path, "rb").read()
    return raw, json.loads(raw)


def check_contract(doc):
    """Returns (version, boundary policy). Raises SystemExit(2) on anything this builder must not read."""
    c = doc.get("contract") if isinstance(doc, dict) else None
    if not isinstance(c, dict) or c.get("name") != CONTRACT_NAME:
        raise SystemExit("erasnap: this is not a Record Atlas context contract (contract.name must be %r)" % CONTRACT_NAME)
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(c.get("version")))
    if not m or int(m.group(1)) != 1:
        print("erasnap: contract version %r: this builder reads major version 1 only (a changed major version means a renamed field "
              "or a changed rule: read the Atlas's /data/#context and update the builder)" % c.get("version"), file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(doc.get("generated"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", doc["generated"]):
        raise SystemExit("erasnap: the contract has no `generated` date")
    rule = doc.get("rule")
    if not isinstance(rule, str) or "from <= year < to" not in rule:
        print("erasnap: the contract's `rule` does not state the half-open interval (from <= year < to): the lookup would be a guess", file=sys.stderr)
        raise SystemExit(2)
    boundary = "newer" if "belongs to the newer era" in rule else "silent"
    if not isinstance(doc.get("regions"), list) or not isinstance(doc.get("quality"), dict):
        raise SystemExit("erasnap: the contract has no regions list or no quality block")
    return c["version"], boundary


def _valid_ring(ring):
    return (isinstance(ring, list) and len(ring) >= 3
            and all(isinstance(p, list) and len(p) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in p) for p in ring))


def _extent(ring):
    return [min(p[0] for p in ring), min(p[1] for p in ring), max(p[0] for p in ring), max(p[1] for p in ring)]


def contract_rings(doc, version):
    """The rings the contract carries (1.8.0 and later): each region's `ring` and `bbox`. The bbox must be the ring's own extent
    ([south, west, north, east]) or the contract contradicts itself and the build stops. -> {region: ring}."""
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(version))
    if (int(m.group(1)), int(m.group(2))) < (1, 8):
        print("erasnap: contract %s carries no rings (1.8.0 added them): give --rings <the Atlas's regions.json> or --no-rings" % version, file=sys.stderr)
        raise SystemExit(2)
    rings, off = {}, 0
    for r in doc["regions"]:
        ring, bbox = r.get("ring"), r.get("bbox")
        if not _valid_ring(ring):
            continue
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(x, (int, float)) for x in bbox)
                and all(abs(x - y) < 1e-6 for x, y in zip(bbox, _extent(ring)))):
            off += 1
            continue
        rings[r["id"]] = ring
    if off:
        print("erasnap: %d region(s) of the contract carry a bbox that is not their ring's extent: the contract contradicts itself, "
              "so no ring is trusted (tell the Atlas)" % off, file=sys.stderr)
        raise SystemExit(2)
    return rings


def check_rings(contract, rings_doc):
    """The OVERRIDE ring file must describe the contract's regions and eras. -> ({region: ring}, regimes)."""
    rings = {}
    rr = {r["id"]: r for r in rings_doc.get("regions") or []}
    cr = {r["id"]: r for r in contract["regions"]}
    if set(rr) != set(cr):
        print("erasnap: the ring file and the contract describe different regions (%d only in the ring file, %d only in the contract): "
              "they must come from the same Atlas build" % (len(set(rr) - set(cr)), len(set(cr) - set(rr))), file=sys.stderr)
        raise SystemExit(2)
    for rid, r in rr.items():
        a = sorted(e.get("from") for e in r.get("eras") or [])
        b = sorted(e.get("from") for e in cr[rid].get("eras") or [])
        if a != b:
            print("erasnap: the ring file and the contract disagree about the eras of %d region(s): they must come from the same Atlas build"
                  % sum(1 for k in rr if sorted(e.get("from") for e in rr[k].get("eras") or []) != sorted(e.get("from") for e in cr[k].get("eras") or [])),
                  file=sys.stderr)
            raise SystemExit(2)
        if _valid_ring(r.get("ring")):
            rings[rid] = r["ring"]
    return rings, rings_doc.get("regimes") or {}


def load_table(path):
    j = json.load(open(path, encoding="utf-8"))
    if isinstance(j, dict) and isinstance(j.get("places"), dict):
        j = j["places"]
    if not isinstance(j, dict):
        raise SystemExit("erasnap: the place table must be a JSON object of place -> region")
    out = {}
    for k, v in j.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            out[k] = (v.get("region"), v.get("lat"), v.get("lon"), v.get("edge") is True)
        else:
            out[k] = (v, None, None, False)
    return out


def quality_ids(q):
    gaps, overlaps = set(), set()
    for row in q.get("gaps") or []:
        gaps.update(x for x in (row.get("from"), row.get("to")) if isinstance(x, str))
    for row in q.get("overlaps") or []:
        overlaps.update(x for x in (row.get("from"), row.get("to")) if isinstance(x, str))
    return gaps, overlaps


def _margin(v):
    """A contract margin: a whole number of years >= 0, else None (absent or unusable: it is then NOT a margin)."""
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None


def load_margins(path):
    """The archive's own wider margins, {era id: years | {"from": n, "to": n}}. -> {era id: (from, to)} (a side may be None)."""
    if not path:
        return {}
    j = json.load(open(path, encoding="utf-8"))
    if isinstance(j, dict) and isinstance(j.get("margins"), dict):
        j = j["margins"]
    if not isinstance(j, dict):
        raise SystemExit("erasnap: --margins must be a JSON object of era id -> years")
    out = {}
    for k, v in j.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            pair = (_margin(v.get("from")), _margin(v.get("to")))
        else:
            pair = (_margin(v), _margin(v))
        if pair == (None, None):
            raise SystemExit("erasnap: --margins: %r is not a number of years" % k)
        out[k] = pair
    return out


def resolve_margin(e, frm, to, ap, co, scope, a, override):
    """-> (from_margin, to_margin, margin_src, margin_sourced), or the string R_MARGINNULL.
    The contract (1.10.0 and later) carries fromMargin/toMargin on every era: a whole number is the margin, 0 means the sources agree on one
    year, null means the bound is UNKNOWABLE and the era is refused (a bound that is not a whole number of years is no better). The end of an era
    still running is no bound. The archive may only WIDEN a margin (--margins). A contract with NO margin fields (before 1.10.0) gives an approx
    era margin 0 on each side with margin_src "fallback" (only the floor N of the library then holds it: PROVISIONAL, not an Atlas fact), and,
    only under --contested margin, a contested era with no scope the same; any other era has none. marginSourced false (on the era) makes the margin
    softer in the library (N more), and is carried."""
    has_keys = "fromMargin" in e or "toMargin" in e
    sides, src = [], []
    for i, key in enumerate(("fromMargin", "toMargin")):
        o = (override or (None, None))[i]
        if i == 1 and to is None:
            sides.append(None)
            continue
        if has_keys:
            c = _margin(e.get(key))
            if c is None:
                return R_MARGINNULL
            v, s_ = (o, "archive") if o is not None and o > c else (c, "contract")
        elif o is not None:
            v, s_ = o, "archive"
        elif (ap is True and a.approx == "margin") or (co is True and a.contested == "margin" and scope is None):
            v, s_ = 0, "fallback"
        else:
            v, s_ = None, None
        sides.append(v)
        if s_:
            src.append(s_)
    rank = {"contract": 0, "archive": 1, "fallback": 2}
    ms = e.get("marginSourced") if isinstance(e.get("marginSourced"), bool) and has_keys else None
    return sides[0], sides[1], (max(src, key=rank.get) if src else None), ms


def load_ruler_polities(path):
    """{regime id: [polityId]} from --ruler-polities, or the kit's default."""
    if not path:
        return {k: list(v) for k, v in RULER_POLITIES.items()}
    j = json.load(open(path, encoding="utf-8"))
    if isinstance(j, dict) and isinstance(j.get("ruler_polities"), dict):
        j = j["ruler_polities"]
    if not isinstance(j, dict) or not all(isinstance(k, str) and isinstance(v, list) and v and all(isinstance(x, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", x) for x in v)
                                          for k, v in j.items() if not k.startswith("_")):
        raise SystemExit("erasnap: --ruler-polities must be a JSON object of regime id -> a list of polityId slugs")
    return {k: list(v) for k, v in sorted(j.items()) if not k.startswith("_")}


def region_rulers(r):
    """The contract's rulers for one region -> the snapshot's {has, why, reigns} (rule m). has is true only if the contract says hasRulers: true
    and every row is usable; otherwise why says what stopped it. A missing field is never read as none: has null says the contract is silent."""
    has = r.get("hasRulers")
    if has is None and "hasRulers" not in r:
        return {"has": None, "why": "the contract has no hasRulers for this region", "reigns": []}
    if has is not True:
        return {"has": False, "why": "the contract says the region has no rulers", "reigns": []}
    rows = r.get("rulers")
    if not isinstance(rows, list) or not rows:
        return {"has": False, "why": "hasRulers is true but the contract carries no reigns", "reigns": []}
    reigns = []
    for row in rows:
        if not isinstance(row, dict):
            return {"has": False, "why": "a reign row that is not an object", "reigns": []}
        ty = row.get("toYear")
        q = row.get("q")
        out = {"name": row.get("name"), "polity_id": row.get("polityId"), "from": row.get("from") if isinstance(row.get("from"), str) else None,
               "to": row.get("to") if isinstance(row.get("to"), str) else None, "from_year": row.get("fromYear"), "to_year": ty,
               "from_margin": _margin(row.get("fromMargin")), "to_margin": _margin(row.get("toMargin")),
               "margin_why": row.get("marginWhy") if isinstance(row.get("marginWhy"), str) else None,
               "q": q if isinstance(q, str) and re.fullmatch(r"Q\d+", q) else None,
               "source": row.get("source") if isinstance(row.get("source"), str) else None}
        # the numeric years must follow the dates as the source states them, and an end must be stated either way: a closed reign with no
        # toYear would otherwise read as a reign that goes on for ever
        fs, ts = row.get("from"), row.get("to")
        consistent = ("toYear" in row and isinstance(fs, str) and str(row.get("fromYear")) == fs[:4]
                      and ((ts is None and ty is None) or (isinstance(ts, str) and ty is not None and str(ty) == ts[:4])))
        if not consistent or not eralib.reign_ok(out):
            return {"has": False, "why": "a reign row the library cannot read (a name, a polityId slug, whole-number years that follow the dates stated, and whole-number margins are needed; a null margin is unknowable)", "reigns": []}
        reigns.append(out)
    return {"has": True, "why": None, "reigns": reigns}


def display_label(era, regime_label, qualify):
    """The contract's regimeLabel, or, for a bare-shorthand regime, the label with the era's own polity (never invented)."""
    lab = regime_label.strip()
    if era.get("regime") not in qualify:
        return lab, None
    pol = era.get("polity")
    if not isinstance(pol, str) or not pol.strip():
        return None, R_NOPOLITY
    pol = pol.strip()
    return (pol if pol.lower().startswith(lab.lower()) else "%s — %s" % (lab, pol)), None


def build(contract_path, rings_path, table_path, a, built):
    raw, doc = load_json_bytes(contract_path)
    version, rule_boundary = check_contract(doc)
    boundary = rule_boundary
    if a.boundary == "silent":
        boundary = "silent"
    elif a.boundary == "newer" and rule_boundary != "newer":
        raise SystemExit("erasnap: --boundary newer, but the contract's own rule does not say a boundary year belongs to the newer era")
    split = lambda s: {x.strip() for x in s.split(",") if x.strip()}
    refuse, qualify = split(a.refuse_regimes), split(a.qualify_regimes)
    rings, rregimes, rings_sha, rings_source = {}, {}, None, "none"
    differ = 0
    if rings_path:
        rraw, rdoc = load_json_bytes(rings_path)
        rings, rregimes = check_rings(doc, rdoc)
        rings_sha, rings_source = hashlib.sha256(rraw).hexdigest(), "file"
        differ = sum(1 for r in doc["regions"] if _valid_ring(r.get("ring")) and r.get("ring") != rings.get(r["id"]))
    elif not a.no_rings:
        rings, rings_source = contract_rings(doc, version), "contract"
    all_rings = bool(rings) and all(r["id"] in rings for r in doc["regions"])
    gap_ids, overlap_ids = quality_ids(doc["quality"])
    overrides = load_margins(a.margins)
    ruler_polities = load_ruler_polities(a.ruler_polities)

    stats = {"eras_in": 0, "eras_kept": 0, "eras_kept_assessed": 0, "eras_kept_unassessed": 0, "eras_overlapping_another_kept_era": 0,
             "eras_kept_flagged": 0, "eras_kept_flagged_by_fallback": 0, "eras_kept_with_unsourced_margin": 0}
    drop_by_reason = {}
    drop_by_region = {}
    dropped = []

    def drop(rid, e, why):
        drop_by_reason[why] = drop_by_reason.get(why, 0) + 1
        drop_by_region.setdefault(rid, {})
        drop_by_region[rid][why] = drop_by_region[rid].get(why, 0) + 1
        dropped.append({"region": rid, "id": e.get("id"), "from": e.get("from"), "to": e.get("to"), "reason": why})

    regions = {}
    for r in doc["regions"]:
        rid = r["id"]
        kept = []
        for e in r.get("eras") or []:
            stats["eras_in"] += 1
            frm, to = e.get("from"), e.get("to")
            if not eralib.is_year(frm):
                drop(rid, e, R_START)
                continue
            if to is not None and not eralib.is_year(to):
                drop(rid, e, R_END)
                continue
            if to is None and e.get("present") is not True:
                drop(rid, e, R_OPEN)
                continue
            if to is not None and not frm < to:
                drop(rid, e, R_ORDER)
                continue
            if e.get("id") != eralib.era_id(rid, frm) or e.get("url") != "/region/%s/#era-%s" % (rid, frm):
                drop(rid, e, R_ID)
                continue
            reg = e.get("regime")
            rl = e.get("regimeLabel")
            if not isinstance(rl, str) or not rl.strip():
                drop(rid, e, R_NOLABEL)
                continue
            if reg in refuse:
                drop(rid, e, R_SHORT)
                continue
            lab, why = display_label(e, rl, qualify)
            if why:
                drop(rid, e, why)
                continue
            ex = (rregimes.get(reg) or {}).get("existed")
            if isinstance(ex, list) and len(ex) == 2 and all(isinstance(x, int) for x in ex):
                if not (ex[0] <= frm and (to is None or to <= ex[1])):
                    drop(rid, e, R_EXISTED)
                    continue
            if e["id"] in gap_ids:
                drop(rid, e, R_GAP)
                continue
            if e["id"] in overlap_ids:
                drop(rid, e, R_OVERLAP)
                continue
            ap, co = e.get("approx"), e.get("contested")
            scope = e.get("contestedScope") if isinstance(e.get("contestedScope"), str) else None
            if ap is True and a.approx != "margin":
                drop(rid, e, R_APPROX)
                continue
            if scope in ("regime", "part") or (scope is not None and scope not in eralib.SCOPES):
                drop(rid, e, R_CSCOPE)
                continue
            if co is True:
                if a.contested == "refuse":
                    drop(rid, e, R_CONTESTED)
                    continue
                if scope is None and a.contested != "margin":
                    drop(rid, e, R_CNOSCOPE)
                    continue
            if (ap is not True and ap is not False) or (co is not True and co is not False):
                if a.unassessed != "allow":
                    drop(rid, e, R_UNASSESSED)
                    continue
            rm = resolve_margin(e, frm, to, ap, co, scope, a, overrides.get(e["id"]))
            if rm == R_MARGINNULL:
                drop(rid, e, R_MARGINNULL)
                continue
            fm, tm, msrc, msd = rm
            flagged = ap is True or co is True
            if flagged and (fm is None or (to is not None and tm is None)):
                drop(rid, e, R_NOMARGIN)
                continue
            basis = e.get("basis") if isinstance(e.get("basis"), str) else "not-recorded"
            why_text = e.get("why") if isinstance(e.get("why"), str) and e["why"].strip() else None
            kept.append({"id": e["id"], "from": frm, "to": to, "present": to is None, "regime": reg, "label": lab,
                         "polity": e.get("polity") if isinstance(e.get("polity"), str) else None, "basis": basis,
                         "seeded_from_archive": basis.startswith("seeded:"), "approx": ap, "contested": co,
                         "assessed": ap is not None and co is not None, "why": why_text, "url": e["url"],
                         "from_margin": fm, "to_margin": tm, "margin_src": msrc, "margin_sourced": msd, "contested_scope": scope})
            span = eralib.margin_span(kept[-1], a.margin_years)
            kept[-1]["margin_ok"] = span
            if msd is False and span is not None:
                stats["eras_kept_with_unsourced_margin"] += 1
            if flagged:
                stats["eras_kept_flagged"] += 1
                stats["eras_kept_flagged_by_fallback"] += 1 if msrc == "fallback" else 0
        stats["eras_kept"] += len(kept)
        stats["eras_overlapping_another_kept_era"] += sum(1 for x in kept if any(y is not x and eralib.meets(x, y) for y in kept))
        stats["eras_kept_assessed"] += sum(1 for x in kept if x["assessed"])
        stats["eras_kept_unassessed"] += sum(1 for x in kept if not x["assessed"])
        regions[rid] = kept

    table = load_table(table_path)
    results = {}          # key -> ("ok", region, unchecked, kind|None, [neighbours]) | ("silent", why)
    pstat = {"places_in": len(table), "places_kept": 0, "places_unmapped": 0, "places_refused_ring_conflict": 0,
             "places_refused_edge": 0, "places_refused_marked_edge": 0, "places_outside_own_ring_kept": 0,
             "places_outside_own_ring_refused": 0, "places_unchecked_no_coordinates": 0, "places_edge_kept_with_neighbours": 0}
    for name, (rid, lat, lon, marked) in sorted(table.items()):
        key = eralib.fold(name)
        if not key:
            raise SystemExit("erasnap: a place in the table folds to nothing")
        if rid in (None, "", "-"):
            pstat["places_unmapped"] += 1
            continue
        if rid not in regions:
            raise SystemExit("erasnap: the table sends a place to region %r, which the contract does not hold" % rid)
        res = None
        if marked:
            res = ("silent", "marked-edge")
        elif isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and not isinstance(lat, bool) and rid in rings:
            mine = eralib.pip(lat, lon, rings[rid])
            inside = sorted(o for o, ring in rings.items() if o != rid and eralib.pip(lat, lon, ring))
            dist = eralib.edge_km(lat, lon, rings[rid])
            conflict = not mine and bool(inside)
            if conflict or dist <= a.edge_km:
                kind = "ring-conflict" if conflict else "edge"
                near = sorted(o for o, ring in rings.items() if o != rid and (o in inside or eralib.edge_km(lat, lon, ring) <= a.edge_km))
                if a.edge == "agree" and all_rings and near:
                    res = ("ok", rid, False, kind, near)
                else:
                    res = ("silent", kind)
            elif not mine and a.outside_ring == "refuse":
                res = ("silent", "ring-conflict")
                pstat["places_outside_own_ring_refused"] += 1
            else:
                res = ("ok", rid, False, None, [])
                if not mine:
                    pstat["places_outside_own_ring_kept"] += 1
        else:
            res = ("ok", rid, True, None, [])
        prev = results.get(key)
        if prev is not None and prev != res:
            if prev[0] == "ok" and res[0] == "ok" and prev[1] != res[1]:
                raise SystemExit("erasnap: two places that fold to one key are sent to different regions")
            if prev[0] == "ok" and res[0] == "ok":
                # the same place twice (coordinates on one spelling, or two sets of them): it is checked if either was, and every neighbour either has is kept
                kind = "ring-conflict" if "ring-conflict" in (prev[3], res[3]) else (prev[3] or res[3])
                res = ("ok", prev[1], prev[2] and res[2], kind, sorted(set(prev[4]) | set(res[4])))
            else:
                res = prev if prev[0] == "silent" else res        # a refusal wins over a keep
        results[key] = res
    places, silent, unchecked, edge_nb = {}, {}, [], {}
    for key, res in sorted(results.items()):
        if res[0] == "silent":
            silent[key] = res[1]
        else:
            places[key] = res[1]
            if res[2]:
                unchecked.append(key)
            if res[3]:
                edge_nb[key] = {"kind": res[3], "regions": res[4]}
    pstat["places_kept"] = len(places)
    pstat["places_unchecked_no_coordinates"] = len(unchecked)
    pstat["places_edge_kept_with_neighbours"] = len(edge_nb)
    pstat["places_refused_ring_conflict"] = sum(1 for v in silent.values() if v == "ring-conflict")
    pstat["places_refused_edge"] = sum(1 for v in silent.values() if v == "edge")
    pstat["places_refused_marked_edge"] = sum(1 for v in silent.values() if v == "marked-edge")

    used = set(places.values()) | {r for v in edge_nb.values() for r in v["regions"]}
    q = doc["quality"]
    keep_row = lambda row: row.get("slug") in used or any(isinstance(row.get(k), str) and row[k].split("--era-")[0] in used for k in ("from", "to"))
    snap = {
        "version": eralib.VERSION,
        "built": built,
        "contract": {"name": CONTRACT_NAME, "version": version, "generated": doc["generated"], "sha256": hashlib.sha256(raw).hexdigest()},
        "atlas": {"base": a.atlas_base, "rings_source": rings_source, "rings_sha256": rings_sha},
        "policy": {"unassessed": a.unassessed, "boundary": boundary, "recent_from": a.recent_from, "edge_km": a.edge_km, "edge": a.edge,
                   "approx": a.approx, "contested": a.contested, "margin_years": a.margin_years,
                   "margins": {k: {"from": v[0], "to": v[1]} for k, v in sorted(overrides.items())}, "ruler_polities": ruler_polities},
        "regions": {k: regions[k] for k in sorted(regions) if k in used},
        "rulers": {r["id"]: region_rulers(r) for r in sorted(doc["regions"], key=lambda x: x["id"]) if r["id"] in used},
        "places": places,
        "places_silent": silent,
        "edge_neighbours": edge_nb,
        "unchecked_edge": unchecked,
        "dropped": sorted((d for d in dropped if d["region"] in used), key=lambda d: (d["region"], d["from"] if d["from"] is not None else 0, str(d["to"]), d["reason"])),
        "quality": {"counts": {"gaps": len(q.get("gaps") or []), "overlaps": len(q.get("overlaps") or [])},
                    "gaps": [r for r in q.get("gaps") or [] if keep_row(r)], "overlaps": [r for r in q.get("overlaps") or [] if keep_row(r)]},
    }
    stats.update(pstat)
    stats["rings_source"] = rings_source
    if rings_source == "file":
        stats["rings_override_differing_from_contract"] = differ
    if rings and not all_rings:
        stats["regions_without_a_usable_ring"] = sum(1 for r in doc["regions"] if r["id"] not in rings)
    stats["eras_dropped"] = dict(sorted(drop_by_reason.items()))
    stats["regions_in_snapshot"] = len(snap["regions"])
    stats["regions_with_rulers"] = sum(1 for v in snap["rulers"].values() if v["has"] is True)
    stats["reigns_carried"] = sum(len(v["reigns"]) for v in snap["rulers"].values())
    stats["regions_with_rulers_refused"] = sum(1 for v in snap["rulers"].values() if v["has"] is False and v["why"].startswith(("a reign", "hasRulers is true")))
    stats["contract"] = "%s generated %s" % (version, doc["generated"])
    report = {"contract": snap["contract"], "policy": snap["policy"], "eras_in": stats["eras_in"], "eras_kept": stats["eras_kept"],
              "eras_dropped_by_reason": dict(sorted(drop_by_reason.items())),
              "eras_dropped_by_region": {k: dict(sorted(v.items())) for k, v in sorted(drop_by_region.items())},
              "eras_in_by_region": {r["id"]: len(r.get("eras") or []) for r in doc["regions"]},
              "eras_kept_by_region": {k: len(v) for k, v in sorted(regions.items())}}
    return snap, stats, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--contract", required=True, help="a local copy of the Record Atlas's context.json (the versioned contract)")
    ap.add_argument("--rings", default=None, help="OPTIONAL override: the Atlas's regions.json (data/regions.json). By default the rings and "
                    "bboxes are read from the contract (1.8.0 and later)")
    ap.add_argument("--no-rings", action="store_true", help="say so explicitly: no place is edge-checked, every place is counted unchecked")
    ap.add_argument("--places", required=True, help="the archive's place -> region table (JSON)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--atlas-base", default=DEFAULT_BASE)
    ap.add_argument("--built", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--refuse-regimes", default=DEFAULT_REFUSE)
    ap.add_argument("--qualify-regimes", default=DEFAULT_QUALIFY, help="regimes whose label is a bare shorthand: shown with the era's polity")
    ap.add_argument("--unassessed", choices=("refuse", "allow"), default="refuse",
                    help="what to do with an era whose contested/approx is null (nobody assessed it). Default refuse.")
    ap.add_argument("--approx", choices=("refuse", "margin"), default="margin",
                    help="an era the Atlas marks approximate (its BOUNDS are uncertain): margin (default) uses it only for a year more than its margin "
                         "from each bound; refuse drops it")
    ap.add_argument("--contested", choices=("refuse", "scope", "margin"), default="scope",
                    help="an era the Atlas marks contested: scope (default) uses it, with its margins, only where the contract's contestedScope is "
                         "'bounds' (a scope of regime or part, or none, is refused); margin also accepts a contested era with NO scope (the what-if for a "
                         "contract before 1.10.0), still never regime or part; refuse drops every contested era")
    ap.add_argument("--margin-years", type=int, default=eralib.MARGIN_YEARS,
                    help="N, the FLOOR of every margin (default %d): a note on an era that carries margins needs a year more than max(N, margin) from each bound "
                         "(N more where marginSourced is false). 0 switches the floor off. For an approx era from a contract with no margins N alone holds it: "
                         "PROVISIONAL, not an Atlas fact" % eralib.MARGIN_YEARS)
    ap.add_argument("--margins", default=None, help="JSON {era id: years | {from, to}}: margins an archive WIDENS (never narrows) for single eras")
    ap.add_argument("--ruler-polities", default=None, help="JSON {regime id: [polityId, ...]}: which polities an era of a regime may name a ruler of "
                    "(replaces the kit's default: twosicilies and italy). A regime not in the table gets no ruler")
    ap.add_argument("--recent-from", type=int, default=eralib.RECENT_FROM,
                    help="the quiet rule: an event in the era still running from this year is silent (default %d)" % eralib.RECENT_FROM)
    ap.add_argument("--edge-km", type=float, default=eralib.EDGE_KM)
    ap.add_argument("--edge", choices=("agree", "strict"), default="agree",
                    help="a place near its region's ring edge (or inside another's ring): agree keeps it with the neighbours that could claim it, "
                         "and the note only in a year when they all have its regime; strict refuses it, as before")
    ap.add_argument("--outside-ring", choices=("keep", "refuse"), default="keep",
                    help="a place whose coordinates are outside its own region's ring (and not near another's)")
    ap.add_argument("--boundary", choices=("auto", "silent", "newer"), default="auto", help="auto: what the contract's rule says; silent is stricter")
    ap.add_argument("--report", default=None, help="write per-region counts of eras refused, and why, to this JSON file")
    ap.add_argument("--check", action="store_true", help="rebuild and compare with --out (ignoring `built`); write nothing")
    a = ap.parse_args(argv)
    if a.rings and a.no_rings:
        print("erasnap: --rings and --no-rings contradict each other", file=sys.stderr)
        return 2
    if not (isinstance(a.recent_from, int) and 1 <= a.recent_from <= 9999):
        print("erasnap: --recent-from must be a year", file=sys.stderr)
        return 2
    if not (isinstance(a.margin_years, int) and 0 <= a.margin_years <= 100):
        print("erasnap: --margin-years must be a whole number of years, 0 to 100", file=sys.stderr)
        return 2
    built = a.built or datetime.date.today().isoformat()
    snap, stats, report = build(a.contract, a.rings, a.places, a, built)
    text = json.dumps(snap, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if a.report:
        open(a.report, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    if a.check:
        try:
            have = json.load(open(a.out, encoding="utf-8"))
        except (OSError, ValueError):
            print("erasnap --check: %s is missing or unreadable" % a.out)
            return 1
        want = json.loads(text)
        have.pop("built", None)
        want.pop("built", None)
        if have != want:
            print("erasnap --check: %s differs from a rebuild from the same inputs (refresh it with erasnap.py and review the diff)" % a.out)
            return 1
        print("erasnap --check: ok  %d regions, %d places, %d eras" % (len(want["regions"]), len(want["places"]),
                                                                       sum(len(v) for v in want["regions"].values())))
        return 0
    open(a.out, "w", encoding="utf-8").write(text)
    print("erasnap: wrote %s" % a.out)
    for k, v in stats.items():
        print("  %-32s %s" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
