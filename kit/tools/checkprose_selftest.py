#!/usr/bin/env python3
"""Prove checkprose.py can fail, and does not cry wolf. Every name here is invented and every year is
impossible for a living person (1899), so no real person's value is a literal in this file.

    python3 kit/tools/checkprose_selftest.py
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checkprose as cp

NAME = "Fixtura Zzyzx"
OTHER = "Aurelia Qqvox"
FEED = {"living": [{"id": "p1", "names": [NAME, "Fixtura Maxima Zzyzx"]}], "deadNames": [OTHER + " Dead"]}
results = []


def case(label, ok, detail=""):
    ok = bool(ok)          # a falsy {} must count as a failure, not slip past results.count(False)
    results.append(ok)
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", label, ("  [" + detail + "]") if detail and not ok else ""))


def tree(files):
    t = tempfile.mkdtemp(prefix="cprose-")
    for rel, body in files.items():
        p = os.path.join(t, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(body)
    return t


def go(files, living=None, dead=None, **kw):
    t = tree(files)
    kw.setdefault("include", cp.DEFAULT_INCLUDE + ["site/src/data/**/*"])
    try:
        f, s = cp.run(t, living if living is not None else [FEED["living"][0]["names"]],
                      dead if dead is not None else FEED["deadNames"], use_git=False, **kw)
        return f, s
    finally:
        shutil.rmtree(t, ignore_errors=True)


P = "site/src/pages/x.astro"
print("a living person in prose")
f, s = go({P: "<p>%s, son of %s, of Zagreb, Croatia.</p>" % (NAME, OTHER)})
case("name + relationship + town and country passes (clean control)", not f and s["places"] == 1, str(f))
f, s = go({P: "<p>%s was born in 1899 in Zagreb.</p>" % NAME})
case("a year beside the name fails", any("a year" in x for x in f), str(f))
f, s = go({P: "<p>%s, born 11 May 1899.</p>" % NAME})
case("a full date beside the name fails", any("full date" in x for x in f), str(f))
f, s = go({P: "<p>%s, 05/11/1899.</p>" % NAME})
case("a slash date fails (not eaten by the url pattern)", any("slash date" in x for x in f), str(f))
f, s = go({P: "<p>%s (1899-1901).</p>" % NAME})
case("a hyphenated year range fails", any("a year" in x for x in f), str(f))
f, s = go({P: "<p>%s died in Zagreb.</p>" % NAME})
case("a life-event word fails", any("life-event" in x for x in f), str(f))
f, s = go({P: "<p>%s shares 212 cM with the tester.</p>" % NAME})
case("a DNA result (centimorgans) beside the name fails", any("DNA result" in x for x in f), str(f))
f, s = go({P: "<p>%s is a DNA match of the tester.</p>" % NAME})
case("'DNA match' beside the name fails", any("DNA result" in x for x in f), str(f))
f, s = go({P: "<p>%s, son of %s. The DNA page explains the method.</p>\n<p>Elsewhere.</p>" % (NAME, OTHER)})
case("a plain mention of 'the DNA page' is not a result and passes", not f, str(f))
f, s = go({P: "<p>%s, son of %s.</p>\n\n<p>The DNA page explains the method.</p>" % (NAME, OTHER)})
case("DNA in the NEXT paragraph is not this person's", not f, str(f))
f, s = go({P: "<p>%s, son of %s.</p>\n\n<p>The register opens in 1899.</p>" % (NAME, OTHER)})
case("a year in the NEXT paragraph is not this person's", not f, str(f))
f, s = go({P: "<p>%s, <a href=\"/person/fixtura-zzyzx-1899/\">page</a>.</p>" % NAME})
case("a year only inside a url is counted, not failed", not f and s["slug_years"] == 1, "%s %s" % (f, s))
f, s = go({P: '<script type="application/ld+json">{"name":"%s","birthDate":"1899-01-02"}</script>' % NAME})
case("JSON-LD with a birthDate fails", bool(f), str(f))
f, s = go({P: "<p>FIXTURA ZZYZX, born 1899.</p>"})
case("capitals (a GEDCOM spelling) are still matched", bool(f), str(f))
f, s = go({P: "<p>Fíxtura Zzýzx, born 1899.</p>"})
case("accents are folded", bool(f), str(f))
f, s = go({P: "<p>Fixtura Maxima Zzyzx, born 1899.</p>"})
case("the full recorded name is a phrase too", bool(f), str(f))

print("a living person in JSON")
f, s = go({"site/src/data/s.json": json.dumps([{"name": NAME, "father": OTHER, "place": "Zagreb, Croatia"}])})
case("a record with only allowed fields passes", not f and s["places"] == 1, str(f))
f, s = go({"site/src/data/s.json": json.dumps([{"name": NAME, "born": "1899"}])})
case("a record with a born field fails", bool(f), str(f))
f, s = go({"site/src/data/s.json": json.dumps([{"name": NAME, "notes": "a plain note"}])})
case("a record with a field outside --allow-keys fails", any("fields beyond" in x for x in f), str(f))
f, s = go({"site/src/data/s.json": json.dumps([{"name": NAME, "notes": "a plain note"}])}, allow_keys={"notes", "name"})
case("--allow-keys widens the list for an archive that needs a field", not f, str(f))
f, s = go({"site/src/data/s.json": json.dumps({"entries": [{"text": "%s, born 1899" % NAME}]})})
case("a living name inside a free-text value is read as prose", bool(f), str(f))
f, s = go({"site/src/data/s.tsv": "id\tname\tdate\np1\t%s\t1899\n" % NAME})
case("a tsv row with a year fails", bool(f), str(f))

print("scope")
f, s = go({"site/src/pages/x.astro": "---\n/* %s, born 1899 */\n// %s died\n---\n<p>fine</p>" % (NAME, NAME)})
case("a name in a code comment is not published and is not read", not f and s["places"] == 0, str((f, s)))
f, s = go({P: "<!-- %s, born 1899 -->" % NAME})
case("an HTML comment is published, so it is read", bool(f), str(f))
f, s = go({"site/src/data/s.json": json.dumps([{"name": NAME, "born": "1899"}])}, include=cp.DEFAULT_INCLUDE)
case("a data file is not read by default (generated data has its own gate)", "refusing" in " ".join(f), str((f, s)))

print("homonyms")
f, s = go({P: "<p>%s, born 1899.</p>" % NAME}, living=[[NAME], ["Unrelata Wwvix"]], dead=[NAME])
case("a name shared with a dead person is skipped and counted, not guessed at", not f and s["ambiguous"] >= 1, str((f, s)))

print("refusals")
f, s = go({P: "<p>x</p>"}, living=[])
case("an empty feed is refused", any("refusing" in x for x in f), str(f))
f, s = go({P: "<p>x</p>"}, living=[], allow_none=True)
case("--allow-none lets an archive with no living person through", not f, str(f))
f, s = go({"notes.txt": "x"})
case("no matching file is refused", any("refusing" in x for x in f), str(f))

print("allowances")
al = [{"file": P, "phrase": NAME, "year": "1899", "reason": "the year belongs to his grandfather"}]
f, s = go({P: "<p>%s, grandson of the 1899 emigrant.</p>" % NAME}, allow=al)
case("a reasoned allowance lets a true false positive through", not f and s["allowed"] == 1, str(f))
f, s = go({P: "<p>%s, of Zagreb.</p>" % NAME}, allow=al)
case("an allowance that matches nothing fails", any("matches nothing" in x for x in f), str(f))
f, s = go({P: "<p>%s, grandson of the 1899 emigrant.</p>" % NAME}, allow=[dict(al[0], reason="")])
case("an allowance with no reason fails", any("no reason" in x for x in f), str(f))

print("the log never carries a value")
f, s = go({P: "<p>%s, born 11 May 1899 in Zagreb.</p>" % NAME})
out = " ".join(f)
case("a failure line names no date, year or person", "1899" not in out and "Zzyzx" not in out and "Fixtura" not in out, out)

print("a failing run still says what it examined")
t0 = tree({P: "<p>%s, born 1899.</p>" % NAME})
try:
    fd = os.path.join(t0, "feed.json"); json.dump(FEED, open(fd, "w"))
    r0 = subprocess.run([sys.executable, os.path.join(HERE, "checkprose.py"), "--root", t0, "--feed", fd, "--no-git"],
                        capture_output=True, text=True)
    case("a failure prints files read, phrases and places as well", r0.returncode == 1 and "examined:" in r0.stdout and "1899" not in r0.stdout, r0.stdout)
finally:
    shutil.rmtree(t0, ignore_errors=True)

print("tracked files only")
t = tree({P: "<p>%s, of Zagreb.</p>" % NAME})
try:
    subprocess.run(["git", "-C", t, "init", "-q"], check=True)
    subprocess.run(["git", "-C", t, "-c", "user.email=a@b", "-c", "user.name=t", "add", "-A"], check=True)
    subprocess.run(["git", "-C", t, "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "x"], check=True)
    open(os.path.join(t, "site/src/pages/new.astro"), "w").write("<p>%s, born 1899.</p>" % NAME)
    f, s = cp.run(t, [[NAME]], [], use_git=True)
    case("an untracked matching file is itself a failure", any("not tracked" in x for x in f), str(f))
    subprocess.run(["git", "-C", t, "add", "-A"], check=True)
    f, s = cp.run(t, [[NAME]], [], use_git=True)
    case("once added, the same file is read and its year is caught", any("new.astro" in x and "a year" in x for x in f), str(f))
finally:
    shutil.rmtree(t, ignore_errors=True)

print("the CLI")
t = tree({P: "<p>%s, born 1899.</p>" % NAME})
try:
    feed = os.path.join(t, "feed.json")
    json.dump(FEED, open(feed, "w"))
    r = subprocess.run([sys.executable, os.path.join(HERE, "checkprose.py"), "--root", t, "--feed", feed, "--no-git"],
                       capture_output=True, text=True)
    case("the command exits 1 on a fault", r.returncode == 1, r.stdout)
    r = subprocess.run([sys.executable, os.path.join(HERE, "checkprose.py"), "--root", t, "--no-git"], capture_output=True, text=True)
    case("no feed is 'not run' (exit 2), never a pass", r.returncode == 2, r.stdout)
finally:
    shutil.rmtree(t, ignore_errors=True)
case("the built-in self-proof holds", cp.prove() == "", cp.prove())

bad = results.count(False)
print("\n%d case(s) FAILED" % bad if bad else "\nall %d cases behave" % len(results))
sys.exit(1 if bad else 0)
