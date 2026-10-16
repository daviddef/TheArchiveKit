#!/usr/bin/env python3
"""Prove checkcross.py can fail. Invented paths only.  python3 kit/tools/checkcross_selftest.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checkcross as cc
ring = json.load(open(os.path.join(os.path.dirname(HERE), "data", "archives.json")))
ok_pair = {"a": {"archive": "falco", "path": "/people/x/"}, "b": {"archive": "darcy", "path": "/people/y/"}, "status": "confirmed", "note": "n"}
res = []
def case(label, cond):
    res.append(bool(cond)); print("  %s  %s" % ("ok  " if cond else "FAIL", label))
def bad(pairs, frag):
    b, _, _ = cc.check(pairs, ring)
    return any(frag in x for x in b)
b, n, nc = cc.check([ok_pair], ring)
case("a clean confirmed pair passes", not b and n == 1 and nc == 1)
case("an empty list is refused", bad([], "empty"))
case("an unknown archive key fails", bad([dict(ok_pair, b={"archive": "nowhere", "path": "/p/"})], "no known archive"))
case("a path without slashes fails", bad([dict(ok_pair, a={"archive": "falco", "path": "people/x"})], "must start and end"))
case("a bad status fails", bad([dict(ok_pair, status="maybe")], "status must be"))
case("a rejected pair needs a note", bad([dict(ok_pair, status="rejected", note="")], "rejected pair needs a note"))
case("a rejected pair with a note passes and is not drawn", not bad([dict(ok_pair, status="rejected")], "status") and cc.check([dict(ok_pair, status="rejected")], ring)[2] == 0)
case("a pair within one archive fails", bad([dict(ok_pair, b={"archive": "falco", "path": "/people/z/"})], "same archive"))
case("a confirmed pair with no note fails", bad([dict(ok_pair, note="")], "needs a note"))
case("the same pair twice (reversed) fails", bad([ok_pair, dict(ok_pair, a=ok_pair["b"], b=ok_pair["a"])], "twice"))
case("one page confirmed against two pages of another archive fails",
     bad([ok_pair, dict(ok_pair, b={"archive": "darcy", "path": "/people/other/"})], "conflict"))
case("a candidate with no note and a conflict is not a conflict",
     not bad([ok_pair, dict(ok_pair, b={"archive": "darcy", "path": "/people/other/"}, status="candidate", note="")], "conflict"))
real = json.load(open(os.path.join(os.path.dirname(HERE), "data", "cross-archive.json")))["pairs"]
b, n, nc = cc.check(real, ring)
case("the real file passes (%d pairs, %d confirmed)" % (n, nc), not b and n > 0)
print("\nall %d cases behave" % len(res) if all(res) else "\n%d FAILED" % res.count(False))
sys.exit(0 if all(res) else 1)
