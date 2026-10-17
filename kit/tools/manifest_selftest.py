#!/usr/bin/env python3
"""Prove manifest.py and checkpin.py's installed-files check can FAIL. Invented fixtures only.
    python3 kit/tools/manifest_selftest.py"""
import os, sys, json, shutil, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
res = []
def case(label, ok, detail=""):
    res.append(bool(ok)); print("  %s  %s%s" % ("ok  " if ok else "FAIL", label, ("  [" + detail[:140] + "]") if detail and not ok else ""))
def run(args, cwd=None):
    p = subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr

tmp = tempfile.mkdtemp(prefix="manifest-")
try:
    print("the committed manifest")
    c, o = run([os.path.join(HERE, "manifest.py"), "--check"])
    case("the kit's own MANIFEST.json matches kit/ (a stale manifest cannot ship)", c == 0, o)

    print("a copy of the kit")
    k = os.path.join(tmp, "kit")
    shutil.copytree(KIT, k, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    c, o = run([os.path.join(HERE, "manifest.py"), "--check", "--kit", k]); case("an untouched copy passes", c == 0, o)
    css = os.path.join(k, "styles", "print.css")
    open(css, "a").write("\n/* edited under node_modules */\n")
    c, o = run([os.path.join(HERE, "manifest.py"), "--check", "--kit", k])
    case("an edited file fails and is named", c == 1 and "changed: styles/print.css" in o, o)
    shutil.copy(os.path.join(KIT, "styles", "print.css"), css)
    os.remove(os.path.join(k, "styles", "print.css"))
    c, o = run([os.path.join(HERE, "manifest.py"), "--check", "--kit", k])
    case("a missing file fails", c == 1 and "missing: styles/print.css" in o, o)
    shutil.copy(os.path.join(KIT, "styles", "print.css"), css)
    open(os.path.join(k, "stray.txt"), "w").write("x")
    c, o = run([os.path.join(HERE, "manifest.py"), "--check", "--kit", k])
    case("an extra file fails", c == 1 and "not in the manifest: stray.txt" in o, o)
    os.remove(os.path.join(k, "stray.txt"))
    os.remove(os.path.join(k, "MANIFEST.json"))
    c, o = run([os.path.join(HERE, "manifest.py"), "--check", "--kit", k])
    case("no manifest is reported as not verified (exit 2), never a pass", c == 2, o)

    print("checkpin.py on a fake archive")
    sha = "a" * 40
    root = os.path.join(tmp, "site"); os.makedirs(os.path.join(root, "node_modules", "@daviddef"))
    json.dump({"name": "x", "scripts": {}, "dependencies": {"@daviddef/archive-kit": "github:daviddef/TheArchiveKit#" + sha}}, open(os.path.join(root, "package.json"), "w"))
    json.dump({"packages": {"node_modules/@daviddef/archive-kit": {"resolved": "git+ssh://git@github.com/daviddef/TheArchiveKit.git#" + sha}}}, open(os.path.join(root, "package-lock.json"), "w"))
    inst = os.path.join(root, "node_modules", "@daviddef", "archive-kit", "kit")
    shutil.copytree(KIT, inst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    cp = os.path.join(inst, "tools", "checkpin.py")
    c, o = run([cp, "--root", root]); case("an installed kit that matches its manifest passes and says so", c == 0 and "match the kit's manifest" in o, o)
    pc = os.path.join(inst, "styles", "print.css")
    open(pc, "a").write("\n/* edited */\n")
    c, o = run([cp, "--root", root]); case("an edited installed file fails the pin check", c == 1 and "differ from the kit's own manifest" in o, o)
    shutil.copy(os.path.join(KIT, "styles", "print.css"), pc)
    os.remove(os.path.join(inst, "MANIFEST.json"))
    c, o = run([cp, "--root", root]); case("an installed kit with no manifest passes but says it is NOT verified", c == 0 and "NOT verified" in o, o)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
bad = res.count(False)
print("\nall %d cases behave" % len(res) if not bad else "\n%d FAILED" % bad)
sys.exit(1 if bad else 0)
