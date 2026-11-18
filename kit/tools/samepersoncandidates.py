#!/usr/bin/env python3
"""Same-person candidates: propose joins for a person to review. NEVER joins anything. See samepersoncore.py.

Run by each archive on its OWN tree.json (the Roots & Routes contract), from the archive's folder:

  KIT=node_modules/@daviddef/archive-kit/kit/tools
  ATLAS="$HOME/Projects/Family Projects/Record Atlas"        # read-only: the surname, given-name and place catalogues

  # 1. Does it work on THIS archive? Hide each link the archive already asserts and see whether the tool finds it again.
  python3 $KIT/samepersoncandidates.py evaluate --tree data/tree-page/tree.json --atlas "$ATLAS" --write-thresholds thr.json

  # 2. Review list for the people joined to no one (writes names: put --out OUTSIDE any repo)
  python3 $KIT/samepersoncandidates.py propose --tree data/tree-page/tree.json --atlas "$ATLAS" \
      --subjects orphans --thresholds thr.json --out ~/Desktop/review

  # 3. A pair a reader decided against is never proposed again
  python3 $KIT/samepersoncandidates.py keep-apart kept-apart.json ID_A ID_B --relation same --why "two men of one name, two parishes"

  # 4. Two rows the archive already knows are one person (or two): how do they score?
  python3 $KIT/samepersoncandidates.py evaluate-same --tree ... --pairs pairs.json

Nothing is written unless --out / --cases / --write-thresholds is given. The files hold NAMES: they are for the person
reviewing, they are never committed, and `check-living` style gates do not read them. Deceased people only.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import samepersoncore as core  # noqa: E402

DEFAULT_ATLAS_ENV = "RECORD_ATLAS"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_context(tree_path, place_map=None, atlas=None, strict=True, today_year=None, block_with_estimates=True):
    tree = load_json(tree_path)
    pm_path = place_map or os.path.join(os.path.dirname(os.path.abspath(tree_path)), "place_map.json")
    pm = load_json(pm_path) if os.path.exists(pm_path) else None
    atlas = atlas or os.environ.get(DEFAULT_ATLAS_ENV)
    sur = giv = names = None
    if atlas:
        def opt(name):
            p = os.path.join(atlas, "data", name)
            return load_json(p) if os.path.exists(p) else None
        sur, giv, names = opt("surname-families.json"), opt("given-name-families.json"), opt("place-names.json")
    cat = core.Catalogue(sur, giv)
    ctx = core.Context(tree["people"], cat, core.Places(pm, names), strict=strict, today_year=today_year, block_with_estimates=block_with_estimates)
    ctx.sources = {"catalogue": bool(sur and giv), "places": bool(pm), "dated-names": bool(names)}
    return ctx


def orphans(ctx):
    """People joined to no one: no parents, spouse or children."""
    out = []
    for pid, p in ctx.P.items():
        if not ctx.parents(pid) and not ctx.kids(pid) and not ctx.spouses(pid) and ctx.eligible(pid):
            out.append(pid)
    return out


# ---------------------------------------------------------------- kept apart
def load_kept(path):
    if not path or not os.path.exists(path):
        return set()
    return {(p["a"], p["b"], p.get("relation") or "any") for p in load_json(path).get("pairs", [])}


def keep_apart(path, a, b, relation, why):
    doc = load_json(path) if os.path.exists(path) else {"note": "Pairs a reader decided are NOT to be proposed again. Ids only.", "pairs": []}
    if not any(p["a"] == a and p["b"] == b and p.get("relation") == relation for p in doc["pairs"]):
        doc["pairs"].append({"a": a, "b": b, "relation": relation, "why": why})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


# ---------------------------------------------------------------- leave-one-out
def mid_credit(greater, ties, k):
    """The chance the truth is in the top k under random tie-breaking."""
    if greater >= k:
        return 0.0
    if greater + ties + 1 <= k:
        return 1.0
    return (k - greater) / float(ties + 1)


def split_of(pid):
    return int(hashlib.md5(pid.encode()).hexdigest(), 16) % 2   # 0 = calibration half, 1 = test half


ALL_KINDS = {"surname", "dates", "place", "household", "namesake", "naming", "sex"}
ABLATIONS = {
    "full model": None,
    "dates only": {"dates"},
    "surname + dates only": {"surname", "dates"},
    "place only (counts the candidate's children's birthplaces)": {"place"},
    "without the household": ALL_KINDS - {"household"},
    "without dates": ALL_KINDS - {"dates"},
    "without surname": ALL_KINDS - {"surname"},
    "without place": ALL_KINDS - {"place"},
    "without the name signals (namesake clash, grandfather naming)": ALL_KINDS - {"namesake", "naming"},
}


def evaluate(ctx, kinds=("father", "mother", "spouse"), min_grade=None, thr=None):
    """Hide each asserted link in turn (the person becomes an orphan) and ask for it back. Returns cases (with ids)."""
    cases = []
    for s in sorted(ctx.P):
        if not ctx.eligible(s):
            continue
        S = ctx.P[s]
        for kind in kinds:
            if kind in ("father", "mother"):
                t = S[kind]
                grade = S["fg"] if kind == "father" else S["mg"]
                truths = [t] if t in ctx.P and ctx.eligible(t) else []
            else:
                truths = [x for x in ctx.spouses(s) if ctx.eligible(x)]
                grade = None
            if not truths or (min_grade is not None and kind != "spouse" and (grade is None or grade < min_grade)):
                continue
            ctx.hide = s
            try:
                res = core.rank(ctx, s, kind, thr=thr)
                full = res["candidates"]
                if kind == "spouse":
                    truths = [x for x in truths if x in ctx.P]
            finally:
                ctx.hide = None
            truth_rows = [r for r in full if r["id"] in truths]
            blocked_truth = not truth_rows
            row = {"subject": s, "kind": kind, "grade": grade, "n": len(full), "blocked": res["blocked"], "truth": truths,
                   "truth_blocked": blocked_truth, "split": split_of(s)}
            if full:
                top = full[0]
                row.update(top_id=top["id"], top_score=top["score"], top_margin=top["margin"], top_tier=top["tier"],
                           top_correct=top["id"] in truths, top_namesakes=top.get("namesakes", 0))
            if truth_rows:
                best = max(truth_rows, key=lambda r: r["score"])
                greater = sum(1 for r in full if r["score"] > best["score"])
                ties = sum(1 for r in full if r["score"] == best["score"]) - 1
                row.update(rank=1 + greater + ties / 2.0, greater=greater, ties=ties, truth_score=best["score"],
                           c1=mid_credit(greater, ties, 1), c3=mid_credit(greater, ties, 3), c10=mid_credit(greater, ties, 10))
                # namesake trap: another candidate with the truth's name keys, plausible age (it was not blocked)
                trow = ctx.P[best["id"]]
                decoys = [r for r in full if r["id"] not in truths and
                          ctx.cat.surname_relation(trow["sur"], ctx.P[r["id"]]["sur"])[0] in ("same-form", "catalogue", "fold") and
                          ctx.cat.given_relation(trow["given"], ctx.P[r["id"]]["given"])[0] in ("identical", "same-name")]
                row["decoys"] = len(decoys)
                row["decoy_beats"] = sum(1 for r in decoys if r["score"] >= best["score"])
                # ablations
                ab = {}
                for name, keep in ABLATIONS.items():
                    if keep is None:
                        ab[name] = (row["c1"], row["c3"], row["c10"])
                        continue
                    sc = lambda r: sum(x["w"] for x in r["signals"] if x["kind"] in keep)
                    ts = sc(best)
                    g = sum(1 for r in full if sc(r) > ts)
                    ti = sum(1 for r in full if sc(r) == ts) - 1
                    ab[name] = (mid_credit(g, ti, 1), mid_credit(g, ti, 3), mid_credit(g, ti, 10))
                row["ablation"] = ab
                # the surname-only-by-age strawman: random ranking
                row["random_c1"] = 1.0 / max(1, len(full))
                row["random_c10"] = min(1.0, 10.0 / max(1, len(full)))
            cases.append(row)
    return cases


def calibrate(cases, target_strong=0.90, target_possible=0.50, min_n=8):
    """Thresholds PER KIND (father, mother, spouse) from the calibration half, chosen so the TOP proposal of that tier is right
    at least `target` of the time. None = no threshold reached the target: that tier is not offered. `same` has no ground
    truth to calibrate on and keeps the default constants."""
    out = {"margin": core.MARGIN, "target": {"strong": target_strong, "possible": target_possible}}
    for kind in ("father", "mother", "spouse"):
        tr = [c for c in cases if c["kind"] == kind and c["split"] == 0 and "top_score" in c]

        def pick(target, need_margin):
            for T in sorted({c["top_score"] for c in tr}):
                sel = [c for c in tr if c["top_score"] >= T and (c["top_margin"] >= core.MARGIN or not need_margin)]
                if len(sel) >= min_n and sum(1 for c in sel if c["top_correct"]) / len(sel) >= target:
                    return T
            return None
        out[kind] = {"strong": pick(target_strong, True), "possible": pick(target_possible, False), "calibration_cases": len(tr)}
    return out


def summarise(cases, thr):
    """Aggregates only: no ids, no names."""
    def agg(rows):
        n = len(rows)
        if not n:
            return {"cases": 0}
        found = [r for r in rows if "rank" in r]
        d = {"cases": n, "truth_in_candidates": len(found), "truth_blocked": sum(1 for r in rows if r["truth_blocked"]),
             "no_candidates": sum(1 for r in rows if r["n"] == 0)}
        if found:
            d.update(top1=round(sum(r["c1"] for r in found) / len(found), 3), top3=round(sum(r["c3"] for r in found) / len(found), 3),
                     top10=round(sum(r["c10"] for r in found) / len(found), 3),
                     median_rank=sorted(r["rank"] for r in found)[len(found) // 2],
                     random_top1=round(sum(r["random_c1"] for r in found) / len(found), 4),
                     random_top10=round(sum(r["random_c10"] for r in found) / len(found), 3),
                     median_candidates=sorted(r["n"] for r in found)[len(found) // 2])
            # of ALL cases, how often is the truth in the top 10 (a block or a missing candidate counts as a miss)
            d["top10_of_all"] = round(sum(r["c10"] for r in found) / n, 3)
            d["top1_of_all"] = round(sum(r["c1"] for r in found) / n, 3)
        return d
    out = {"by_kind": {}, "by_tier": {}, "namesake": {}, "ablation": {}, "thresholds": thr}
    for kind in ("father", "mother", "spouse"):
        rows = [c for c in cases if c["kind"] == kind]
        out["by_kind"][kind] = agg(rows)
        for g in (0, 2):
            rg = [c for c in rows if c["grade"] == g]
            if rg:
                out["by_kind"][kind]["grade_%d" % g] = agg(rg)
        # ablations
        ab = defaultdict(lambda: [0, 0, 0, 0])
        for c in rows:
            for name, (a1, a3, a10) in c.get("ablation", {}).items():
                v = ab[name]
                v[0] += a1; v[1] += a3; v[2] += a10; v[3] += 1
        out["ablation"][kind] = {k: {"top1": round(v[0] / v[3], 3), "top3": round(v[1] / v[3], 3), "top10": round(v[2] / v[3], 3)} for k, v in ab.items() if v[3]}
        # namesakes
        found = [c for c in rows if "rank" in c]
        trap = [c for c in found if c["decoys"]]
        free = [c for c in found if not c["decoys"]]
        out["namesake"][kind] = {
            "cases_with_a_namesake_decoy": len(trap), "cases_without": len(free),
            "top1_with_decoy": round(sum(c["c1"] for c in trap) / len(trap), 3) if trap else None,
            "top1_without": round(sum(c["c1"] for c in free) / len(free), 3) if free else None,
            "top_was_a_decoy": sum(1 for c in trap if "top_correct" in c and not c["top_correct"] and c["decoy_beats"] > 0)}
    # tier calibration on the test half, with the thresholds fitted on the other half
    for half, label in ((1, "test half"), (0, "calibration half")):
        for kind in ("father", "mother", "spouse"):
            rows = [c for c in cases if c["kind"] == kind and c["split"] == half and "top_score" in c]
            def tier_of(c, kind=kind):
                k = thr.get(kind) or {}
                return core.tier(c["top_score"], c["top_margin"], {"strong": k.get("strong") if k.get("strong") is not None else math.inf,
                                                                  "possible": k.get("possible") if k.get("possible") is not None else math.inf})
            tiers = defaultdict(lambda: [0, 0])
            for c in rows:
                t = tier_of(c)
                tiers[t][0] += 1
                tiers[t][1] += 1 if c["top_correct"] else 0
            out["by_tier"]["%s/%s" % (kind, label)] = {t: {"proposals": v[0], "right": v[1], "precision": round(v[1] / v[0], 3) if v[0] else None} for t, v in sorted(tiers.items())}
    return out


# ---------------------------------------------------------------- same-person pairs
def evaluate_same(ctx, pairs):
    """pairs: [{"a","b","same":true|false}]. For each pair: the score, whether it is blocked, and the rank of b among all
    candidates for a (and a for b) when ranking for 'same'."""
    out = []
    for p in pairs:
        a, b = p["a"], p["b"]
        if a not in ctx.P or b not in ctx.P:
            out.append({"in_tree": False, "same": p["same"]})
            continue
        sg, bl = core.same_signals(ctx, a, b)
        res = core.rank(ctx, a, "same")
        rows = res["candidates"]
        pos = next((i for i, r in enumerate(rows) if r["id"] == b), None)
        out.append({"in_tree": True, "same": p["same"], "score": round(sum(x["w"] for x in sg), 2), "blocked": bool(bl),
                    "rank": (pos + 1) if pos is not None else None, "n": len(rows), "tier": rows[pos]["tier"] if pos is not None else None,
                    "a": a, "b": b, "why": [x["why"] for x in sg][:6], "blocks": bl, "kind": p.get("kind")})
    return out


# ---------------------------------------------------------------- writing the review list
def label(ctx, x):
    p = ctx.P[x]
    bits = [p["name"] or x]
    if p["by"] is not None:
        bits.append(("b. c. %d" if p["bye"] else "b. %d") % p["by"])
    if p["bp"]:
        bits.append(p["bp"])
    if p["dy"] is not None:
        bits.append(("d. c. %d" if p["dye"] else "d. %d") % p["dy"])
    return ", ".join(bits)


def write_review(ctx, results, path, header):
    lines = ["# Same-person candidates: for review", "", header, "",
             "**A proposal is a place to look, never a finding.** Nothing here has been joined. Check the register, then decide; "
             "a pair you decide against goes in the kept-apart list so it does not come back.", ""]
    for subj, res in results:
        if not res["candidates"]:
            continue
        lines.append("## %s  (%s)" % (label(ctx, subj), res["mode"]))
        for r in res["candidates"]:
            ns = (", %d namesake%s among the candidates" % (r["namesakes"], "" if r["namesakes"] == 1 else "s")) if r.get("namesakes") else ""
            lines.append("- **%s** `%s` score %.1f margin %.1f%s: %s" % (r["tier"], r["id"], r["score"], r["margin"] if r["margin"] < 90 else 0, ns, label(ctx, r["id"])))
            for x in r["signals"][:6]:
                lines.append("    - %+.1f %s" % (x["w"], x["why"]))
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def thresholds_from(path):
    """{kind: {"strong", "possible"}} from `evaluate --write-thresholds`; a tier no threshold reached is infinity (not offered)."""
    if not path:
        return None
    t = load_json(path)
    out = {}
    for kind in ("father", "mother", "spouse"):
        k = t.get(kind) or {}
        out[kind] = {"strong": k["strong"] if k.get("strong") is not None else math.inf,
                     "possible": k["possible"] if k.get("possible") is not None else math.inf}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--tree", required=True)
        p.add_argument("--place-map")
        p.add_argument("--atlas", help="Record Atlas checkout (default $%s); read-only" % DEFAULT_ATLAS_ENV)
        p.add_argument("--lenient", action="store_true", help="count estimated years and places taken from a relative as evidence (default: strict)")
    p = sub.add_parser("propose"); common(p)
    p.add_argument("--mode", default="all", choices=["parents", "spouse", "same", "all"])
    p.add_argument("--subjects", default="orphans", help="orphans | all | comma-separated ids")
    p.add_argument("--kept-apart"); p.add_argument("--thresholds"); p.add_argument("--top", type=int, default=3)
    p.add_argument("--min-tier", default="possible", choices=["weak", "possible", "strong"])
    p.add_argument("--out", help="directory for review.md and proposals.json (names inside: keep it out of any repo)")
    p = sub.add_parser("evaluate"); common(p)
    p.add_argument("--kinds", default="father,mother,spouse"); p.add_argument("--min-grade", type=int)
    p.add_argument("--cases", help="write per-case results (ids) here"); p.add_argument("--write-thresholds")
    p = sub.add_parser("evaluate-same"); common(p)
    p.add_argument("--pairs", required=True)
    p = sub.add_parser("keep-apart")
    p.add_argument("file"); p.add_argument("a"); p.add_argument("b")
    p.add_argument("--relation", default="any", choices=["father", "mother", "spouse", "same", "any"]); p.add_argument("--why", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "keep-apart":
        keep_apart(a.file, a.a, a.b, a.relation, a.why)
        print("kept apart: %s | %s (%s)" % (a.a, a.b, a.relation))
        return 0
    # evaluate: no estimate may touch the answer (it could have been worked out from the hidden relative). propose: nothing is
    # hidden, so an estimate may BLOCK a gross contradiction (a father born 160 years after his child) though it never scores.
    ctx = build_context(a.tree, a.place_map, a.atlas, strict=not a.lenient, block_with_estimates=(a.cmd != "evaluate"))
    if not ctx.sources["catalogue"]:
        print("note: no Atlas catalogues found (--atlas): surnames and given names are compared by spelling and accent only", file=sys.stderr)

    if a.cmd == "evaluate":
        kinds = tuple(k for k in a.kinds.split(",") if k)
        cases = evaluate(ctx, kinds, a.min_grade)
        thr = calibrate(cases)
        summ = summarise(cases, thr)
        summ["people"] = len(ctx.P)
        summ["eligible"] = sum(1 for x in ctx.P if ctx.eligible(x))
        summ["mode"] = "lenient" if a.lenient else "strict"
        summ["sources"] = ctx.sources
        print(json.dumps(summ, indent=1, ensure_ascii=False))
        if a.cases:
            with open(a.cases, "w", encoding="utf-8") as f:
                json.dump(cases, f, ensure_ascii=False)
        if a.write_thresholds:
            with open(a.write_thresholds, "w", encoding="utf-8") as f:
                json.dump(thr, f, indent=1)
        return 0

    if a.cmd == "evaluate-same":
        res = evaluate_same(ctx, load_json(a.pairs))
        summ = {"pairs": len(res), "in_tree": sum(1 for r in res if r["in_tree"])}
        for same in (True, False):
            rows = [r for r in res if r["in_tree"] and r["same"] is same]
            summ["same" if same else "distinct"] = {
                "pairs": len(rows), "blocked": sum(1 for r in rows if r["blocked"]),
                "scored_possible_or_better": sum(1 for r in rows if not r["blocked"] and r["score"] >= core.TIERS["possible"]),
                "median_score": sorted(r["score"] for r in rows)[len(rows) // 2] if rows else None,
                "rank_1": sum(1 for r in rows if r["rank"] == 1), "rank_le_3": sum(1 for r in rows if r["rank"] and r["rank"] <= 3)}
        print(json.dumps(summ, indent=1))
        return 0

    # propose
    thr = thresholds_from(a.thresholds)
    kept = load_kept(a.kept_apart)
    if a.subjects == "orphans":
        subs = orphans(ctx)
    elif a.subjects == "all":
        subs = [x for x in sorted(ctx.P) if ctx.eligible(x)]
    else:
        subs = [x for x in a.subjects.split(",") if x in ctx.P]
    modes = {"parents": ["father", "mother"], "spouse": ["spouse"], "same": ["same"], "all": ["father", "mother", "spouse", "same"]}[a.mode]
    order = {"weak": 0, "possible": 1, "strong": 2}
    results = []
    for s in subs:
        for m in modes:
            res = core.rank(ctx, s, m, kept, (thr or {}).get(m))   # `same` is never calibrated: default constants
            res["candidates"] = [r for r in res["candidates"] if order[r["tier"]] >= order[a.min_tier]][: a.top]
            if res["candidates"]:
                results.append((s, res))
    print(json.dumps({"subjects": len(subs), "with_proposals": len(results),
                      "by_tier": {t: sum(1 for _, r in results for c in r["candidates"] if c["tier"] == t) for t in order}}))
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        header = "Thresholds: %s; same-person proposals always use the DEFAULT thresholds (there are too few adjudicated pairs to calibrate them). Years and places: %s. Catalogues: %s." % (
            "father, mother and spouse calibrated on this archive" if thr else "DEFAULT, not calibrated on this archive (run `evaluate --write-thresholds` first)",
            "estimates and borrowed places count as unknown (strict)" if not a.lenient else "estimates are wide ranges (lenient)",
            "the Atlas's" if ctx.sources["catalogue"] else "NOT loaded (spelling and accent only)")
        write_review(ctx, results, os.path.join(a.out, "review.md"), header)
        with open(os.path.join(a.out, "proposals.json"), "w", encoding="utf-8") as f:
            json.dump([{"subject": s, **r} for s, r in results], f, ensure_ascii=False, indent=1)
        print("wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
