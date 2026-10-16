#!/usr/bin/env python3
"""Check kit/data/cross-archive.json, the estate's list of persons documented in two archives.

A CONFIRMED pair is drawn as a pointer on both pages (kit/components/AlsoIn.astro); a CANDIDATE never is.
This refuses a file that could draw a wrong or one-sided pointer:

  schema      every pair has two ends (archive key from kit/data/archives.json, path starting and ending
              with "/"), a status of candidate, confirmed or rejected, and a note on a confirmed or rejected pair
  same site   a pair joining an archive to itself (that is a duplicate, not a cross-archive pair)
  repeat      the same pair twice, in either order
  conflict    one page confirmed against two different pages of the same other archive (one person
              cannot be two people there: the research owners must settle which)
  live        (--live) both pages of every CONFIRMED pair answer 200
  empty       no pairs at all

    python3 checkcross.py [--file kit/data/cross-archive.json] [--live]
"""
import os
import sys
import json
import argparse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def check(pairs, ring):
    keys = {a["key"]: a["url"].rstrip("/") for a in ring["archives"]}
    bad = []
    seen = set()
    conf = {}
    if not pairs:
        return ["empty: no pairs (a list with nothing to check has not passed)"], 0, 0
    for i, p in enumerate(pairs):
        ends = []
        for side in ("a", "b"):
            e = p.get(side) or {}
            if e.get("archive") not in keys:
                bad.append("pair %d: end %s has no known archive key (%r)" % (i, side, e.get("archive")))
            path = e.get("path", "")
            if not (path.startswith("/") and path.endswith("/")):
                bad.append("pair %d: end %s path must start and end with '/'" % (i, side))
            ends.append((e.get("archive"), path))
        if p.get("status") not in ("candidate", "confirmed", "rejected"):
            bad.append("pair %d: status must be candidate, confirmed or rejected" % i)
        if p.get("status") == "rejected" and not p.get("note"):
            bad.append("pair %d: a rejected pair needs a note saying why" % i)
        if ends[0][0] == ends[1][0]:
            bad.append("pair %d: both ends are the same archive (%s): that is a duplicate, not a cross-archive pair" % (i, ends[0][0]))
        key = frozenset(ends)
        if key in seen:
            bad.append("pair %d: the same pair is listed twice" % i)
        seen.add(key)
        if p.get("status") == "confirmed":
            if not p.get("note"):
                bad.append("pair %d: a confirmed pair needs a note saying what each page holds" % i)
            for me, other in ((ends[0], ends[1]), (ends[1], ends[0])):
                conf.setdefault((me, other[0]), set()).add(other[1])
    for (me, oa), paths in conf.items():
        if len(paths) > 1:
            bad.append("conflict: %s %s is confirmed against %d different pages of %s" % (me[0], me[1], len(paths), oa))
    n_conf = sum(1 for p in pairs if p.get("status") == "confirmed")
    return bad, len(pairs), n_conf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=os.path.join(DATA, "cross-archive.json"))
    ap.add_argument("--ring", default=os.path.join(DATA, "archives.json"))
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    pairs = json.load(open(a.file, encoding="utf-8")).get("pairs", [])
    ring = json.load(open(a.ring, encoding="utf-8"))
    bad, n, nc = check(pairs, ring)
    if a.live and not bad:
        base = {x["key"]: x["url"].rstrip("/") for x in ring["archives"]}
        for p in pairs:
            if p.get("status") != "confirmed":
                continue
            for s in ("a", "b"):
                u = base[p[s]["archive"]] + p[s]["path"]
                try:
                    code = urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=20).status
                except Exception as e:
                    code = getattr(e, "code", "error")
                if code != 200:
                    bad.append("live: %s answers %s" % (u, code))
    if bad:
        print("checkcross: FAIL (%d)" % len(bad))
        for b in bad:
            print("  - " + b)
        return 1
    print("checkcross: ok. %d pairs (%d confirmed, drawn as pointers; %d candidates, never drawn)%s" % (
        n, nc, n - nc, ", every confirmed page answers 200" if a.live else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
