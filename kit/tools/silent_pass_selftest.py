#!/usr/bin/env python3
"""Prove the kit's gates refuse to pass on nothing, and that this test can fail.

Written 16 October 2026 after four sweeps (Mazza, Blazevic, D'Arcy, Luwinski) each found
kit gates that printed "ok" and exited 0 over a fault or over an empty input:

  checkliving.py   a GEDCOM date in capitals ("11 MAY 1990") was never harvested; a missing
                   --data directory counted as nobody living
  checktemplates   `astro check` crashed, it printed "ok every tag closes" over an unclosed tag
  sitemap.py       an empty dist wrote "0 urls" and exited 0 (a CI step)
  checkinline.py   an empty root printed "ok, 0 exempt"
  checkkin / checkrows / checkpages   "not run" and exit 0 (now an opt-in --require)
  checkarchive.py  its page floor was a fixed 5, so seven stub pages passed

Every case runs the CURRENT tools, and, when git has the previous kit commit, the SAME case
against the OLD tools. A case whose old tool does not pass silently proves nothing about the
fix, so the test says so rather than counting it.

    python3 kit/tools/silent_pass_selftest.py [--old <git rev>]     (default old: fcf629a)
"""
import os, sys, subprocess, tempfile, shutil, argparse, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = HERE


def run(tooldir, tool, args, cwd, env=None, timeout=120):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, os.path.join(tooldir, tool)] + args, cwd=cwd,
                       capture_output=True, text=True, env=e, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def page(title, body=""):
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>%s</title>"
            "<meta name=\"description\" content=\"%s\"></head><body><main><h1>%s</h1>%s</main></body></html>"
            % (title, title, title, body))


def make_dist(root, n=7, extra=None):
    d = os.path.join(root, "dist")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page("Home", extra or ""))
    for i in range(1, n):
        os.makedirs(os.path.join(d, "p%d" % i), exist_ok=True)
        open(os.path.join(d, "p%d" % i, "index.html"), "w", encoding="utf-8").write(page("Page %d" % i))
    return d


def fake_npx(root, body, code):
    b = os.path.join(root, "bin")
    os.makedirs(b, exist_ok=True)
    f = os.path.join(b, "npx")
    open(f, "w").write("#!/bin/sh\ncat <<'EOF'\n%s\nEOF\nexit %d\n" % (body, code))
    os.chmod(f, 0o755)
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="fcf629a")
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="silentpass-")
    old = None
    try:
        r = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        top = r.stdout.strip()
        if r.returncode == 0 and top:
            od = os.path.join(tmp, "oldkit")
            os.makedirs(od)
            import shlex
            ar = subprocess.run("git -C %s archive %s kit/tools | tar -x -C %s"
                                % (shlex.quote(top), shlex.quote(a.old), shlex.quote(od)),
                                shell=True, capture_output=True, text=True)
            if ar.returncode == 0 and os.path.isdir(os.path.join(od, "kit", "tools")):
                old = os.path.join(od, "kit", "tools")
        if not old:
            print("note: the old kit version could not be extracted, so the 'old tool passed silently' "
                  "controls are skipped")

        results = []   # (label, new_ok, old_passed_silently|None)

        def case(label, tool, args, cwd, want_new, env=None, control=True, expect_old=0):
            n_code, n_out = run(NEW, tool, args, cwd, env)
            ok_new = (n_code == want_new) if want_new != "fail" else (n_code != 0)
            o_state = None
            if old and control:
                o_code, _ = run(old, tool, args, cwd, env)
                o_state = (o_code == expect_old)
            results.append((label, ok_new, o_state))
            tag = "ok  " if ok_new else "FAIL"
            ctl = "" if o_state is None else ("  [old tool %s]" % ("passed silently, so this case can fail" if o_state
                                                                    else "did NOT behave as the case assumes"))
            print("  %s  %s%s" % (tag, label, ctl))
            if not ok_new:
                print("          exit %s, output: %s" % (n_code, n_out.strip().splitlines()[-1][:160] if n_out.strip() else ""))

        # ---- checkliving ------------------------------------------------------------
        for name, page_text, want, label in [
            ("leak", "<p>born 11 May 1990</p>", "fail", "checkliving: a GEDCOM-style date (11 MAY 1990) on a page is caught"),
            ("clean", "<p>nothing here</p>", 0, "checkliving: the same data with no date on any page passes (clean control)"),
        ]:
            d = os.path.join(tmp, "cl-" + name)
            make_dist(d, 7, page_text)
            os.makedirs(os.path.join(d, "data"))
            open(os.path.join(d, "data", "people.json"), "w", encoding="utf-8").write(
                '[{"name": "Fixture Personone", "living": true, "born": "11 MAY 1990", "died": ""}]')
            case(label, "checkliving.py", ["--dist", "dist", "--data", "data"], d, want,
                 control=(want == "fail"), expect_old=0)
        d = os.path.join(tmp, "cl-nodata")
        make_dist(d, 7, "<p>nothing</p>")
        case("checkliving: a missing --data directory fails instead of meaning nobody is living",
             "checkliving.py", ["--dist", "dist", "--data", "nodata"], d, "fail", expect_old=0)

        # ---- sitemap ----------------------------------------------------------------
        d = os.path.join(tmp, "sm")
        os.makedirs(os.path.join(d, "site", "dist"))
        open(os.path.join(d, "site", "astro.config.mjs"), "w").write("export default { site: 'https://x.example.com', base: '/' };")
        case("sitemap: an empty dist is refused, not written as '0 urls'", "sitemap.py",
             ["--dist", "dist"], os.path.join(d, "site"), "fail", expect_old=0)

        # ---- checktemplates ---------------------------------------------------------
        for name, body, code, want, label in [
            ("crash", "Error: Cannot find module '@volar/language-service/lib/features/provideHover.js'", 1, "fail",
             "checktemplates: an astro check that crashes is a failure, not 'ok every tag closes'"),
            ("fine", "Result (3 files):\n- 0 errors\n- 0 warnings\n- 0 hints", 0, 0,
             "checktemplates: an astro check that completes cleanly passes (clean control)"),
        ]:
            d = os.path.join(tmp, "tp-" + name)
            os.makedirs(os.path.join(d, "node_modules", "@astrojs", "check"))
            b = fake_npx(d, body, code)
            case(label, "checktemplates.py", ["--root", d], d, want,
                 env={"PATH": b + os.pathsep + os.environ.get("PATH", "")},
                 control=(want == "fail"), expect_old=0)

        # ---- checkinline ------------------------------------------------------------
        d = os.path.join(tmp, "in")
        os.makedirs(d)
        case("checkinline: a root with no templates is refused, not 'ok, 0 exempt'", "checkinline.py",
             ["--root", d], d, "fail", expect_old=0)

        # ---- opt-in --require -------------------------------------------------------
        d = os.path.join(tmp, "req")
        os.makedirs(d)
        case("checkkin --require: 'not run' becomes a failure", "checkkin.py",
             ["--data", os.path.join(d, "nofile.json"), "--require"], d, "fail", expect_old=2, control=False)
        case("checkkin without --require: 'not run' still exits 0 (the default is unchanged)", "checkkin.py",
             ["--data", os.path.join(d, "nofile.json")], d, 0, control=False)
        dd = os.path.join(d, "r")
        os.makedirs(os.path.join(dd, "dist"))
        case("checkrows --require: 'not run' becomes a failure", "checkrows.py",
             ["--root", dd, "--require"], dd, "fail", control=False)
        case("checkpages --require: 'not run' becomes a failure", "checkpages.py",
             ["--root", dd, "--estate", dd, "--require"], dd, "fail", control=False)
        case("checkpages without --require: 'not run' still exits 0", "checkpages.py",
             ["--root", dd, "--estate", dd], dd, 0, control=False)

        # ---- checkarchive -----------------------------------------------------------
        d = os.path.join(tmp, "ca")
        make_dist(d, 7)
        case("checkarchive: seven stub pages are below the floor", "checkarchive.py",
             ["--dist", "dist"], d, "fail", expect_old=0)
        # --min-pages is adjustable, so a small legitimate site is not locked out
        case("checkarchive: --min-pages 5 lets the same small site through (the floor is adjustable)",
             "checkarchive.py", ["--dist", "dist", "--min-pages", "5"], d, 0, control=False)

        print()
        bad = [r for r in results if not r[1]]
        weak = [r for r in results if r[2] is False]
        if bad:
            print("%d case(s) FAILED:" % len(bad))
            for r in bad:
                print("  - " + r[0])
        if weak:
            print("note: %d case(s) whose OLD tool did not behave as assumed, so they prove less:" % len(weak))
            for r in weak:
                print("  - " + r[0])
        print("\nall cases behave" if not bad else "")
        return 1 if bad else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
