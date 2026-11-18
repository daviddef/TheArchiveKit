#!/usr/bin/env python3
"""Self-test for samepersoncore.py / samepersoncandidates.py. INVENTED people, places and spellings only: nothing here is a
real person, and no catalogue file is read (the Atlas documents below are tiny stand-ins with the same shape).

    python3 kit/tools/samepersoncandidates_selftest.py
"""
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samepersoncore as core  # noqa: E402
import samepersoncandidates as cli  # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


# ---- stand-ins for the Atlas catalogues (same shape as data/*.json; invented families)
SUR = {"families": [
    {"id": "tessarin", "name": "Tessarin", "members": [
        {"form": "Tessarin", "status": "same"}, {"form": "Tessarini", "status": "attested"},
        {"form": "Tesarin", "status": "lead"}, {"form": "Tessarino", "status": "case-by-case"}],
     "notSame": [{"form": "Tessari"}]}]}
GIV = {"families": [
    {"id": "giovanni", "name": "Giovanni", "members": [
        {"form": "Giovanni", "status": "attested"}, {"form": "Joannes", "status": "attested"}, {"form": "Ivan", "status": "attested"},
        {"form": "Zuane", "status": "attested"}]},
    {"id": "battista", "name": "Battista", "members": [{"form": "Battista", "status": "attested"}, {"form": "Baptista", "status": "attested"}]},
    {"id": "maria", "name": "Maria", "members": [{"form": "Maria", "status": "attested"}, {"form": "Marija", "status": "attested"}]},
    {"id": "aldo", "name": "Aldo", "members": [{"form": "Aldo", "status": "attested"}]},
]}
NAMES = {"places": [{"id": "marenza", "name": "Marenza", "names": [{"name": "Borgovecchio", "from": None, "to": 1900}]}]}
PM = {"Marenza": {"name": "Marenza", "lat": 45.00, "lon": 14.00, "atlas_id": "marenza"},
      "Corvalle": {"name": "Corvalle", "lat": 45.05, "lon": 14.02, "atlas_id": "corvalle"},
      "Brisca": {"name": "Brisca", "lat": 46.90, "lon": 15.80, "atlas_id": "brisca"}}


def P(i, given, sur, by, bp, sex="m", dy=None, father=None, mother=None, spouse=(), kids=(), bye=False, dye=False, bpe=False, fg=None, mg=None):
    return {"id": i, "sex": sex, "given": given, "sur": sur, "by": by, "bp": bp, "dy": dy if dy else (by + 60 if by else None),
            "dp": bp, "father": father, "mother": mother, "spouse": list(spouse), "kids": list(kids), "bye": bye, "dye": dye if dy else True,
            "bpe": bpe, "fg": fg, "mg": mg, "route": []}


def tree():
    return [
        P("aldo-1800", "Aldo", "Tessarin", 1800, "Marenza", dy=1860, spouse=["rosa-1805"], kids=["pietro-1830", "lucia-1833", "antonio-1836"]),
        P("rosa-1805", "Rosa", "Bellan", 1805, "Marenza", "f", dy=1872, spouse=["aldo-1800"], kids=["pietro-1830", "lucia-1833", "antonio-1836"]),
        P("pietro-1830", "Pietro", "Tessarin", 1830, "Marenza", dy=1890, father="aldo-1800", mother="rosa-1805"),
        P("lucia-1833", "Lucia", "Tessarin", 1833, "Marenza", "f", dy=1899, father="aldo-1800", mother="rosa-1805"),
        P("antonio-1836", "Antonio", "Tessarin", 1836, "Marenza", dy=1901, father="aldo-1800", mother="rosa-1805"),
        # the orphan: born 1839 in Marenza
        P("giovanni-1839", "Giovanni", "Tessarin", 1839, "Marenza", dy=1900),
        # decoys
        P("aldo-1750", "Aldo", "Tessarin", 1750, "Marenza", dy=1790),                     # namesake, dead before the birth
        P("aldo-1798", "Aldo", "Tessarini", 1798, "Corvalle", dy=1870),                   # cousin of one name, a village over
        P("aldo-1801", "Aldo", "Tessari", 1801, "Marenza", dy=1860),                      # a different name (not-same)
        P("aldo-1803", "Aldo", "Tessarin", 1803, "Brisca", dy=1870),                      # right name, far away
        P("rosa-1812", "Rosa", "Moro", 1812, "Brisca", "f", dy=1870),                     # far away
        # a living person: never a subject, never a candidate
        P("living-1990", "Aldo", "Tessarin", 1990, "Marenza", dy=None),
    ]


def ctx_for(people=None, strict=False, cat=True, block_est=True):
    return core.Context(people or tree(), core.Catalogue(SUR, GIV) if cat else core.Catalogue(),
                        core.Places(PM, NAMES), strict=strict, today_year=2026, block_with_estimates=block_est)


def test_names():
    c = core.Catalogue(SUR, GIV)
    check(c.surname_relation("De Tessarin", "de-Tessarin")[0] == "same-form", "typography is never a spelling")
    check(c.surname_relation("Tessarin", "Tessarini")[0] == "catalogue", "attested spelling is a catalogue match")
    check(c.surname_relation("Tessarin", "Tesarin")[0] == "lead", "a lead is weak")
    check(c.surname_relation("Tessarin", "Tessarino")[0] == "case-by-case", "case-by-case is neutral")
    check(c.surname_relation("Tessarin", "Tessari")[0] == "not-same", "not-same blocks")
    check(c.surname_relation("Tessarin", "Tessarín")[0] == "fold", "an accent is a spelling: reported as a fold, not as the same form")
    check(c.surname_relation("Tessarin", "Moro")[0] == "different", "unrelated names")
    check(c.surname_relation("", "Moro")[0] == "unknown", "no surname is unknown, not different")
    check(c.given_relation("Giovanni", "Joannes")[0] == "same-name", "Giovanni = Joannes")
    check(c.given_relation("Zuane", "Ivan")[0] == "same-name", "Zuane = Ivan through the family")
    check(c.given_relation("Maria Anna", "Maria Teresa")[0] == "partial", "Maria Anna is not Maria Teresa")
    check(c.same_full_name("Giovanni Battista", "Joannes Baptista"), "whole names match form by form")
    check(not c.same_full_name("Giovanni", "Giovanni Battista"), "a shorter name is not the whole name")
    plain = core.Catalogue()
    check(plain.surname_relation("Tessarin", "Tessarini")[0] == "different", "without the catalogue only spelling and accent are compared")
    check(plain.given_relation("Giovanni", "Joannes")[0] == "different", "without the catalogue Giovanni and Joannes are not joined")


def test_places():
    pl = core.Places(PM, NAMES)
    check(pl.resolve("Borgovecchio", 1850)["key"] == "marenza", "an old name resolves to the Atlas place of its year")
    check(pl.resolve("Borgovecchio", 1950) is None, "the old name does not resolve after its last year")
    check(pl.relation(pl.resolve("Marenza"), pl.resolve("Marenza"))[0] == "same", "same place")
    check(pl.relation(pl.resolve("Marenza"), pl.resolve("Corvalle"))[0] == "near", "a village over is within 25 km")
    check(pl.relation(pl.resolve("Marenza"), pl.resolve("Brisca"))[0] == "far", "far")
    check(pl.relation(pl.resolve("Marenza"), None)[0] == "unknown", "an unresolved place is unknown")


def test_father_and_mother():
    ctx = ctx_for()
    ctx.hide = "giovanni-1839"
    res = core.rank(ctx, "giovanni-1839", "father")
    ids = [r["id"] for r in res["candidates"]]
    check(ids[0] == "aldo-1800", "the right father ranks first, got %s" % ids[:3])
    check("aldo-1750" not in ids, "a man dead before the birth is blocked")
    check("aldo-1801" not in ids, "a not-same surname is blocked")
    check("living-1990" not in ids, "a living person is never a candidate")
    top = res["candidates"][0]
    check(top["namesakes"] >= 2, "namesakes are counted (the cousin of one name, the man far away): %s" % top["namesakes"])
    check(any("same place" in x["why"] or "same place" in x["why"].lower() for x in top["signals"]), "the reasons are written out")
    mres = core.rank(ctx, "giovanni-1839", "mother")
    check(mres["candidates"][0]["id"] == "rosa-1805", "the right mother ranks first")
    check(any("husband bears this person's surname" in x["why"] for x in mres["candidates"][0]["signals"]), "a mother is scored by her husband's surname")
    # the mother's own maiden name is not evidence: a Tessarin-named stranger is not preferred to Rosa
    check(not any(x["kind"] == "surname" for x in mres["candidates"][0]["signals"]), "no surname signal for a mother")
    ctx.hide = None


def test_blocks():
    ppl = tree() + [P("kid-1790", "Piero", "Tessarin", 1790, "Marenza", dy=1850),
                    P("boy-1825", "Nico", "Tessarin", 1825, "Marenza", dy=1880)]
    ctx = ctx_for(ppl)
    sg, bl = core.parent_signals(ctx, "aldo-1800", "boy-1825", "father")
    check(any("under 13" in b for b in bl), "a would-be father born 25 years AFTER his child is blocked")
    # own descendant
    ppl2 = tree()
    for p in ppl2:
        if p["id"] == "pietro-1830":
            p["kids"] = ["giovanni-1839"]
        if p["id"] == "giovanni-1839":
            p["father"] = "pietro-1830"
    c2 = ctx_for(ppl2)
    sg, bl = core.parent_signals(c2, "pietro-1830", "giovanni-1839", "father")
    check(any("descendant" in b or "under 13" in b for b in bl), "a descendant cannot be the father")
    # an estimated year: strict scoring ignores it, blocking still sees a gross contradiction
    ppl3 = tree() + [P("zuan-1600", "Zuan", "Tessarin", 1950, "Marenza", dy=None, bye=True)]
    for p in ppl3:
        if p["id"] == "zuan-1600":
            p["dy"], p["dye"] = 2005, False
    st = ctx_for(ppl3, strict=True)
    sg, bl = core.parent_signals(st, "giovanni-1839", "zuan-1600", "father")
    check(bool(bl), "an estimated birth 110 years after the child blocks, even in strict mode")
    st2 = ctx_for(ppl3, strict=True, block_est=False)
    sg, bl = core.parent_signals(st2, "giovanni-1839", "zuan-1600", "father")
    check(not bl, "the leave-one-out test lets no estimate touch the result")


def test_living():
    ctx = ctx_for()
    res = core.rank(ctx, "living-1990", "father")
    check(res.get("skipped") and not res["candidates"], "a living person is never a subject")
    check(not ctx.eligible("living-1990") and ctx.eligible("aldo-1800"), "eligibility follows the kit's living rule")
    # an ESTIMATED death is not a death record: a person born inside the window stays living
    p = P("est-1960", "Aldo", "Tessarin", 1960, "Marenza", dy=2000, dye=True)
    p["dye"] = True
    c = ctx_for(tree() + [p])
    check(not c.eligible("est-1960"), "an estimated death does not release a person born inside the living window")


def test_kept_apart_and_tiers():
    ctx = ctx_for()
    ctx.hide = "giovanni-1839"
    first = core.rank(ctx, "giovanni-1839", "father")["candidates"][0]["id"]
    kept = {("giovanni-1839", first, "father")}
    again = core.rank(ctx, "giovanni-1839", "father", kept)["candidates"]
    check(first not in [r["id"] for r in again], "a kept-apart pair is not proposed again")
    check(core.tier(9.0, 0.2) == "possible", "a strong score without a margin is only possible")
    check(core.tier(9.0, 1.5) == "strong", "a strong score with a margin is strong")
    check(core.tier(2.0, 3.0) == "weak", "a low score is weak")
    check(core.tier(9.0, 5.0, {"strong": float("inf"), "possible": 3.0}) == "possible", "calibration can make the strong tier unreachable")
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "kept.json")
        cli.keep_apart(f, "a", "b", "same", "two men of one name in two parishes")
        cli.keep_apart(f, "a", "b", "same", "again")
        check(len(json.load(open(f))["pairs"]) == 1, "keep-apart does not record a pair twice")
        check(("a", "b", "same") in cli.load_kept(f), "keep-apart reads back")


def test_same():
    ppl = tree() + [
        P("joannes-1801", "Joannes", "Tessarin", 1801, "Marenza", dy=1862),
        P("giovanni-1801", "Giovanni", "Tessarin", 1801, "Marenza", dy=1862),
        P("giovanni-1801b", "Giovanni", "Tessarini", 1802, "Corvalle", dy=1870),
        P("giovanni-1830", "Giovanni", "Tessarin", 1830, "Marenza", dy=1890),
        P("zuane-1801-f", "Zuane", "Tessarin", 1801, "Marenza", "f", dy=1862),
    ]
    ctx = ctx_for(ppl)
    res = core.rank(ctx, "joannes-1801", "same")
    ids = [r["id"] for r in res["candidates"]]
    check(ids[0] == "giovanni-1801", "Joannes and Giovanni of one year and place are the best match, got %s" % ids[:3])
    check("giovanni-1830" not in ids, "a man born 29 years later is not the same man")
    byid = {r["id"]: r for r in res["candidates"]}
    check("zuane-1801-f" in byid and byid["zuane-1801-f"]["score"] < byid["giovanni-1801"]["score"] - 2, "a different recorded sex is a heavy penalty (sex may be a guess), not a block")
    check(byid["giovanni-1801b"]["score"] < byid["giovanni-1801"]["score"], "an attested spelling a village over scores below the exact twin")


def test_cli_output_is_aggregate():
    with tempfile.TemporaryDirectory() as d:
        tp = os.path.join(d, "tree.json")
        json.dump({"meta": {}, "people": tree()}, open(tp, "w"))
        json.dump(PM, open(os.path.join(d, "place_map.json"), "w"))
        atlas = os.path.join(d, "atlas", "data")
        os.makedirs(atlas)
        for name, doc in (("surname-families.json", SUR), ("given-name-families.json", GIV), ("place-names.json", NAMES)):
            json.dump(doc, open(os.path.join(atlas, name), "w"))
        before = {n: hashlib.sha1(open(os.path.join(atlas, n), "rb").read()).hexdigest() for n in os.listdir(atlas)}
        ctx = cli.build_context(tp, None, os.path.join(d, "atlas"), strict=True, block_with_estimates=False)
        check(ctx.sources == {"catalogue": True, "places": True, "dated-names": True}, "the catalogues and places load")
        cases = cli.evaluate(ctx, ("father", "mother"))
        summ = json.dumps(cli.summarise(cases, cli.calibrate(cases)))
        for word in ("Tessarin", "Aldo", "Rosa", "pietro", "giovanni", "Marenza"):
            check(word not in summ, "the aggregate summary names no one and no place (%s)" % word)
        after = {n: hashlib.sha1(open(os.path.join(atlas, n), "rb").read()).hexdigest() for n in os.listdir(atlas)}
        check(before == after, "the Atlas catalogues are read-only")
        # propose writes nothing unless told where; the review file holds names and says a proposal is not a finding
        cwd = os.getcwd()
        os.chdir(d)
        try:
            cli.main(["propose", "--tree", tp, "--atlas", os.path.join(d, "atlas"), "--subjects", "giovanni-1839", "--min-tier", "weak"])
            check(sorted(os.listdir(d)) == ["atlas", "place_map.json", "tree.json"], "propose without --out writes nothing")
            out = os.path.join(d, "review")
            cli.main(["propose", "--tree", tp, "--atlas", os.path.join(d, "atlas"), "--subjects", "giovanni-1839", "--min-tier", "weak", "--out", out])
            md = open(os.path.join(out, "review.md"), encoding="utf-8").read()
            check("never a finding" in md and "Aldo" in md, "the review list says a proposal is not a finding and names the candidates")
        finally:
            os.chdir(cwd)


def test_orphans():
    ctx = ctx_for()
    o = cli.orphans(ctx)
    check("giovanni-1839" in o and "aldo-1800" not in o and "living-1990" not in o, "orphans: joined to no one, deceased only")


def main():
    for t in (test_names, test_places, test_father_and_mother, test_blocks, test_living, test_kept_apart_and_tiers, test_same,
              test_cli_output_is_aggregate, test_orphans):
        try:
            t()
        except Exception as e:  # a crash is a failure with a name
            import traceback
            traceback.print_exc()
            FAILS.append("%s crashed: %s" % (t.__name__, e))
    if FAILS:
        print("%d check(s) FAILED" % len(FAILS))
        return 1
    print("samepersoncandidates selftest: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
