#!/usr/bin/env python3
"""Build the era snapshot an archive keeps: the Record Atlas's versioned context contract, cut down to what a note may say, committed.

WHY A SNAPSHOT. The sites are static and the Atlas's files change daily. A note that fetched the Atlas at build time would
make the same page say different things on different days, and a note an archive cannot reproduce is a claim it cannot stand
behind. So the archive commits `era-snapshot.json`, refreshes it by running THIS, deliberately, and reviews the diff. Nothing
in a build ever reads the Atlas. kit/lib/era.js reads the snapshot; kit/tools/checkera.py holds the built pages to it.

    python3 erasnap.py --contract <Record Atlas>/site/public/context.json --rings <Record Atlas>/data/regions.json \\
                       --places era-places.json --out era-snapshot.json
    python3 erasnap.py ... --check          # rebuild in memory and compare with --out (ignores `built`); exit 1 if it differs
    python3 erasnap.py ... --report drops.json      # also write, per region, the eras refused and why (counts, for the Atlas)

THE CONTRACT is https://recordatlas.org/context.json (documented at /data/#context): region eras with a permanent id
(`<region>--era-<from>`), a half-open interval (from <= year < to; `to` null = still running), a display label (`regimeLabel`),
a `basis` (where the region's bands came from), `contested` and `approx` (null = nobody has assessed it), and a `quality` block
listing gaps and overlaps. It is read as the SOURCE: the snapshot records its version, its `generated` stamp and the sha256 of
the file's bytes. Major version 1 only; any other is refused (a renamed field is what a major version is for).

THE RINGS are NOT in the contract. They are in the Atlas's regions.json (the source the contract is built from: use
`data/regions.json` in the Atlas repository; `site/public/regions.json` is what the Atlas served last and can be older than the
contract). They are needed only for the edge rule below, and the ring file must describe the same regions and eras as the
contract or the build stops. `--no-rings` says so explicitly: no place is then edge-checked, and all are counted unchecked.

THE PLACE TABLE is the ARCHIVE's, never the Atlas's: a JSON object (or {"places": {...}}) from a place exactly as the archive
prints it to a region id, either `"Briatico, Vibo Valentia, Calabria": "calabria"` or an entry with coordinates the archive holds
`"...": {"region": "calabria", "lat": 38.72, "lon": 16.03}`, and optionally `"edge": true` (the archive says this place is on the
edge of its region: it gets no note). A null region (or "-") says "looked at, and no region covers it". A place is folded
(kit/lib/era.js fold) to a key, so spellings that differ only in case, accents or punctuation are one place.

THE EDGE RULE. The rings are 4-11 vertex shapes, "approximate by design". With coordinates:
  - a point inside ANOTHER region's ring and not inside its own is refused ("ring-conflict");
  - a point within --edge-km (default 15) of its own region's ring edge, inside or outside, is refused ("edge");
  - a point outside its own ring and further than that is kept (the archive's table is its own statement) unless --outside-ring
    refuse, and is counted;
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
  an era the contract marks approximate or contested (true), and, unless --unassessed allow, one it has not assessed (null).
    As of contract 1.7.0 EVERY region era is null on both, so the default keeps NO era; --unassessed allow is a deliberate choice an
    archive makes, recorded in the snapshot's policy, printed by the gate, and refused by the gate's --strict-unassessed.
It KEEPS, but flags contested, BOTH eras of any pair of eras of one region that overlap: era.js then stays silent about every year
they touch. The display label is the contract's regimeLabel; for a --qualify-regimes regime (default napo) it is the era's polity
(when that already begins with the label) or "<label> - <polity>", never invented.
A region whose `basis` begins "seeded:" (the Atlas took its bands from this estate's own research) carries seeded_from_archive true
on every era, so a note says "per this archive's own research" and does not pretend the Atlas is a second source.
The boundary policy comes from the contract's own `rule` text: "newer" only if it says a year equal to a boundary belongs to the
newer era; otherwise "silent". --boundary silent can make it stricter, never looser.

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


def check_rings(contract, rings_doc):
    """The ring file must describe the contract's regions and eras. -> ({region: ring}, regimes)."""
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
        ring = r.get("ring")
        if isinstance(ring, list) and len(ring) >= 3 and all(isinstance(p, list) and len(p) == 2 and all(isinstance(x, (int, float)) for x in p) for p in ring):
            rings[rid] = ring
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
    rings, rregimes, rings_sha = {}, {}, None
    if rings_path:
        rraw, rdoc = load_json_bytes(rings_path)
        rings, rregimes = check_rings(doc, rdoc)
        rings_sha = hashlib.sha256(rraw).hexdigest()
    gap_ids, overlap_ids = quality_ids(doc["quality"])

    stats = {"eras_in": 0, "eras_kept": 0, "eras_flagged_contested_overlap": 0}
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
            if ap is True:
                drop(rid, e, R_APPROX)
                continue
            if co is True:
                drop(rid, e, R_CONTESTED)
                continue
            if (ap is not False or co is not False) and a.unassessed != "allow":
                drop(rid, e, R_UNASSESSED)
                continue
            basis = e.get("basis") if isinstance(e.get("basis"), str) else "not-recorded"
            kept.append({"id": e["id"], "from": frm, "to": to, "present": to is None, "regime": reg, "label": lab,
                         "polity": e.get("polity") if isinstance(e.get("polity"), str) else None, "basis": basis,
                         "seeded_from_archive": basis.startswith("seeded:"), "approx": ap, "contested": co, "url": e["url"]})
        for x in kept:
            if any(y is not x and eralib.meets(x, y) for y in kept):
                x["contested"] = True
        stats["eras_kept"] += len(kept)
        stats["eras_flagged_contested_overlap"] += sum(1 for x in kept if x["contested"] is True)
        regions[rid] = kept

    table = load_table(table_path)
    results = {}          # key -> ("ok", region, unchecked) | ("silent", why)
    pstat = {"places_in": len(table), "places_kept": 0, "places_unmapped": 0, "places_refused_ring_conflict": 0,
             "places_refused_edge": 0, "places_refused_marked_edge": 0, "places_outside_own_ring_kept": 0,
             "places_outside_own_ring_refused": 0, "places_unchecked_no_coordinates": 0}
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
            others = [o for o, ring in rings.items() if o != rid and eralib.pip(lat, lon, ring)]
            dist = eralib.edge_km(lat, lon, rings[rid])
            if not mine and others:
                res = ("silent", "ring-conflict")
            elif dist <= a.edge_km:
                res = ("silent", "edge")
            elif not mine and a.outside_ring == "refuse":
                res = ("silent", "ring-conflict")
                pstat["places_outside_own_ring_refused"] += 1
            else:
                res = ("ok", rid, False)
                if not mine:
                    pstat["places_outside_own_ring_kept"] += 1
        else:
            res = ("ok", rid, True)
        prev = results.get(key)
        if prev is not None and prev != res:
            if prev[0] == "ok" and res[0] == "ok" and prev[1] != res[1]:
                raise SystemExit("erasnap: two places that fold to one key are sent to different regions")
            res = prev if prev[0] == "silent" else res        # a refusal wins over a keep
        results[key] = res
    places, silent, unchecked = {}, {}, []
    for key, res in sorted(results.items()):
        if res[0] == "silent":
            silent[key] = res[1]
        else:
            places[key] = res[1]
            if res[2]:
                unchecked.append(key)
    pstat["places_kept"] = len(places)
    pstat["places_unchecked_no_coordinates"] = len(unchecked)
    pstat["places_refused_ring_conflict"] = sum(1 for v in silent.values() if v == "ring-conflict")
    pstat["places_refused_edge"] = sum(1 for v in silent.values() if v == "edge")
    pstat["places_refused_marked_edge"] = sum(1 for v in silent.values() if v == "marked-edge")

    used = {v for v in places.values()}
    q = doc["quality"]
    keep_row = lambda row: row.get("slug") in used or any(isinstance(row.get(k), str) and row[k].split("--era-")[0] in used for k in ("from", "to"))
    snap = {
        "version": eralib.VERSION,
        "built": built,
        "contract": {"name": CONTRACT_NAME, "version": version, "generated": doc["generated"], "sha256": hashlib.sha256(raw).hexdigest()},
        "atlas": {"base": a.atlas_base, "rings_sha256": rings_sha},
        "policy": {"unassessed": a.unassessed, "boundary": boundary, "recent_from": a.recent_from, "edge_km": a.edge_km},
        "regions": {k: regions[k] for k in sorted(regions) if k in used},
        "places": places,
        "places_silent": silent,
        "unchecked_edge": unchecked,
        "dropped": sorted((d for d in dropped if d["region"] in used), key=lambda d: (d["region"], d["from"] if d["from"] is not None else 0, str(d["to"]), d["reason"])),
        "quality": {"counts": {"gaps": len(q.get("gaps") or []), "overlaps": len(q.get("overlaps") or [])},
                    "gaps": [r for r in q.get("gaps") or [] if keep_row(r)], "overlaps": [r for r in q.get("overlaps") or [] if keep_row(r)]},
    }
    stats.update(pstat)
    stats["eras_dropped"] = dict(sorted(drop_by_reason.items()))
    stats["regions_in_snapshot"] = len(snap["regions"])
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
    ap.add_argument("--rings", default=None, help="the Atlas's regions.json (data/regions.json), for the ring-edge rule: the contract has no rings")
    ap.add_argument("--no-rings", action="store_true", help="say so explicitly: no place is edge-checked, every place is counted unchecked")
    ap.add_argument("--places", required=True, help="the archive's place -> region table (JSON)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--atlas-base", default=DEFAULT_BASE)
    ap.add_argument("--built", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--refuse-regimes", default=DEFAULT_REFUSE)
    ap.add_argument("--qualify-regimes", default=DEFAULT_QUALIFY, help="regimes whose label is a bare shorthand: shown with the era's polity")
    ap.add_argument("--unassessed", choices=("refuse", "allow"), default="refuse",
                    help="what to do with an era whose contested/approx is null (nobody assessed it). Default refuse.")
    ap.add_argument("--recent-from", type=int, default=eralib.RECENT_FROM,
                    help="the quiet rule: an event in the era still running from this year is silent (default %d)" % eralib.RECENT_FROM)
    ap.add_argument("--edge-km", type=float, default=eralib.EDGE_KM)
    ap.add_argument("--outside-ring", choices=("keep", "refuse"), default="keep",
                    help="a place whose coordinates are outside its own region's ring (and not near another's)")
    ap.add_argument("--boundary", choices=("auto", "silent", "newer"), default="auto", help="auto: what the contract's rule says; silent is stricter")
    ap.add_argument("--report", default=None, help="write per-region counts of eras refused, and why, to this JSON file")
    ap.add_argument("--check", action="store_true", help="rebuild and compare with --out (ignoring `built`); write nothing")
    a = ap.parse_args(argv)
    if bool(a.rings) == bool(a.no_rings):
        print("erasnap: give --rings <the Atlas's regions.json> (the contract carries no rings), or --no-rings to say no place is edge-checked", file=sys.stderr)
        return 2
    if not (isinstance(a.recent_from, int) and 1 <= a.recent_from <= 9999):
        print("erasnap: --recent-from must be a year", file=sys.stderr)
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
