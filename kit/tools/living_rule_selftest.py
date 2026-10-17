#!/usr/bin/env python3
"""Prove living_rule.py does what its header says, and can fail.  python3 kit/tools/living_rule_selftest.py

The cases are NOT written here. They are in kit/data/living-rule-cases.json, which
kit/tools/checkperson_logic.mjs reads too and asserts against kit/lib/person.js, so the
Python rule and the JavaScript rule are held to the same questions and cannot drift apart
unnoticed. This file only runs them, checks the fixture itself has not been hollowed out, and
proves the run can fail.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_rule as lr

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(os.path.dirname(HERE), "data", "living-rule-cases.json")
D = json.load(open(FIX, encoding="utf-8"))
Y = D["today"]
bad = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
    if not ok:
        bad.append(label)
        if detail:
            print("          " + detail)


def answers(case):
    i = case["in"]
    cit = i.get("citations", [])
    return {
        "public_source": lr.public_source(cit),
        "is_living": lr.is_living(i.get("birth_year"), i.get("recorded_dead", False), cit, Y, i.get("youngest_child_year"), i.get("said_living", False)),
        "possible_minor": lr.possible_minor(i.get("birth_year"), i.get("recorded_dead", False), cit, i.get("parent_living", False), Y, i.get("youngest_child_year"), i.get("said_living", False)),
        "is_held_out": lr.is_held_out(i.get("id", "none"), i.get("birth_year"), i.get("recorded_dead", False), cit,
                                      i.get("parent_living", False), i.get("held_ids", []), Y, i.get("youngest_child_year"), i.get("said_living", False)),
    }


def run_all():
    n_bad = 0
    for c in D["cases"]:
        got = answers(c)
        miss = {k: (got[k], v) for k, v in c["want"].items() if got[k] != v}
        if miss:
            n_bad += 1
        yield c, miss
    for pc in D["place_cases"]:
        if lr.address_like(pc["place"]) != pc["address_like"]:
            n_bad += 1
            yield {"id": "place: " + pc["place"], "why": "address_like"}, {"address_like": (lr.address_like(pc["place"]), pc["address_like"])}
        else:
            yield {"id": "place: " + pc["place"], "why": "address_like"}, {}


print("the fixture is intact (kit/data/living-rule-cases.json)")
ids = [c["id"] for c in D["cases"]]
check("case ids are unique", len(ids) == len(set(ids)))
tags = {t for c in D["cases"] for t in c["tags"]}
missing = [t for t in D["required_tags"] if t not in tags]
check("every required scenario is covered by a case (" + ", ".join(D["required_tags"]) + ")", not missing, f"missing {missing}")
check("at least 25 cases and 10 place cases", len(D["cases"]) >= 25 and len(D["place_cases"]) >= 10)

print("the shared cases")
n = 0
for c, miss in run_all():
    n += 1
    check(c["id"], not miss, f"{c.get('why','')}: got/want {miss}")

print("the test can fail")
orig = lr.LIVING_YEARS
lr.LIVING_YEARS = 100
hit = [c["id"] for c, miss in run_all() if miss]
check(f"with a 100-year bound the shared cases catch it ({len(hit)} fail: {', '.join(hit[:3])}…)", len(hit) >= 2)
lr.LIVING_YEARS = 79
hit = [c["id"] for c, miss in run_all() if miss]
check(f"with a 79-year bound the 80/81 boundary catches it ({len(hit)} fail)", "age-80-is-living" in hit)
lr.LIVING_YEARS = orig
orig_c = lr.CHILD_LIVING_YEARS
lr.CHILD_LIVING_YEARS = 100
hit = [c["id"] for c, miss in run_all() if miss]
check(f"with a 100-year recent-child bound the child cases catch it ({len(hit)} fail)", "undated-child-boundary-61" in hit)
lr.CHILD_LIVING_YEARS = 59
hit = [c["id"] for c, miss in run_all() if miss]
check(f"with a 59-year recent-child bound the boundary catches it ({len(hit)} fail)", "undated-child-boundary-60" in hit)
lr.CHILD_LIVING_YEARS = orig_c
orig_rc = lr.recent_child
lr.recent_child = lambda *a, **k: False
hit = [c["id"] for c, miss in run_all() if miss]
check(f"with the recent child ignored the child cases catch it ({len(hit)} fail)", "undated-recent-child" in hit)
lr.recent_child = orig_rc
_il = lr.is_living
lr.is_living = lambda b, d, c=(), t=None, y=None, said_living=False: _il(b, d, c, t, y, False)
hit = [c["id"] for c, miss in run_all() if miss]
check(f"with a living statement ignored the said-living case catches it ({len(hit)} fail)", "said-living-undated" in hit)
lr.is_living = _il
_pm = lr.possible_minor
lr.possible_minor = lambda b, d, c=(), p=False, t=None, y=None, said_living=False: _pm(b, d, c, p, t, y, False)
hit = [c["id"] for c, miss in run_all() if miss]
check(f"with a living statement ignored by possible_minor the held-out case catches it ({len(hit)} fail)", "said-living-child-of-living-parent-not-held-out" in hit)
lr.possible_minor = _pm
saved = lr.EXCLUDED
lr.EXCLUDED = []
hit = [c["id"] for c, miss in run_all() if miss]
check(f"with the private-tree exclusions emptied the tree cases catch it ({len(hit)} fail)", "myheritage-research-wikitree-is-a-tree" in hit)
lr.EXCLUDED = saved
check("restored, every case passes again", not [1 for c, m in run_all() if m])

print(f"\n{n} cases ({len(D['cases'])} rule, {len(D['place_cases'])} place)")
print("all cases behave" if not bad else f"{len(bad)} FAILED")
sys.exit(1 if bad else 0)
