#!/usr/bin/env python3
"""The gate on the mini flags of the ribbon cards (components/FlagMini.astro; the contract is kit/docs/ribbon-flags.md).

WHY. A flag beside "from Senj" says, without a word, "this is who held Senj in that card's year". It is the "at the time" note
in a picture, and a picture is believed faster and checked less. So every flag a card carries is RECOMPUTED here, independently
of the generator that wrote it (kit/tools/ribbonflags.py), from the archive's era snapshot (the same rules as the era notes,
kit/tools/eralib.py), the kit's table of which flag stands for which regime (kit/data/regime-flags.json) and the kit's copy of
the Flags Atlas's flag years and artwork (kit/data/flags/index.json, kit/data/flags/*.svg); a flag where those say nothing fails.

    python3 checkribbonflags.py --snapshot src/data/era-snapshot.json [--story src/data/story.json] [--family-lines src/data/family-lines.json]
                                [--alias src/data/flag-places.json] [--dist dist] [--now 2026]
    python3 checkribbonflags.py --kit-only        the kit's own files: R1 and R8 only
    python3 checkribbonflags.py --selftest        build cards, pass them, then plant every fault and see each one caught

Rules (the code is printed with every finding):
  R1  the flag's file is in kit/data/flags and listed in index.json with that file and sha256; every svg there is listed; every listed
      drawable flag has its file
  R2  a flag has a label (and, built, an alt and a title that are that label)
  R3  a flag's kind is era or today and its line from, at or spouse; one of each kind per line at most; the card's line names its place
  R4  a flag where the era rules are silent (contested, edge, unassessed, a boundary year, the quiet rule, no region, no flag ...)
  R5  an era flag on a living or minor card (or a living spouse's line), or a today flag (or a living line's) with a year
      (today's flag: the country the place is in now, by the card's words, the archive's table or a one-country region, the kit's
      data/place-countries.json; never a name two countries have)
  R6  a flag that differs from the independent recompute (file, flag, era, year, label, grade, assessed)
  R7  a card without the flag the recompute gives it (run ribbonflags.py --write)
  R8  the kit's table names only flags the index accounts for, never a withheld one, and the index draws only the evidence the table allows
  R10 a today flag beside an era flag of the same country (never two flags of one country on a line)
  R9  (with --dist) every built img.flag-mini has alt == title, not empty, its lines, and sits in a ribbon card; a page with one carries
      the credit; a built flag on a data-living="1" card names no year
Exit 0 clean, 1 on any finding, 2 when an input cannot be read or nothing was checked.
"""
import argparse, copy, datetime, hashlib, json, math, os, re, shutil, sys, tempfile
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import eralib  # noqa: E402

CREDIT = "Flags: Flags Atlas, by David Defranceski, drawn for this project"
WORDS = ": flag as in Flags Atlas"
EVIDENCE_TAIL = {"reconstructed": " (reconstructed)", "symbolic": " (an emblem)"}


def read(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ---- the independent recompute (deliberately not imported from ribbonflags.py) --------------------------------------------
def four(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if 1000 <= v <= 2999 else None
    s = "" if v is None else str(v).strip()
    return int(s) if len(s) == 4 and s.isdigit() else None


def year_of(card, line):
    at = four(card.get("atYear"))
    if line == "at":
        return at
    if line == "spouse" and card.get("spouseOriginYear") not in (None, ""):
        return four(card.get("spouseOriginYear"))
    if line == "spouse":
        line = "from"
    if card.get("originYear") not in (None, ""):
        return four(card.get("originYear"))
    m = re.match(r"^(?:named\s+)?(\d{4})(?:\s*[–—-].*)?$", str(card.get("years") or "").strip())
    return int(m.group(1)) if m else at


def place_of(card, line):
    s = str({"from": card.get("origin"), "at": card.get("atPlace"), "spouse": card.get("spouseOrigin")}.get(line) or "").strip()
    if line == "spouse":
        s = re.sub(r"^(?:of|from)\s+", "", s, flags=re.I).strip()
    return s


def living_of(card, line):
    return bool(card.get("living") or card.get("minor") or (line == "spouse" and (card.get("spouseLiving") or card.get("spouseMinor"))))


def flag_in_year(table, index, era_id, regime, year):
    eras_t, reg_t = table.get("eras") or {}, table.get("regimes") or {}
    names = eras_t[era_id]["flags"] if era_id in eras_t else (reg_t[regime]["flags"] if regime in reg_t else None)
    if not names:
        return None, "no-table" if names is None else "no-flag"
    hits = []
    for fid in names:
        rec = (index.get("flags") or {}).get(fid)
        if fid in (table.get("withheld") or {}) or rec is None:
            continue
        lo, hi = rec.get("from"), rec.get("to")
        if isinstance(lo, int) and lo <= year and ((hi is None and rec.get("present") is True) or (isinstance(hi, int) and year < hi)):
            hits.append(fid)
    if len(hits) != 1:
        return None, "no-flag-for-year" if not hits else "flags-overlap"
    rec = index["flags"][hits[0]]
    if not rec.get("file"):
        return None, "no-art"
    if rec.get("evidence") not in (table.get("evidence") or []):
        return None, "evidence"
    return hits[0], "ok"


def _resolve(ctx, look, year, rf):
    snap = ctx["snapshot"]
    era = eralib.era_at(snap, look, year, recent_from=rf)
    if era is None:
        return None, None, eralib.why_not(snap, look, year, recent_from=rf)
    if era["boundary"] or era["contested"]:
        return era, None, "boundary" if era["boundary"] else "contested"
    regime = next((e.get("regime") for e in snap["regions"][era["region"]] if e.get("id") == era["id"]), None)
    fid, why = flag_in_year(ctx["table"], ctx["index"], era["id"], regime, year)
    if fid is None:
        return era, None, why
    if era["edgeAgree"]:
        for nb in ((snap.get("edge_neighbours") or {}).get(era["place"]) or {}).get("regions") or []:
            cov = [e for e in snap["regions"].get(nb) or [] if eralib.numeric(e) and eralib.covers(e, year)]
            if len(cov) != 1 or flag_in_year(ctx["table"], ctx["index"], cov[0]["id"], cov[0].get("regime"), year)[0] != fid:
                return era, None, "edge-flag"
    return era, fid, "ok"


PHRASES = {"from": "from {}", "at": "at {}", "spouse": "spouse of {}"}


def nation(ctx, card, line, place):
    """Today's country of a place, by the contract (the card's words; the archive's table or single-country region; the kit's table;
    never a name two countries have, never two answers)."""
    pc = ctx["countries_table"]
    parts = [eralib.fold(x) for x in place.split(",") if eralib.fold(x)]
    named = {cc for cc, m in pc["countries"].items() for x in parts if x in m["aliases"]}
    if named:
        return named.pop() if len(named) == 1 else None
    if place in ctx["countries"]:
        return ctx["countries"][place] if ctx["countries"][place] in pc["countries"] else None
    found = set()
    look = ctx["alias"].get(place, place) if place in ctx["alias"] else place
    reg = (ctx["snapshot"].get("places") or {}).get(eralib.fold(look or ""))
    rc = (ctx["index"].get("regionCountries") or {}).get(reg) or [] if reg else []
    if len(rc) == 1:
        found.add(rc[0])
    whole = eralib.fold(place)
    if whole in pc["places"]:
        found.add(pc["places"][whole])
    elif whole not in set(pc.get("ambiguous") or []):
        found.update(pc["places"][x] for x in parts if x in pc["places"])
    return found.pop() if len(found) == 1 else None


def recompute_line(ctx, card, line):
    """-> the flags the line should carry (era first, then today's where it is another country's), as the generator writes them."""
    place = place_of(card, line)
    if not place:
        return []
    say = PHRASES[line].format(place)
    grade = card.get("originGrade") if card.get("originGrade") in ("doc", "inf", "lore") else "doc"
    out = []
    look = place
    if place in ctx["alias"]:
        look = ctx["alias"][place]
    if look is not None and not living_of(card, line):
        year = year_of(card, line)
        if year is not None and year <= ctx["now"]:
            era, fid, _ = _resolve(ctx, look, year, None)
            if fid and era["assessed"]:
                rec = ctx["index"]["flags"][fid]
                out.append({"kind": "era", "line": line, "place": place, "svg": rec["file"], "flag": fid, "era": era["id"], "year": year,
                            "label": f"{say}, {year}: {era['label']} then{EVIDENCE_TAIL.get(rec.get('evidence'), '')}", "grade": grade, "assessed": True})
    cc = nation(ctx, card, line, place)
    fid = (ctx["index"].get("today") or {}).get(cc) if cc else None
    if fid:
        rec = ctx["index"]["flags"][fid]
        if not (out and one_country(ctx["index"], out[0]["flag"], fid)):
            out.append({"kind": "today", "line": line, "place": place, "svg": rec["file"], "flag": fid, "country": cc, "year": None,
                        "label": f"{say}: {ctx['countries_table']['countries'][cc]['name']} today{EVIDENCE_TAIL.get(rec.get('evidence'), '')}", "grade": grade})
    return out


def one_country(index, a, b):
    fa, fb = index["flags"].get(a) or {}, index["flags"].get(b) or {}
    return a == b or (fa.get("country") and fa.get("country") == fb.get("country")) or (fa.get("sha256") and fa.get("sha256") == fb.get("sha256"))


def recompute_card(ctx, card):
    return {line: recompute_line(ctx, card, line) for line in ("from", "at", "spouse")}


# ---- the checks --------------------------------------------------------------------------------------------------------
class Findings:
    def __init__(self):
        self.items = []

    def add(self, code, where, msg):
        self.items.append((code, where, msg))

    def codes(self):
        return {c for c, _, _ in self.items}


def check_kit(table, index, flag_dir, out):
    flags = index.get("flags") or {}
    files = {f for f in os.listdir(flag_dir) if f.endswith(".svg")} if os.path.isdir(flag_dir) else set()
    listed = set()
    for fid, rec in flags.items():
        if rec.get("file"):
            listed.add(rec["file"])
            p = os.path.join(flag_dir, rec["file"])
            if rec["file"] != fid + ".svg":
                out.add("R1", fid, f"index lists file {rec['file']!r} for flag {fid}")
            if not os.path.exists(p):
                out.add("R1", fid, "listed in index.json but its svg is missing")
            elif hashlib.sha256(open(p, "rb").read()).hexdigest() != rec.get("sha256"):
                out.add("R1", fid, "the svg is not the file index.json lists (sha256)")
            if rec.get("evidence") not in (table.get("evidence") or []):
                out.add("R8", fid, f"a drawable flag of evidence {rec.get('evidence')!r}, which the table does not allow")
    for f in sorted(files - listed):
        out.add("R1", f, "an svg in kit/data/flags that index.json does not list")
    known = set(flags) | set(index.get("unpicked") or [])
    withheld = table.get("withheld") or {}
    for k, v in list((table.get("regimes") or {}).items()) + list((table.get("eras") or {}).items()):
        for fid in v.get("flags") or []:
            if fid in withheld:
                out.add("R8", k, f"names the withheld flag {fid}")
            if fid not in known:
                out.add("R8", k, f"names {fid}, which index.json does not account for (run ribbonflags.py --sync-atlas)")
    for fid in withheld:
        if fid in flags and flags[fid].get("file"):
            out.add("R8", fid, "a withheld flag has its art in the kit")


def check_cards(ctx, cards, out):
    n = 0
    for where, i, card in cards:
        tag = f"{where} card {i + 1} ({card.get('name')})"
        have = card.get("flags") or []
        if not isinstance(have, list):
            out.add("R3", tag, "flags is not a list")
            continue
        want = recompute_card(ctx, card)
        bykey = {}
        for f in have:
            n += 1
            if not isinstance(f, dict):
                out.add("R3", tag, "a flag that is not an object")
                continue
            line, kind = f.get("line"), f.get("kind")
            if line not in ("from", "at", "spouse") or kind not in ("era", "today"):
                out.add("R3", tag, f"a flag of kind {kind!r} on the line {line!r}")
                continue
            if (line, kind) in bykey:
                out.add("R3", tag, f"two {kind} flags on the {line} line")
            bykey[(line, kind)] = f
            if not isinstance(f.get("label"), str) or not f["label"].strip():
                out.add("R2", tag, f"the {line} {kind} flag has no label")
            if f.get("svg") and f["svg"] not in {r.get("file") for r in ctx["index"]["flags"].values()}:
                out.add("R1", tag, f"the {line} flag's file {f.get('svg')!r} is not in kit/data/flags")
            shown = place_of(card, line)
            if not shown or f.get("place") != shown:
                out.add("R3", tag, f"the {line} flag names {f.get('place')!r} and the card's {line} line names {shown!r}")
            if (living_of(card, line) and kind == "era") or ((living_of(card, line) or kind == "today") and (
                    f.get("year") is not None or re.search(r"(?<!\d)\d{4}(?!\d)", str(f.get("label") or "")))):
                out.add("R5", tag, f"a {kind} flag with a year, or an era flag on a living line: {f.get('label')!r}")
            exp = next((x for x in want.get(line, []) if x["kind"] == kind), None)
            if exp is None:
                if kind == "today" and any(x["kind"] == "era" and one_country(ctx["index"], x["flag"], f.get("flag")) for x in want.get(line, [])):
                    out.add("R10", tag, f"a today flag beside an era flag of the same country on the {line} line")
                else:
                    out.add("R4", tag, f"a {line} {kind} flag where the rules are silent")
                continue
            for k in exp:
                if k not in ("kind", "line", "place") and f.get(k) != exp[k]:
                    out.add("R6", tag, f"the {line} {kind} flag's {k} is {f.get(k)!r}, the recompute says {exp[k]!r}")
        for line, fl in want.items():
            for x in fl:
                if (line, x["kind"]) not in bykey:
                    out.add("R7", tag, f"no {line} {x['kind']} flag, and the recompute gives {x['label']!r} (run ribbonflags.py --write)")
    return n


class Built(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.flags, self.credit, self._cr = [], [], False, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img" and "flag-mini" in (a.get("class") or "").split():
            card = next((s for s in reversed(self.stack) if s[0] == "li"), None)
            self.flags.append((a, card[1] if card else None))
        if a.get("data-flag-credit") == "1":
            self._cr += 1
        if tag not in ("img", "br", "meta", "link", "input", "source", "hr"):
            self.stack.append((tag, a))

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break

    def handle_data(self, d):
        if self._cr and CREDIT in d:
            self.credit = True


def check_dist(dist, out):
    n = 0
    for d, _, fs in os.walk(dist):
        for f in fs:
            if not f.endswith(".html"):
                continue
            p = os.path.join(d, f)
            b = Built()
            b.feed(open(p, encoding="utf-8", errors="replace").read())
            rel = os.path.relpath(p, dist)
            for a, card in b.flags:
                n += 1
                alt, title = (a.get("alt") or "").strip(), (a.get("title") or "").strip()
                if not alt or alt != title:
                    out.add("R9", rel, f"a built flag whose alt {alt!r} and title {title!r} are not one non-empty label")
                if not a.get("data-flag-lines") or any(x not in ("from", "at", "spouse") for x in a["data-flag-lines"].split()):
                    out.add("R9", rel, f"a built flag with no line ({a.get('data-flag-lines')!r})")
                if card is None or not any(c in (card.get("class") or "").split() for c in ("st-rb", "fr-c")):
                    out.add("R9", rel, "a built flag outside a ribbon card")
                elif card.get("data-living") == "1" and re.search(r"(?<!\d)\d{4}(?!\d)", alt):
                    out.add("R5", rel, f"a built flag on a living card names a year: {alt!r}")
            if b.flags and not b.credit:
                out.add("R9", rel, f"a page with flags and without the credit '{CREDIT}'")
    return n


def cards_in(story, families):
    out = []
    if story is not None:
        out += [("story", i, c) for i, c in enumerate((story.get("ribbon") or {}).get("cards") or [])]
    if families is not None:
        for fam in (families.get("families") if isinstance(families, dict) else families) or []:
            out += [(f"family:{fam.get('id')}", i, c) for i, c in enumerate(fam.get("cards") or [])]
    return out


def gate(snapshot, story, families, alias=None, dist=None, now=None, table=None, index=None, flag_dir=None, countries=None):
    out = Findings()
    table = table if table is not None else read(os.path.join(KIT, "data", "regime-flags.json"))
    index = index if index is not None else read(os.path.join(KIT, "data", "flags", "index.json"))
    check_kit(table, index, flag_dir or os.path.join(KIT, "data", "flags"), out)
    ctx = {"snapshot": snapshot, "table": table, "index": index, "now": now or datetime.date.today().year,
           "alias": {k: v for k, v in (alias or {}).items() if not k.startswith("_")},
           "countries": {k: v for k, v in (countries or {}).items() if not k.startswith("_")},
           "countries_table": read(os.path.join(KIT, "data", "place-countries.json"))}
    counts = {"cards": 0, "flags": 0, "built": 0}
    if snapshot is not None:
        cards = cards_in(story, families)
        counts["cards"] = len(cards)
        counts["flags"] = check_cards(ctx, cards, out)
    if dist:
        counts["built"] = check_dist(dist, out)
    return out, counts


# ---- selftest ------------------------------------------------------------------------------------------------------------
def _era(region, fr, to, regime, label):
    return {"id": f"{region}--era-{fr}", "from": fr, "to": to, "present": to is None, "regime": regime, "label": label, "polity": label,
            "basis": "test", "seeded_from_archive": False, "approx": False, "contested": False, "assessed": True, "why": None,
            "url": f"/region/{region}/#era-{fr}", "from_margin": None, "to_margin": None, "margin_src": None, "margin_sourced": None,
            "contested_scope": "none"}


def fixture():
    snap = {"version": 5, "built": "2026-10-27", "contract": {"name": "recordatlas-context", "version": "1.13.0"},
            "atlas": {"base": "https://recordatlas.org", "rings_source": "none", "rings_sha256": None},
            "policy": {"unassessed": "refuse", "boundary": "newer", "recent_from": 1990, "edge_km": 15, "edge": "agree", "approx": "margin",
                       "contested": "scope", "margin_years": 5, "margins": {}, "ruler_polities": {}},
            "regions": {"istria-central": [_era("istria-central", 1815, 1918, "habsburg", "Habsburg / Austria–Hungary"),
                                           _era("istria-central", 1918, 1943, "italy", "Italy"),
                                           _era("istria-central", 1945, 1991, "yugo", "Yugoslavia"),
                                           _era("istria-central", 1991, None, "croatia", "Croatia")],
                        "transvaal": [_era("transvaal", 1910, 1961, "britain", "Britain and its colonies"),
                                      _era("transvaal", 1961, None, "southafrica", "South Africa")]},
            "places": {"pazin": "istria-central", "johannesburg": "transvaal"}, "places_silent": {"rijeka": "edge"}, "edge_neighbours": {},
            "unchecked_edge": [], "dropped": [], "quality": {"counts": {"gaps": 0, "overlaps": 0}, "gaps": [], "overlaps": []}, "rulers": {}}
    story = {"ribbon": {"cards": [
        {"name": "A", "years": "1830–1890", "origin": "Pazin", "originGrade": "doc", "spouse": "B", "spouseOrigin": "of Pazin", "atPlace": "Pazin", "atYear": "1880", "living": False},
        {"name": "C", "years": "1920–1980", "origin": "Pazin", "originGrade": "inf", "spouse": "D", "spouseOrigin": "of Rijeka", "atPlace": "Johannesburg", "atYear": "1950", "living": False},
        {"name": "E", "years": "", "origin": "Johannesburg", "originGrade": "doc", "spouse": "", "spouseOrigin": "", "atPlace": "", "atYear": "", "living": True},
        {"name": "F", "years": "c.1700–1760", "origin": "Nowhere", "originGrade": "lore", "spouse": "", "spouseOrigin": "", "atPlace": "", "atYear": "", "living": False}]}}
    return snap, story


def _html(story):
    """The markup the components draw (the selftest's stand-in for a build)."""
    lis = []
    for c in story["ribbon"]["cards"]:
        imgs = "".join(f'<img class="flag-mini flag-mini-{f["grade"]}" src="x" alt="{f["label"]}" title="{f["label"]}" data-flag-lines="{f["line"]}">'
                       for f in c.get("flags") or [])
        lis.append(f'<li class="st-rb" data-living="{"1" if c.get("living") else "0"}"><span>{c["name"]}</span>{imgs}</li>')
    return f'<html><body><nav class="st-rib"><ol>{"".join(lis)}</ol><p data-flag-credit="1">key. <span>{CREDIT}.</span></p></nav></body></html>'


def selftest():
    import ribbonflags
    snap, story = fixture()
    ctx = ribbonflags.context(snap, {}, 2026)
    rep = ribbonflags.run(ctx, story, None)
    labels = [(c["card"], c["line"], c["kind"], c["label"]) for c in rep["cards"]]
    expect = [(1, "from", "era", "from Pazin, 1830: Habsburg / Austria–Hungary then"), (1, "from", "today", "from Pazin: Croatia today"),
              (1, "at", "era", "at Pazin, 1880: Habsburg / Austria–Hungary then"), (1, "at", "today", "at Pazin: Croatia today"),
              (1, "spouse", "era", "spouse of Pazin, 1830: Habsburg / Austria–Hungary then"), (1, "spouse", "today", "spouse of Pazin: Croatia today"),
              (2, "from", "era", "from Pazin, 1920: Italy then"), (2, "from", "today", "from Pazin: Croatia today"),
              (2, "at", "era", "at Johannesburg, 1950: Britain and its colonies then"), (2, "spouse", "today", "spouse of Rijeka: Croatia today"),
              (3, "from", "today", "from Johannesburg: South Africa today")]
    fails = 0
    if labels != expect:
        print("FAIL the generator's flags on the fixture:", labels)
        fails += 1
    if rep["lines"] != {"era+today": 4, "era": 1, "today": 2, "none": 1}:
        print("FAIL the generator's lines on the fixture:", rep["lines"])
        fails += 1
    tmp = tempfile.mkdtemp()
    try:
        def run_case(name, mutate, want, dist=False, kit=None):
            nonlocal fails
            s = copy.deepcopy(story)
            t = read(os.path.join(KIT, "data", "regime-flags.json"))
            ix = read(os.path.join(KIT, "data", "flags", "index.json"))
            fd = os.path.join(KIT, "data", "flags")
            if mutate:
                mutate(s, t, ix)
            if kit:
                fd = os.path.join(tmp, "flags")
                shutil.rmtree(fd, ignore_errors=True)
                shutil.copytree(os.path.join(KIT, "data", "flags"), fd)
                kit(fd)
            d = None
            if dist:
                d = os.path.join(tmp, "dist")
                shutil.rmtree(d, ignore_errors=True)
                os.makedirs(os.path.join(d, "story"))
                html = _html(s)
                if callable(dist):
                    html = dist(html)
                open(os.path.join(d, "story", "index.html"), "w").write(html)
            out, counts = gate(snap, s, None, dist=d, now=2026, table=t, index=ix, flag_dir=fd)
            got = out.codes()
            ok = got == set(want)
            if not ok:
                fails += 1
            print(f"{'ok  ' if ok else 'FAIL'} {name}: want {sorted(want) or 'clean'}, got {sorted(got) or 'clean'}"
                  + ("" if ok else "\n       " + "\n       ".join(f"{c} {w}: {m}" for c, w, m in out.items)))

        def card(s, i):
            return s["ribbon"]["cards"][i]

        def first_other_svg(ix, not_this):
            return next(r["file"] for k, r in sorted(ix["flags"].items()) if r.get("file") and r["file"] != not_this)

        run_case("clean", None, [])
        run_case("clean, built", None, [], dist=True)
        run_case("R1 a flag file that is not in the kit", lambda s, t, ix: card(s, 0)["flags"][0].update(svg="nowhere-flags--era-1.svg"), ["R1", "R6"])
        run_case("R1 an svg changed after it was listed", None, ["R1"], kit=lambda fd: open(os.path.join(fd, "austria-flags--era-1804.svg"), "a").write(" "))
        run_case("R1 an svg the index does not list", None, ["R1"], kit=lambda fd: open(os.path.join(fd, "stray-flags--era-1.svg"), "w").write("<svg/>"))
        run_case("R2 a flag with no label", lambda s, t, ix: card(s, 0)["flags"][0].update(label=""), ["R2", "R6"])
        run_case("R3 a flag on a line that names another place", lambda s, t, ix: card(s, 1)["flags"][0].update(line="spouse"), ["R3", "R4", "R7"])
        run_case("R3 two flags on one line", lambda s, t, ix: card(s, 0)["flags"].append(dict(card(s, 0)["flags"][0])), ["R3"])
        run_case("R3 a flag on no line", lambda s, t, ix: card(s, 0)["flags"][0].update(line="name"), ["R3", "R7"])
        run_case("R10 today's flag beside an era flag of the same country", lambda s, t, ix: card(s, 1)["flags"].append(dict(
            card(s, 2)["flags"][0], line="at", place="Johannesburg")), ["R10"])
        run_case("R5 an era flag on a living card", lambda s, t, ix: card(s, 2)["flags"].insert(0, dict(
            card(s, 1)["flags"][2], line="from", place="Johannesburg")), ["R5", "R4"])
        run_case("R4 a flag where the place is silent (edge)", lambda s, t, ix: card(s, 1)["flags"].append(
            dict(card(s, 1)["flags"][0], line="spouse", place="Rijeka")), ["R4"])
        run_case("R4 a flag where the place has no region", lambda s, t, ix: card(s, 3).update(flags=[
            dict(card(s, 2)["flags"][0], place="Nowhere", grade="lore")]), ["R4"])
        run_case("R4 an era flag on a year the era rules refuse", lambda s, t, ix: card(s, 3).update(origin="Pazin", years="1944–1990", flags=[
            dict(card(s, 1)["flags"][0], place="Pazin", year=1944, grade="lore"), dict(card(s, 1)["flags"][1], grade="lore")]), ["R4"])
        run_case("R4 today's flag for a name two countries have (Córdoba)", lambda s, t, ix: card(s, 3).update(origin="Córdoba", flags=[
            dict(card(s, 2)["flags"][0], place="Córdoba", svg="spain-flags--era-1975.svg", flag="spain-flags--era-1975", country="ES",
                 label="from Córdoba: Spain today", grade="lore")]), ["R4"])
        run_case("R6 today's flag of the wrong country", lambda s, t, ix: card(s, 2)["flags"][0].update(
            svg="argentina-flags--era-1861.svg", flag="argentina-flags--era-1861"), ["R6"])
        run_case("R5 a living card's flag with a year", lambda s, t, ix: card(s, 2)["flags"][0].update(
            label="from Johannesburg, 2026: South Africa", year=2026), ["R5", "R6"])
        run_case("R6 the wrong flag", lambda s, t, ix: card(s, 0)["flags"][0].update(svg=first_other_svg(ix, card(s, 0)["flags"][0]["svg"])), ["R6"])
        run_case("R6 a flag that hides the card's evidence", lambda s, t, ix: card(s, 1)["flags"][0].update(grade="doc"), ["R6"])
        run_case("R6 a flag on the wrong era", lambda s, t, ix: card(s, 0)["flags"][0].update(era="istria-central--era-1918"), ["R6"])
        run_case("R7 a flag left off", lambda s, t, ix: card(s, 0)["flags"].pop(0), ["R7"])
        run_case("R8 the table names a withheld flag", lambda s, t, ix: t["regimes"]["italy"]["flags"].append("italy-flags--era-1943"), ["R8"])
        run_case("R8 the table names a flag the kit does not hold", lambda s, t, ix: t["regimes"]["yugo"]["flags"].append("atlantis-flags--era-1"), ["R8"])
        run_case("R8 a drawable flag of an evidence the table refuses", lambda s, t, ix: ix["flags"]["australia-flags--era-1901"].update(evidence="unconfirmed"), ["R8"])
        run_case("R9 a built flag with no alt", None, ["R9"], dist=lambda h: h.replace('alt="from Pazin, 1920: Italy then"', 'alt=""', 1))
        run_case("R9 a page with flags and no credit", None, ["R9"], dist=lambda h: h.replace(CREDIT, "Flags"))
        run_case("R9 a built flag outside a card", None, ["R9"], dist=lambda h: h.replace("</ol>", '</ol><img class="flag-mini" alt="x" title="x" data-flag-lines="from">'))
        run_case("R5 a built living card's flag naming a year", None, ["R5"], dist=lambda h: h.replace(
            'alt="from Johannesburg: South Africa today"', 'alt="from Johannesburg, 2026: South Africa"').replace(
            'title="from Johannesburg: South Africa today"', 'title="from Johannesburg, 2026: South Africa"'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"checkribbonflags selftest: {'all faults caught' if not fails else str(fails) + ' FAILED'}")
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--snapshot")
    ap.add_argument("--story")
    ap.add_argument("--family-lines")
    ap.add_argument("--alias")
    ap.add_argument("--countries")
    ap.add_argument("--dist")
    ap.add_argument("--now", type=int)
    ap.add_argument("--kit-only", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    try:
        snap = read(a.snapshot) if a.snapshot else None
        story = read(a.story) if a.story else None
        fams = read(a.family_lines) if a.family_lines else None
        alias = read(a.alias) if a.alias else {}
        countries = read(a.countries) if a.countries else {}
    except (OSError, ValueError) as e:
        print(f"checkribbonflags: cannot read an input: {e}", file=sys.stderr)
        return 2
    if not a.kit_only and (snap is None or (story is None and fams is None)):
        ap.error("--snapshot and --story or --family-lines (or --kit-only)")
    out, counts = gate(None if a.kit_only else snap, story, fams, alias, a.dist, a.now, countries=countries)
    for c, w, m in out.items:
        print(f"  {c} {w}: {m}")
    print(f"checkribbonflags: {counts['cards']} cards, {counts['flags']} flags in the data"
          + (f", {counts['built']} built" if a.dist else "") + f"; {len(out.items)} findings")
    if not a.kit_only and counts["cards"] == 0:
        return 2
    return 1 if out.items else 0


if __name__ == "__main__":
    sys.exit(main())
