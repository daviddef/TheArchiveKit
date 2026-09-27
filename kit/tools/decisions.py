#!/usr/bin/env python3
"""Values that are a DECISION rather than a measurement, and refuse when one moves.

WHOSE IDEA THIS IS. The D'Arcy session wrote it (tools/check_decisions.py,
e628e15) and offered it for the kit. What is here is the machinery; the PROBES
stay in each archive, because only the archive knows where its own decisions live.

WHY NOT A DELTA OVER EVERYTHING. checkpin.py records one number and speaks when
it moves, which is right for that number and wrong as a general rule: nearly
every number a build prints moves every run for a good reason — pages, records,
badges, search entries — and a delta report over those is noise with a different
shape. The failure mode of every noisy check is that somebody turns it off. So
the question is not «state or delta». It is WHICH VALUES ARE SUPPOSED TO BE
CONSTANT, and those are few, and each is an act of judgement rather than a count.

WHY IT REFUSES INSTEAD OF REPORTING. A decision changing is precisely the case
where a deliberate act should be required, and editing the declaration in the
same commit IS that act — one file, one line, and the move then shows as a diff
in a file whose only subject is the decision. A report can be scrolled past, and
the proof of that is the fault this came from: a pin moved inside a commit about
something else and three builds printed the correct new value under «ok» before
anybody read it.

WHAT THE TWO OF US GOT WRONG ON THE WAY, because it is the argument for the
shape. I concluded that putting numbers into «ok» lines was the fault. It is not:
their 858-versus-852 page-count split was found BECAUSE the numbers were printed.
The fault is that nothing compared them to anything. A declaration is the thing
to be compared against.

    from decisions import check
    raise SystemExit(check("src/data/decisions.json", {
        "kitPin": lambda: pin_from_package_json(),
        "livingPolicy": lambda: json.load(open(...)).get("policy", "named-bare"),
    }))

Every declared key needs a probe and every probe needs a declared key: a key
nobody can recompute is not being watched, and a probe nobody declared would
otherwise be adopted silently at whatever value it happens to have today.
"""
import json
import os

LABEL = "decisions"


def canon(v):
    """Compare by meaning, not by spelling: order in a list is not a decision."""
    if isinstance(v, dict):
        return {k: canon(v[k]) for k in sorted(v)}
    if isinstance(v, (list, tuple)):
        inner = [canon(x) for x in v]
        try:
            return sorted(inner, key=lambda x: json.dumps(x, sort_keys=True))
        except Exception:
            return inner
    return v


def same(a, b):
    return json.dumps(canon(a), sort_keys=True) == json.dumps(canon(b), sort_keys=True)


def brief(v, n=64):
    s = v if isinstance(v, str) else json.dumps(canon(v), sort_keys=True)
    return s if len(s) <= n else s[:n - 1] + "…"


def check(path, probes, quiet=False):
    """0 when every declared decision still holds, 1 when one has moved."""
    if not os.path.exists(path):
        print("  FAIL  %-10s no declaration at %s. This gate is only as good as its "
              "list, so a missing list is a failure and not a pass." % (LABEL, path))
        return 1
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        # A FILE THAT CANNOT BE READ IS NOT A DECISION THAT HAS NOT MOVED.
        print("  FAIL  %-10s %s UNREADABLE — %s" % (LABEL, path, str(e)[:70]))
        return 1

    declared = doc.get("decisions", doc)
    if not isinstance(declared, dict) or not declared:
        print("  FAIL  %-10s %s declares nothing, so nothing is being watched"
              % (LABEL, path))
        return 1
    declared = {k: v for k, v in declared.items() if not k.startswith("_")}

    fails = []
    for key in sorted(set(declared) | set(probes)):
        if key not in probes:
            fails.append((key, "declared here and nothing recomputes it, so it is "
                               "written down rather than watched", None, None))
            continue
        if key not in declared:
            fails.append((key, "recomputed but never declared — it would be adopted "
                               "silently at whatever value it holds today", None, None))
            continue
        want = declared[key]
        want = want.get("value") if isinstance(want, dict) and "value" in want else want
        why = declared[key].get("why", "") if isinstance(declared[key], dict) else ""
        try:
            got = probes[key]()
        except Exception as e:
            fails.append((key, "could not be recomputed — %s" % str(e)[:60], why, None))
            continue
        if not same(want, got):
            fails.append((key, "declared %s, found %s" % (brief(want), brief(got)), why, got))

    if fails:
        print("  FAIL  %-10s %d decision(s) no longer hold" % (LABEL, len(fails)))
        for key, what, why, _got in fails:
            print("          %s — %s" % (key, what))
            if why:
                print("            it was decided because: %s" % why[:150])
        print("          A decision changing is a deliberate act. Edit %s in the same "
              "commit, or put back what moved." % path)
        return 1
    if not quiet:
        print("  ok    %-10s %d decision(s) still hold, each recomputed from its own "
              "source" % (LABEL, len(declared)))
    return 0
