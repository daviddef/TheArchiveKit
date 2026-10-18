#!/usr/bin/env python3
"""Build the era snapshot an archive keeps: the Record Atlas's region eras, cut down to what a note may say, committed.

WHY A SNAPSHOT. The sites are static and the Atlas's files change daily. A note that fetched the Atlas at build time would
make the same page say different things on different days, and a note an archive cannot reproduce is a claim it cannot stand
behind. So the archive commits `era-snapshot.json`, refreshes it by running THIS, deliberately, and reviews the diff. Nothing
in a build ever reads the Atlas. kit/lib/era.js reads the snapshot; kit/tools/checkera.py holds the built pages to it.

    python3 erasnap.py --atlas <Record Atlas>/site/public/regions.json --places era-places.json --out era-snapshot.json
    python3 erasnap.py ... --check          # rebuild in memory and compare with --out (ignores `built`); exit 1 if it differs

THE PLACE TABLE is the ARCHIVE's, never the Atlas's: a JSON object (or {"places": {...}}) from a place exactly as the archive
prints it to a region id, either `"Briatico, Vibo Valentia, Calabria": "calabria"` or an entry with coordinates the archive holds
`"...": {"region": "calabria", "lat": 38.72, "lon": 16.03}`. A null region (or "-") says "looked at, and no region covers it". A
place is folded (kit/lib/era.js fold) to a key, so spellings that differ only in case, accents or punctuation are one place.
If coordinates are given and the point falls inside ANOTHER region's ring while not inside its own, the place is refused: the
rings are four- and five-sided shapes, "approximate by design", and a town on a ring's edge must not be given its neighbour's era.

WHAT IT REFUSES, and counts (rule b; kit/docs/era-notes.md)
  an era without a whole-number start and end year, or with a start that is not before its end ("words-only")
  an era whose regime has no label, or whose regime is one the Atlas itself calls "this project's own shorthand for a situation
    rather than the name of a state" (`feudal` = "Aquileia · Gorizia · Frankopan" is Istria's, and means nothing in Calabria;
    `german` = "German occupation"): --refuse-regimes, default feudal,german
  an era that falls outside the dates the Atlas holds for its regime (`existed`)
It KEEPS, but flags, an era marked approximate or contested, and BOTH eras of any pair that overlap (contested): era.js then
stays silent about every year they touch, and an archive can count what it left silent and why.
A region whose regimes the Atlas seeded from this estate's own research carries seeded_from_archive: true on every era
(--seeded, default: istria-central, istria-south, kvarner, carnia, dalmatia, imotski), so a note can say "per this archive's
own research" and not pretend the Atlas is a second source.

Prints counts only; never a place or a person.
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eralib  # noqa: E402

DEFAULT_SEEDED = "istria-central,istria-south,kvarner,carnia,dalmatia,imotski"
DEFAULT_REFUSE = "feudal,german"
DEFAULT_BASE = "https://recordatlas.org"


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


def git_ref(path):
    d = os.path.dirname(os.path.abspath(path))
    try:
        sha = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", d, "status", "--porcelain", "--", os.path.abspath(path)], capture_output=True,
                               text=True, check=True).stdout.strip()
        return sha + ("+modified" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return ""


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
            out[k] = (v.get("region"), v.get("lat"), v.get("lon"))
        else:
            out[k] = (v, None, None)
    return out


def build(atlas_path, table_path, base, ref, built, seeded, refuse):
    raw = open(atlas_path, "rb").read()
    atlas = json.loads(raw)
    regimes_in = atlas.get("regimes") or {}
    regions_in = atlas.get("regions") or []
    rings = {r["id"]: r.get("ring") for r in regions_in}
    stats = {"eras_in": 0, "eras_kept": 0, "eras_flagged_approx": 0, "eras_flagged_contested": 0}
    dropped = []
    drop_n = {}

    def drop(rid, e, why):
        drop_n[why] = drop_n.get(why, 0) + 1
        dropped.append({"region": rid, "from": e.get("from"), "to": e.get("to"), "reason": why})

    regions = {}
    used = set()
    for r in regions_in:
        rid = r["id"]
        kept = []
        for e in r.get("eras") or []:
            stats["eras_in"] += 1
            if not (eralib.is_year(e.get("from")) and eralib.is_year(e.get("to"))):
                drop(rid, e, "words-only or non-numeric years")
                continue
            if not e["from"] < e["to"]:
                drop(rid, e, "start not before end")
                continue
            reg = e.get("regime")
            lab = ((regimes_in.get(reg) or {}).get("label") if isinstance(reg, str) else None)
            if not isinstance(lab, str) or not lab.strip():
                drop(rid, e, "regime has no label")
                continue
            if reg in refuse:
                drop(rid, e, "regime is the project's own shorthand, not a state")
                continue
            ex = (regimes_in.get(reg) or {}).get("existed")
            if isinstance(ex, list) and len(ex) == 2 and all(isinstance(x, int) for x in ex) and not (ex[0] <= e["from"] and e["to"] <= ex[1]):
                drop(rid, e, "era outside the dates the Atlas holds for its regime")
                continue
            kept.append({"from": e["from"], "to": e["to"], "regime": reg, "approx": bool(e.get("approx")),
                         "contested": bool(e.get("contested")), "seeded_from_archive": rid in seeded, "sources": ["regions.json"]})
            used.add(reg)
        for a in kept:
            if any(b is not a and a["from"] < b["to"] and b["from"] < a["to"] for b in kept):
                a["contested"] = True
        stats["eras_kept"] += len(kept)
        stats["eras_flagged_approx"] += sum(1 for a in kept if a["approx"])
        stats["eras_flagged_contested"] += sum(1 for a in kept if a["contested"])
        regions[rid] = kept

    table = load_table(table_path)
    places = {}
    pstat = {"places_in": len(table), "places_kept": 0, "places_unmapped": 0, "places_refused_ring": 0, "places_outside_own_ring": 0}
    for name, (rid, lat, lon) in sorted(table.items()):
        key = eralib.fold(name)
        if not key:
            raise SystemExit("erasnap: a place in the table folds to nothing")
        if rid in (None, "", "-"):
            pstat["places_unmapped"] += 1
            continue
        if rid not in regions:
            raise SystemExit("erasnap: the table sends a place to region %r, which the Atlas file does not hold" % rid)
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and rings.get(rid):
            mine = pip(lat, lon, rings[rid])
            others = [o for o, ring in rings.items() if o != rid and ring and pip(lat, lon, ring)]
            if not mine and others:
                pstat["places_refused_ring"] += 1
                continue
            if not mine:
                pstat["places_outside_own_ring"] += 1
        if key in places and places[key] != rid:
            raise SystemExit("erasnap: two places that fold to one key are sent to different regions")
        places[key] = rid
        pstat["places_kept"] += 1

    snap = {
        "version": eralib.VERSION,
        "built": built,
        "atlas_commit_or_etag": ref,
        "atlas": {"base": base, "file_sha256": hashlib.sha256(raw).hexdigest()},
        "regimes": {k: regimes_in[k]["label"].strip() for k in sorted(used)},
        "regions": {k: regions[k] for k in sorted(regions) if k in set(places.values())},
        "places": dict(sorted(places.items())),
        "dropped": sorted((d for d in dropped if any(d["region"] == v for v in places.values())),
                          key=lambda d: (d["region"], str(d["from"]), str(d["to"]))),
    }
    # only regimes a kept region actually uses
    need = {e["regime"] for es in snap["regions"].values() for e in es}
    snap["regimes"] = {k: v for k, v in snap["regimes"].items() if k in need}
    stats.update(pstat)
    stats["eras_dropped"] = dict(sorted(drop_n.items()))
    stats["regions_in_snapshot"] = len(snap["regions"])
    return snap, stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--atlas", required=True, help="a local copy of the Record Atlas's regions.json")
    ap.add_argument("--places", required=True, help="the archive's place -> region table (JSON)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--atlas-ref", default=None, help="the Atlas commit or the file's ETag (default: git HEAD beside --atlas)")
    ap.add_argument("--atlas-base", default=DEFAULT_BASE)
    ap.add_argument("--built", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--seeded", default=DEFAULT_SEEDED)
    ap.add_argument("--refuse-regimes", default=DEFAULT_REFUSE)
    ap.add_argument("--check", action="store_true", help="rebuild and compare with --out (ignoring `built`); write nothing")
    a = ap.parse_args(argv)
    ref = a.atlas_ref if a.atlas_ref is not None else git_ref(a.atlas)
    if not ref:
        print("erasnap: no --atlas-ref and no git history beside --atlas: the snapshot must say which Atlas it came from", file=sys.stderr)
        return 2
    built = a.built or datetime.date.today().isoformat()
    split = lambda s: {x.strip() for x in s.split(",") if x.strip()}
    snap, stats = build(a.atlas, a.places, a.atlas_base, ref, built, split(a.seeded), split(a.refuse_regimes))
    text = json.dumps(snap, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
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
        print("  %-26s %s" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
