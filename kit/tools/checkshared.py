#!/usr/bin/env python3
"""Report components that exist in more than one archive, and whether they agree.

Two archives carrying a component of the same name is not itself a bug — it is
how a shared thing starts. What makes it a bug is what happens next: the copies
drift, and then the same name means two behaviours. That is how `Chip` came to
mean one thing on one archive and something else on another, and how the two
`Pedigree` components ended up 7.6KB and 1.8KB apart.

Measured across the seven on 14 September 2026: nine names duplicated, 115KB in
total, and eight of the nine already drifted.

Comments are stripped before comparing, because two copies that differ only in
how they explain themselves are still one component and should be promoted, not
argued about.

  python3 checkshared.py --root /path/containing/the/archives [--fail-on-new]

Advisory by default: an estate does not stop deploying because two archives
share a file. --fail-on-new gates against the list growing, which is the thing
actually worth preventing.
"""
import os, re, sys, glob, json, hashlib, argparse, collections

SEEN = ".shared-components.json"


def norm(path):
    s = open(path, encoding="utf-8", errors="replace").read()
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)      # block comments
    s = re.sub(r"^\s*//.*$", "", s, flags=re.M)      # line comments
    s = re.sub(r"\s+", " ", s).strip()
    return hashlib.sha1(s.encode()).hexdigest()[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--kit", default=None)
    ap.add_argument("--fail-on-new", action="store_true")
    a = ap.parse_args()

    kit_dir = a.kit or os.path.join(a.root, "Archive Kit", "kit", "components")
    kit = {os.path.basename(p) for p in glob.glob(os.path.join(kit_dir, "*.astro"))}

    owned = collections.defaultdict(list)
    for p in glob.glob(os.path.join(a.root, "*", "site", "src", "components", "*.astro")):
        arch = os.path.relpath(p, a.root).split(os.sep)[0]
        owned[os.path.basename(p)].append((arch, norm(p), os.path.getsize(p)))

    dup = {n: v for n, v in owned.items() if len(v) > 1}
    in_kit_too = sorted(n for n in dup if n in kit)

    total = sum(sz for v in dup.values() for _, _, sz in v)
    drifted = [n for n, v in dup.items() if len({h for _, h, _ in v}) > 1]

    print(f"  {len(dup)} component name(s) in more than one archive, {total/1024:.0f}KB in total")
    for n in sorted(dup, key=lambda n: -sum(sz for _, _, sz in dup[n])):
        v = dup[n]
        same = len({h for _, h, _ in v}) == 1
        mark = "identical" if same else "DRIFTED "
        who = ", ".join(f"{arch.replace(' Family','')} {sz/1024:.1f}KB" for arch, _, sz in v)
        print(f"    {mark}  {n:<22} {len(v)} copies — {who}")
    if in_kit_too:
        print(f"  also in the kit, so the local copies are shadowing it: {', '.join(in_kit_too)}")
    print(f"  {len(drifted)} of {len(dup)} have drifted — same name, different behaviour")

    if a.fail_on_new:
        path = os.path.join(a.root, SEEN)
        # Record the COUNT, not just the name. A component already forked in two
        # archives going to three is the same failure as a new one forking, and
        # the first version of this check let it through.
        raw = json.load(open(path)) if os.path.exists(path) else None
        known = ({n: 2 for n in raw} if isinstance(raw, list) else raw) if raw is not None else None
        now = {n: len(v) for n, v in dup.items()}
        if known is None:
            json.dump(now, open(path, "w"), indent=1, sort_keys=True)
            print(f"  baseline written to {SEEN} — {len(now)} known")
            return 0
        new = sorted(n for n in now if n not in known)
        grew = sorted(n for n in now if n in known and now[n] > known[n])
        if new or grew:
            for n in new:
                print(f"  FAIL  {n} has been copied into a second archive "
                      f"({now[n]} copies now)")
            for n in grew:
                print(f"  FAIL  {n} has gained a copy — {known[n]} before, {now[n]} now")
            print("        promote it to the kit, or update " + SEEN + " deliberately")
            return 1
        gone = sorted(n for n in known if n not in now)
        if gone:
            print(f"  {len(gone)} promoted or removed since the baseline: {', '.join(gone)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
