#!/usr/bin/env python3
"""Mini flags on the ribbon cards: which flag flew over the place a card names, in that card's year. The generator.

WHAT IT DOES. For each card of the story ribbon (story.json `ribbon.cards`) and of the family ribbons (family-lines.json
`families[].cards`), and for each of the card's place lines (`from <origin>`, `at <place> <year>`, `m. <spouse>, of <origin>`),
it works out the ERA flag (the regime that held that place in that card's year) and TODAY's flag (the country the place is in now,
drawn only where it is another country's, or alone where the era cannot be said), and writes them to the card as `flags`:

    {kind: era|today, line: from|at|spouse, place, svg, flag, era|country, year, label, grade, assessed}

The ribbons draw them as one strip in the card's header row (components/FlagMini.astro). TODAY's country: the card's own words,
then the archive's (--countries; its snapshot region when it lies in one country), then kit/data/place-countries.json; a name two
countries have is never guessed.

THE ERA FLAG'S CHAIN (kit/docs/ribbon-flags.md has the why of each step):
    the place as the card prints it  -> the archive's era snapshot (era-snapshot.json: the same table and the same rules as the
                                        "at the time" notes, kit/tools/eralib.py era_at: rings, edges, margins, boundary years,
                                        the quiet rule, assessed or not)
    -> the region era for the year   -> its regime (and its region era id)
    -> kit/data/regime-flags.json    -> the Flags Atlas flags that stand for that regime (or for that one era)
    -> the one flag whose own years cover the year, of an evidence class the table allows, not withheld
    -> kit/data/flags/<flag id>.svg  (the artwork, copied from the Record Atlas by --sync-atlas; index.json lists it)
Anything that does not resolve to exactly one flag is SILENCE: no flag and no words, and the reason is counted.

    python3 ribbonflags.py --snapshot src/data/era-snapshot.json --story src/data/story.json \\
            [--family-lines src/data/family-lines.json] [--alias src/data/flag-places.json] [--now 2026] (--write | --check) [--report out.json]
    python3 ribbonflags.py --sync-atlas "<Record Atlas>/site/public" [--write]      kit maintainers: refresh kit/data/flags from the Atlas

--alias is the archive's table of card place text -> the place as its era table prints it (or null: no region), for a card that
prints a place another way ("Rosario de Santa Fe" for "Rosario, Santa Fe"). Without it a card's text must be in the snapshot.
Exit 0 ok, 1 (--check) the cards are not what the inputs make, 2 an input cannot be read.
"""
import argparse, copy, datetime, hashlib, json, math, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import eralib  # noqa: E402

TABLE = os.path.join(KIT, "data", "regime-flags.json")
FLAG_DIR = os.path.join(KIT, "data", "flags")
INDEX = os.path.join(FLAG_DIR, "index.json")
PLACE_COUNTRIES = os.path.join(KIT, "data", "place-countries.json")
CREDIT = "Flags: Flags Atlas, by David Defranceski, drawn for this project"
TAIL = ": flag as in Flags Atlas"
EVIDENCE_WORD = {"reconstructed": " (reconstructed)", "symbolic": " (an emblem)"}
LINES = ("from", "at", "spouse")
GRADES = ("doc", "inf", "lore")


def load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def dump(p, doc):
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


# ---- years and places on a card -----------------------------------------------------------------------------------------
LEAD = re.compile(r"^(?:named\s+)?(\d{4})(?:\s*[–—-].*)?$")


def plain(v):
    """A whole year written as four digits and nothing else ("1791", 1791), else None."""
    if isinstance(v, int) and not isinstance(v, bool):
        return v if 1000 <= v <= 2999 else None
    s = str(v if v is not None else "").strip()
    return int(s) if re.fullmatch(r"\d{4}", s) else None


def lead_year(years):
    """The card's first year where `years` begins with a plain one: "1882–1950" -> 1882, "named 1791" -> 1791; "c.1767–...", "by 1882" -> None."""
    m = LEAD.match(str(years or "").strip())
    return int(m.group(1)) if m else None


def line_year(card, line):
    """The year a line's flag is for. at: atYear. from: originYear if the card states one (then only it), else the first plain year of
    `years`, else atYear. spouse: spouseOriginYear if stated, else the from line's year (the same generation, the same papers)."""
    at = plain(card.get("atYear"))
    if line == "at":
        return at
    if line == "from":
        if card.get("originYear") not in (None, ""):
            return plain(card.get("originYear"))
        return lead_year(card.get("years")) or at
    if card.get("spouseOriginYear") not in (None, ""):
        return plain(card.get("spouseOriginYear"))
    return line_year(card, "from")


OF = re.compile(r"^(?:of|from)\s+", re.I)


def line_place(card, line):
    """The place a line names, as the card prints it (the spouse line's leading "of " taken off), or ""."""
    v = {"from": card.get("origin"), "at": card.get("atPlace"), "spouse": card.get("spouseOrigin")}[line]
    s = str(v or "").strip()
    return OF.sub("", s).strip() if line == "spouse" else s


def living_line(card, line):
    """A living (or minor) card, or a living spouse's line: the flag of the country only, with no year."""
    if card.get("living") or card.get("minor"):
        return True
    return line == "spouse" and bool(card.get("spouseLiving") or card.get("spouseMinor"))


# ---- the flag for a regime in a year --------------------------------------------------------------------------------------
def flag_covers(f, year):
    fr, to = f.get("from"), f.get("to")
    if not isinstance(fr, int):
        return False
    if to is None:
        return f.get("present") is True and fr <= year
    return isinstance(to, int) and fr <= year < to


def flag_list(table, era_id, regime):
    if era_id in (table.get("eras") or {}):
        return table["eras"][era_id].get("flags")
    if regime in (table.get("regimes") or {}):
        return table["regimes"][regime].get("flags")
    return None


def pick(table, index, era_id, regime, year):
    """(flag id, "ok") or (None, why)."""
    lst = flag_list(table, era_id, regime)
    if lst is None:
        return None, "no-table"
    if not lst:
        return None, "no-flag"
    withheld = table.get("withheld") or {}
    flags = index.get("flags") or {}
    cands = []
    for fid in lst:
        if fid in withheld:
            continue
        f = flags.get(fid)
        if f is None:
            continue            # in the table, but no region era can pick it (index.json `unpicked`): it covers none of these years
        if flag_covers(f, year):
            cands.append(fid)
    if not cands:
        return None, "no-flag-for-year"
    if len(cands) > 1:
        return None, "flags-overlap"
    if not flags[cands[0]].get("file"):
        return None, "no-art"
    if flags[cands[0]].get("evidence") not in (table.get("evidence") or []):
        return None, "evidence"
    return cands[0], "ok"


def era_record(snap, region, era_id):
    for e in (snap.get("regions") or {}).get(region) or []:
        if e.get("id") == era_id:
            return e
    return None


def neighbour_flag(snap, table, index, nb, year):
    eras = [e for e in (snap.get("regions") or {}).get(nb) or [] if eralib.numeric(e) and eralib.covers(e, year)]
    if len(eras) != 1:
        return None
    return pick(table, index, eras[0]["id"], eras[0].get("regime"), year)[0]


PHRASE = {"from": "from {}", "at": "at {}", "spouse": "spouse of {}"}


def era_label(line, place, year, era_label_, evidence):
    """'at Canelones, 1791: Spanish Empire then' (the place the flag is for, its year, the Atlas's regime label)."""
    return f"{PHRASE[line].format(place)}, {year}: {era_label_} then{EVIDENCE_WORD.get(evidence, '')}"


def today_label(line, place, country, evidence):
    """'from Córdoba: Spain today'."""
    return f"{PHRASE[line].format(place)}: {country} today{EVIDENCE_WORD.get(evidence, '')}"


def lookup_of(ctx, card, line):
    """(the place as the card prints it, the text to look up in the snapshot | None, why)."""
    place = line_place(card, line)
    if not place:
        return place, None, "no-place"
    alias = ctx["alias"]
    if place in alias:
        return (place, None, "no-region") if alias[place] is None else (place, alias[place], "ok")
    return place, place, "ok"


def _flag_for(ctx, lookup, year, recent):
    """The era the snapshot gives and the flag the table picks for it: (era, flag id, "ok") or (era|None, None, why)."""
    snap = ctx["snapshot"]
    why = eralib.why_not(snap, lookup, year, recent_from=recent)
    if why != "ok":
        return None, None, why
    era = eralib.era_at(snap, lookup, year, recent_from=recent)
    if era["boundary"]:
        return era, None, "boundary"
    if era["contested"]:
        return era, None, "contested"
    rec = era_record(snap, era["region"], era["id"])
    fid, why = pick(ctx["table"], ctx["index"], era["id"], rec.get("regime") if rec else None, year)
    if fid is None:
        return era, None, why
    if era["edgeAgree"]:
        en = (snap.get("edge_neighbours") or {}).get(era["place"]) or {}
        for nb in en.get("regions") or []:
            if neighbour_flag(snap, ctx["table"], ctx["index"], nb, year) != fid:
                return era, None, "edge-flag"
    return era, fid, "ok"


def era_flag(ctx, card, line):
    """The flag of the state that held the place in the line's year: (flag, "ok") or (None, why). Needs an ASSESSED era."""
    place, lookup, why = lookup_of(ctx, card, line)
    if lookup is None:
        return None, why
    if living_line(card, line):
        return None, "living"
    year = line_year(card, line)
    if year is None or year > ctx["now"]:
        return None, "year"
    era, fid, why = _flag_for(ctx, lookup, year, None)
    if fid is None:
        return None, why
    if not era["assessed"]:
        return None, "unassessed"
    f = ctx["index"]["flags"][fid]
    return {"kind": "era", "line": line, "place": place, "svg": f["file"], "flag": fid, "era": era["id"], "year": year,
            "label": era_label(line, place, year, era["label"], f.get("evidence")), "grade": grade_of(card), "assessed": True}, "ok"


def country_of(ctx, card, line):
    """TODAY's country of the line's place: (cc, source) or (None, why). The card's own words first (a part that is a country:
    'Brisbane, Australia'), then the archive's own (its --countries file; its era snapshot's region, where that region lies in one
    country), then the kit's table (data/place-countries.json). A name two countries have is never read from the kit's table; two
    sources that disagree give nothing."""
    place = line_place(card, line)
    if not place:
        return None, "no-place"
    pc = ctx["countries_table"]
    parts = [eralib.fold(p) for p in place.split(",") if eralib.fold(p)]
    full = eralib.fold(place)
    explicit = {cc for p in parts for cc, m in pc["countries"].items() if p in m["aliases"]}
    if len(explicit) == 1:
        return explicit.pop(), "card"
    if len(explicit) > 1:
        return None, "two-countries"
    if place in ctx["countries"]:
        v = ctx["countries"][place]
        return (v, "archive") if v in pc["countries"] else (None, "archive-none")
    cands, region_split = set(), False
    lookup = ctx["alias"].get(place, place) if place in ctx["alias"] else place
    region = (ctx["snapshot"].get("places") or {}).get(eralib.fold(lookup or ""))
    if region:
        rc = (ctx["index"].get("regionCountries") or {}).get(region) or []
        if len(rc) == 1:
            cands.add(rc[0])
        else:
            region_split = True
    amb = set(pc.get("ambiguous") or [])
    if full in pc["places"]:
        cands.add(pc["places"][full])
    elif full not in amb:
        cands |= {pc["places"][p] for p in parts if p in pc["places"]}
    if len(cands) == 1:
        return cands.pop(), "table"
    if len(cands) > 1:
        return None, "sources-disagree"
    if full in amb or any(p in amb for p in parts):
        return None, "ambiguous"
    return None, "region-split" if region_split else "unknown-place"


def today_flag(ctx, card, line):
    """The flag of the country the place is in today: (flag, "ok") or (None, why)."""
    cc, src = country_of(ctx, card, line)
    if cc is None:
        return None, src
    fid = (ctx["index"].get("today") or {}).get(cc)
    if not fid:
        return None, "no-present-flag"
    f = ctx["index"]["flags"][fid]
    place = line_place(card, line)
    return {"kind": "today", "line": line, "place": place, "svg": f["file"], "flag": fid, "country": cc, "year": None,
            "label": today_label(line, place, ctx["countries_table"]["countries"][cc]["name"], f.get("evidence")), "grade": grade_of(card)}, "ok"


def grade_of(card):
    return card.get("originGrade") if card.get("originGrade") in GRADES else "doc"


def same_country(index, a, b):
    """Two flags of one Flags Atlas country page (Spain then and Spain now): the card draws the era's alone."""
    fa, fb = index["flags"].get(a) or {}, index["flags"].get(b) or {}
    return a == b or (fa.get("country") is not None and fa.get("country") == fb.get("country")) or bool(fa.get("sha256") and fa.get("sha256") == fb.get("sha256"))


def line_flags(ctx, card, line):
    """The flags of one line, era first: [era], [era, today] (another country now), [today] (the era cannot be said), or []."""
    e, ewhy = era_flag(ctx, card, line)
    t, twhy = today_flag(ctx, card, line)
    if e and t and same_country(ctx["index"], e["flag"], t["flag"]):
        t = None
    return [x for x in (e, t) if x], ewhy, twhy


def card_flags(ctx, card):
    """The card's flags (in line order) and, per line with a place, what it carries and why not more."""
    out, notes = [], []
    for line in LINES:
        if not line_place(card, line):
            continue
        fl, ewhy, twhy = line_flags(ctx, card, line)
        notes.append((line, line_place(card, line), ewhy, twhy, "none" if not fl else "+".join(f["kind"] for f in fl)))
        out += fl
    return out, notes


# ---- the archive's files -----------------------------------------------------------------------------------------------
def cards_of(story, families):
    """(where, card) for every stored card: ("story", i, card) and ("family:<id>", i, card). Lane families have no stored cards."""
    out, lanes = [], []
    if story is not None:
        for i, c in enumerate(((story.get("ribbon") or {}).get("cards")) or []):
            out.append(("story", i, c))
    if families is not None:
        fams = families.get("families") if isinstance(families, dict) else families
        for fam in fams or []:
            if fam.get("cards"):
                for i, c in enumerate(fam["cards"]):
                    out.append((f"family:{fam.get('id')}", i, c))
            elif fam.get("lane"):
                lanes.append(fam.get("id"))
    return out, lanes


def context(snapshot, alias=None, now=None, table=None, index=None, countries=None, countries_table=None):
    return {"snapshot": snapshot, "alias": alias or {}, "now": now or datetime.date.today().year, "countries": countries or {},
            "table": table if table is not None else load(TABLE), "index": index if index is not None else load(INDEX),
            "countries_table": countries_table if countries_table is not None else load(PLACE_COUNTRIES)}


def run(ctx, story, families):
    """Apply to the documents in place. -> report {cards: [...], lines: {era|era+today|today|none: n}, silent: {why: n}, ...}."""
    cards, lanes = cards_of(story, families)
    rep = {"cards": [], "lines": {}, "eraSilent": {}, "lineNotes": [], "lanes": lanes, "svgs": []}
    for where, i, c in cards:
        fl, notes = card_flags(ctx, c)
        if fl:
            c["flags"] = fl
        else:
            c.pop("flags", None)
        for f in fl:
            rep["cards"].append({"where": where, "card": i + 1, "name": c.get("name"), "line": f["line"], "kind": f["kind"], "place": f["place"],
                                 "label": f["label"], "svg": f["svg"]})
            if f["svg"] not in rep["svgs"]:
                rep["svgs"].append(f["svg"])
        for line, place, ewhy, twhy, kind in notes:
            rep["lines"][kind] = rep["lines"].get(kind, 0) + 1
            if kind == "none":
                rep["eraSilent"][twhy] = rep["eraSilent"].get(twhy, 0) + 1
            rep["lineNotes"].append({"where": where, "card": i + 1, "line": line, "place": place, "drawn": kind, "era": ewhy, "today": twhy})
    rep["svgs"].sort()
    return rep


def print_report(rep):
    print(f"ribbonflags: {len(rep['cards'])} flags on {len({(c['where'], c['card']) for c in rep['cards']})} cards; place lines by what they draw: "
          + ", ".join(f"{k} {v}" for k, v in sorted(rep["lines"].items())))
    for c in rep["cards"]:
        print(f"  flag   {c['where']} #{c['card']} {c['line']:6} {c['kind']:5} {c['place']!r}: {c['label']}  [{c['svg']}]")
    for n in rep["lineNotes"]:
        if n["drawn"] == "none":
            print(f"  none   {n['where']} #{n['card']} {n['line']:6} {n['place']!r}: no country ({n['today']}); era: {n['era']}")
    if rep["lanes"]:
        print(f"  families drawn from a lane (no stored cards, no flags): {', '.join(map(str, rep['lanes']))}")
    print(f"  flag files used: {len(rep['svgs'])}")


# ---- the kit's copy of the artwork ----------------------------------------------------------------------------------------
def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sync_atlas(atlas_public, write):
    """Read the Atlas's contract (context.json, `countries` = the Flags Atlas's flag eras) and fl/*.svg; check the table against them;
    copy the flags the table can actually draw for some year of some region era into kit/data/flags, and list them in index.json."""
    cpath = os.path.join(atlas_public, "context.json")
    raw = open(cpath, "rb").read()
    contract = json.loads(raw)
    table = load(TABLE)
    by_id = {}
    for co in contract.get("countries") or []:
        for e in co.get("eras") or []:
            by_id[e["id"]] = (co, e)
    errors, noart = [], set()
    named = set()
    for k, v in list((table.get("regimes") or {}).items()) + list((table.get("eras") or {}).items()):
        for fid in v.get("flags") or []:
            named.add(fid)
            if fid not in by_id:
                errors.append(f"{k}: {fid} is not a flag era in the contract")
            elif not os.path.exists(os.path.join(atlas_public, "fl", fid + ".svg")):
                noart.add(fid)          # the Atlas has no image for it: it cannot be drawn, and its years are silent
            elif fid in (table.get("withheld") or {}):
                errors.append(f"{k}: {fid} is withheld and must not be listed")
    known_regimes = {e["regime"] for r in contract.get("regions") or [] for e in r.get("eras") or []}
    for k in table.get("regimes") or {}:
        if k not in known_regimes:
            errors.append(f"regime {k} is not a regime of the contract")
    era_ids = {e["id"] for r in contract.get("regions") or [] for e in r.get("eras") or []}
    for k in table.get("eras") or {}:
        if k not in era_ids:
            errors.append(f"era {k} is not a region era of the contract")
    for m in sorted(known_regimes - set(table.get("regimes") or {})):
        errors.append(f"regime {m} of the contract is not in the table (say [] if it has no flag)")
    if errors:
        for e in errors:
            print("  ERROR", e)
        return 1
    # the full index first (every named flag), then keep only those some year of some region era can pick
    full = {"flags": {}}
    for fid in sorted(named):
        co, e = by_id[fid]
        full["flags"][fid] = {"file": None if fid in noart else fid + ".svg", "country": co.get("slug"), "from": e.get("from"), "to": e.get("to"),
                              "present": e.get("present") is True, "polity": e.get("polity"), "evidence": e.get("evidence"), "page": e.get("url")}
    now = datetime.date.today().year
    used = set()
    for r in contract.get("regions") or []:
        for e in r.get("eras") or []:
            fr, to = e.get("from"), e.get("to")
            if not isinstance(fr, int):
                continue
            for y in range(max(fr, 1000), (to if isinstance(to, int) else now + 1)):
                fid, why = pick(table, full, e["id"], e["regime"], y)
                if fid:
                    used.add(fid)
    # today's flags: the present flag of each country page the place table or a region can name
    pc = load(PLACE_COUNTRIES)
    region_cc = {r["id"]: list(r.get("countries") or []) for r in contract.get("regions") or []}
    today = {}
    for cc in sorted(set(pc["countries"]) | {c for v in region_cc.values() for c in v}):
        meta = pc["countries"].get(cc)
        co = next((x for x in contract.get("countries") or [] if meta and x.get("slug") == meta["slug"]), None)
        pres = [e for e in (co or {}).get("eras") or [] if e.get("to") is None and e.get("present") is True]
        if len(pres) != 1 or pres[0].get("evidence") not in (table.get("evidence") or []) or not os.path.exists(os.path.join(atlas_public, "fl", pres[0]["id"] + ".svg")):
            continue
        e = pres[0]
        today[cc] = e["id"]
        full["flags"].setdefault(e["id"], {"file": e["id"] + ".svg", "country": co.get("slug"), "from": e.get("from"), "to": None, "present": True,
                                           "polity": e.get("polity"), "evidence": e.get("evidence"), "page": e.get("url")})
        used.add(e["id"])
    index = {"about": "The Flags Atlas artwork the ribbon flags can draw: copied by kit/tools/ribbonflags.py --sync-atlas from the Record Atlas "
                      "(site/public/fl/<id>.svg), only the flags kit/data/regime-flags.json can pick for some year of some region era. "
                      "The art is David Defranceski's own project's (the Flags Atlas), drawn for him; it is used on his own archive sites with "
                      "his say, and NO open licence is claimed for it. Credit wherever it is shown: '" + CREDIT + "'.",
             "credit": CREDIT,
             "licence": "No open licence. The Flags Atlas's own art, used on David Defranceski's archive sites with his permission (27 October 2026).",
             "contract": {"name": (contract.get("contract") or {}).get("name"), "version": (contract.get("contract") or {}).get("version"),
                          "generated": contract.get("generated"), "sha256": hashlib.sha256(raw).hexdigest()},
             "flags": {}}
    for fid in sorted(used):
        rec = dict(full["flags"][fid])
        rec["sha256"] = sha(os.path.join(atlas_public, "fl", fid + ".svg"))
        index["flags"][fid] = rec
    for fid in sorted(noart):
        index["flags"][fid] = dict(full["flags"][fid], sha256=None)   # listed for its years only: a year it covers is silent ("no-art")
    index["unpicked"] = sorted(named - used - noart)                  # named in the table, but no year of any region era can pick it
    index["today"] = today                                             # {cc: the present flag of that country's Flags Atlas page}
    index["regionCountries"] = region_cc                               # {region: [cc]}: the countries a region's ground lies in today
    unused = sorted(named - used - noart - set(today.values()))
    print(f"sync-atlas: contract {index['contract']['version']}; the table names {len(named)} flags; {len(used)} can be drawn; "
          f"{len(noart)} have no image in the Atlas: {', '.join(sorted(noart)) or '-'}; "
          f"{len(unused)} cannot be picked (evidence, overlap or no region era in their years): {', '.join(unused) or '-'}")
    if not write:
        return 0
    os.makedirs(FLAG_DIR, exist_ok=True)
    for f in os.listdir(FLAG_DIR):
        if f.endswith(".svg") and f[:-4] not in used:
            os.remove(os.path.join(FLAG_DIR, f))
    for fid in sorted(used):
        shutil.copyfile(os.path.join(atlas_public, "fl", fid + ".svg"), os.path.join(FLAG_DIR, fid + ".svg"))
    dump(INDEX, index)
    print(f"  wrote {len(used)} svgs and {os.path.relpath(INDEX, KIT)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sync-atlas", metavar="ATLAS_PUBLIC")
    ap.add_argument("--snapshot")
    ap.add_argument("--story")
    ap.add_argument("--family-lines")
    ap.add_argument("--alias")
    ap.add_argument("--countries", help="the archive's own {card place text: country code | null} table for today's flag")
    ap.add_argument("--now", type=int)
    ap.add_argument("--report")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.sync_atlas:
        return sync_atlas(a.sync_atlas, a.write)
    if not a.snapshot or not (a.story or a.family_lines):
        ap.error("--snapshot and at least one of --story, --family-lines")
    try:
        snap = load(a.snapshot)
        story = load(a.story) if a.story else None
        fams = load(a.family_lines) if a.family_lines else None
        alias = load(a.alias) if a.alias else {}
        countries = load(a.countries) if a.countries else {}
    except (OSError, ValueError) as e:
        print(f"ribbonflags: cannot read an input: {e}", file=sys.stderr)
        return 2
    alias = {k: v for k, v in alias.items() if not k.startswith("_")}
    ctx = context(snap, alias, a.now, countries={k: v for k, v in countries.items() if not k.startswith("_")})
    before = (copy.deepcopy(story), copy.deepcopy(fams))
    rep = run(ctx, story, fams)
    print_report(rep)
    if a.report:
        dump(a.report, rep)
    if a.check:
        if (story, fams) != before:
            print("ribbonflags: the cards' flags are not what the snapshot and the kit's table make: run with --write", file=sys.stderr)
            return 1
        return 0
    if a.write:
        if a.story:
            dump(a.story, story)
        if a.family_lines:
            dump(a.family_lines, fams)
    return 0


if __name__ == "__main__":
    sys.exit(main())
