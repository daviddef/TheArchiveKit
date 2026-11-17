#!/usr/bin/env python3
"""The flag table for places named in prose: which flag flew over each place in each year, and today's.

    python3 placeflags.py --snapshot src/data/era-snapshot.json --places places.json --out place-flags.json
                          [--alias src/data/flag-places.json] [--countries src/data/flag-countries.json] [--now 2026]

WHY. kit/lib/placelinks.js links a place named in a correction to its page and draws the flag of the state that held it in the year the sentence
is about. The ribbon cards already work that out per card (kit/tools/ribbonflags.py); this does it per PLACE, over the years, once at build, so the
page only looks a year up. It uses ribbonflags' own chain (the archive's era snapshot -> the Atlas's regime -> kit/data/regime-flags.json -> the one
flag whose years cover the year) and so its own silences: a boundary year, a contested place, an unassessed era, two flags that overlap, no art: no
flag for that year. Nothing is filled in.

--places is the archive's list of places it has a page for: [{"name": "Crikvenica", "aliases": ["..."], "flagKey": "optional"}], the same rows
placeIndex() takes. The snapshot is looked up by the name as the archive's era table prints it; --alias maps a name another way ({name: table name
| null}), as for the ribbon.

THE TABLE it writes:  { "<flagKey or name>": { "today": {"svg": "croatia-flags--era-1991.svg", "label": "Croatia"} | null,
                                               "eras": [[from, to, "svg-file", "Regime label"], ...] } }
`eras` are runs of whole years [from, to) in which one flag stood; a year in no run has no flag. Exit 0; 2 an input cannot be read."""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eralib  # noqa: E402
import ribbonflags as rf  # noqa: E402

FIRST = 1300


def era_run_table(ctx, lookup, now):
    """[[from, to, svg, label], ...] for the years FIRST..now that the snapshot assesses and the table gives exactly one flag."""
    runs, cur = [], None
    for y in range(FIRST, now + 1):
        try:
            era, fid, why = rf._flag_for(ctx, lookup, y, None)
        except Exception:
            era, fid = None, None
        ok = fid is not None and era is not None and era.get("assessed")
        key = (ctx["index"]["flags"][fid]["file"], era["label"]) if ok else None
        if cur and cur[2] == key:
            cur[1] = y + 1
            continue
        if cur and cur[2] is not None:
            runs.append([cur[0], cur[1], cur[2][0], cur[2][1]])
        cur = [y, y + 1, key]
    if cur and cur[2] is not None:
        runs.append([cur[0], cur[1], cur[2][0], cur[2][1]])
    return runs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--places", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--alias")
    ap.add_argument("--countries")
    ap.add_argument("--now", type=int)
    a = ap.parse_args(argv)
    try:
        snap, places = rf.load(a.snapshot), rf.load(a.places)
        alias = rf.load(a.alias) if a.alias else {}
        countries = rf.load(a.countries) if a.countries else {}
    except (OSError, ValueError) as e:
        print(f"placeflags: cannot read an input: {e}", file=sys.stderr)
        return 2
    alias = {k: v for k, v in alias.items() if not k.startswith("_")}
    countries = {k: v for k, v in countries.items() if not k.startswith("_")}
    ctx = rf.context(snap, alias, a.now, countries=countries)
    now = ctx["now"]
    table, n_era, n_today = {}, 0, 0
    for row in places:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        key = row.get("flagKey") or name
        if key in table:
            continue
        card = {"atPlace": name}
        lookup = alias[name] if name in alias else name
        eras = era_run_table(ctx, lookup, now) if lookup else []
        tf, why = rf.today_flag(ctx, card, "at")
        today = None
        if tf:
            cc = tf["country"]
            today = {"svg": tf["svg"], "label": ctx["countries_table"]["countries"][cc]["name"]}
        if eras or today:
            table[key] = {"today": today, "eras": eras}
            n_era += 1 if eras else 0
            n_today += 1 if today else 0
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(table, ensure_ascii=False, indent=1) + "\n")
    print(f"placeflags: {len(table)} places with a flag of some kind ({n_era} with era flags, {n_today} with today's) of {len(places)} given -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
