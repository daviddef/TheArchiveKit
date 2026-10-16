#!/usr/bin/env python3
"""Prove living_rule.py does what its header says, and can fail.  python3 kit/tools/living_rule_selftest.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_rule as lr

Y = 2026
bad = []
def expect(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
    if not ok:
        bad.append(label); print(f"          got {got!r} want {want!r}")

print("who is living")
expect("born 1946, no death: 80, living", lr.is_living(1946, False, (), Y), True)
expect("born 1945, no death: 81, not living", lr.is_living(1945, False, (), Y), False)
expect("born 1990, no death: living", lr.is_living(1990, False, (), Y), True)
expect("born 1990 with a recorded death: not living", lr.is_living(1990, True, (), Y), False)
expect("no birth year: cannot be shown to be 80 or younger, not living", lr.is_living(None, False, (), Y), False)
expect("born 1960 but cited by FamilySearch: not living", lr.is_living(1960, False, ("FamilySearch record 1950 census",), Y), False)
expect("born 1960 cited only by a private family tree: living", lr.is_living(1960, False, ("MyHeritage family tree entry",), Y), True)
expect("born 1960 cited by a Geni tree profile: living", lr.is_living(1960, False, ("https://www.geni.com/people/x",), Y), True)
expect("born 1960 cited by FamilySearch Family Tree: not living (FamilySearch always counts)", lr.is_living(1960, False, ("FamilySearch Family Tree",), Y), False)
expect("born 1960 cited as MyHeritage research: Geni World Family Tree: a tree, living", lr.is_living(1960, False, ("MyHeritage research: Geni World Family Tree",), Y), True)
expect("born 1960 cited as MyHeritage research: WikiTree: a tree, living", lr.is_living(1960, False, ("myheritage.com/research WikiTree",), Y), True)
expect("born 1960 cited by Findmypast: not living", lr.is_living(1960, False, ("Findmypast 1939 Register",), Y), False)

print("who is held out")
expect("born 2015, no death: a KNOWN child is living, and NOT held out (David 16 Oct)", lr.possible_minor(2015, False, (), True, Y), False)
expect("born 2015, no death: a known child is living", lr.is_living(2015, False, (), Y), True)
expect("no birth year and a living parent: held out", lr.possible_minor(None, False, (), True, Y), True)
expect("no birth year and no living parent: not held out", lr.possible_minor(None, False, (), False, Y), False)
expect("recorded dead: never held out", lr.possible_minor(None, True, (), True, Y), False)
expect("a public source: never held out", lr.possible_minor(None, False, ("FamilySearch",), True, Y), False)
expect("National Archives of Australia counts as public: not living", lr.is_living(1960, False, ("NAA RecordSearch passenger manifest",), Y), False)
expect("held by id", lr.is_held_out("42", 1900, True, (), False, held_ids=["42"], today_year=Y), True)
expect("not held by id", lr.is_held_out("43", 1900, True, (), False, held_ids=["42"], today_year=Y), False)

print("the test can fail")
orig = lr.LIVING_YEARS
lr.LIVING_YEARS = 100
expect("with a 100-year bound, 1945 would wrongly be living (so the 80 above is doing the work)",
       lr.is_living(1945, False, (), Y), True)
lr.LIVING_YEARS = orig

print("\nall cases behave" if not bad else f"\n{len(bad)} FAILED")
sys.exit(1 if bad else 0)
