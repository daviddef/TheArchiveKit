#!/usr/bin/env python3
"""Prove check_row_pages.py can fail, on throwaway archives built here (nothing shipped is touched).

A gate only ever seen passing has not been seen working. Each case builds a tiny archive (searched.json, corrections.json, docs/row-pages.json, a dist
with a few built pages), runs the real script as a subprocess and asserts its exit code and what it names.

    python3 kit/tools/check_row_pages_selftest.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_row_pages.py")

fails = []


def expect(name, cond, detail=""):
    print("  %s  %s" % ("ok  " if cond else "FAIL", name))
    if not cond:
        fails.append(name)
        if detail:
            print("        " + detail.replace("\n", "\n        "))


def archive(rows, cfg, pages=("/imotski/", "/story/"), corrections=None):
    d = tempfile.mkdtemp(prefix="rowpages-")
    os.makedirs(os.path.join(d, "src", "data"))
    os.makedirs(os.path.join(d, "docs"))
    json.dump(rows, open(os.path.join(d, "src", "data", "searched.json"), "w"))
    if corrections is not None:
        json.dump(corrections, open(os.path.join(d, "src", "data", "corrections.json"), "w"))
    if cfg is not None:
        open(os.path.join(d, "docs", "row-pages.json"), "w").write(cfg if isinstance(cfg, str) else json.dumps(cfg))
    for p in ("/",) + tuple(pages):
        q = os.path.join(d, "dist", p.strip("/"))
        os.makedirs(q, exist_ok=True)
        open(os.path.join(q, "index.html"), "w").write("<html></html>")
    return d


def run(d, *extra):
    r = subprocess.run([sys.executable, SCRIPT, "--dist", "dist", *extra], cwd=d, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


FROM = {"from": "2026-11-12"}
good = {"when": "12 Nov 2026", "src": "FamilySearch", "what": "baptisms", "outcome": "found", "ev": [["/imotski/", "Imotski"]]}

# 1. a found row with a built ev page passes
d = archive([good], FROM)
rc, out = run(d)
expect("a found row whose ev page is built passes", rc == 0 and "ok" in out, out)

# 2. a found row with no ev fails, and is named
bad = {"when": "13 Nov 2026", "src": "DAPA", "what": "burials", "outcome": "hit", "key": "k-1"}
d = archive([good, bad], FROM)
rc, out = run(d)
expect("a found row with no ev fails", rc == 1 and "row 2 [k-1]" in out and "no `ev`" in out, out)

# 3. ev pointing at a page that is not built fails
d = archive([dict(good, ev=[["/nowhere/", "Nowhere"]])], FROM)
rc, out = run(d)
expect("ev to a page that is not built fails", rc == 1 and "/nowhere/" in out, out)

# 4. one built page among several is enough; an anchor and a query do not matter
d = archive([dict(good, ev=[["/nowhere/", "x"], ["/story/#p3", "Story"]])], FROM)
rc, out = run(d)
expect("one built page among the ev entries is enough (anchor ignored)", rc == 0, out)

# 5. logOnly passes without ev
d = archive([dict(bad, logOnly=True)], FROM)
rc, out = run(d)
expect("logOnly: true passes without ev", rc == 0, out)
d = archive([dict(bad, logOnly="yes")], FROM)
rc, out = run(d)
expect("logOnly must be true, not a word", rc == 1, out)

# 6. a row before the from date is not checked; the same row on the day is
d = archive([dict(bad, when="11 Nov 2026"), dict(bad, when="2026-11-01")], FROM)
rc, out = run(d)
expect("rows before the from date are not checked", rc == 0, out)
d = archive([dict(bad, when="2026-11-12")], FROM)
rc, out = run(d)
expect("the from date itself is checked", rc == 1, out)

# 7. nil, partial, blocked, undated and unknown-outcome rows are not 'found'
rows = [dict(bad, outcome=o) for o in ("nil", "partial", "blocked", "no Falco", "pending", "outstanding")] + [dict(bad, when="1814"), dict(bad, when="Arienzo 1890: tavolae")]
d = archive(rows, FROM)
rc, out = run(d)
expect("only found rows with a date pulse.js can read are checked", rc == 0, out)

# 8. the gate is off without docs/row-pages.json
d = archive([bad], None)
rc, out = run(d)
expect("no docs/row-pages.json: the gate is off, exit 0, and says so", rc == 0 and "OFF" in out, out)

# 9. a config that is not a date fails loudly (a typo must not switch the gate off)
for cfg in ('{"from": "12 Nov 2026"}', '{"from": "2026-13-45"}', "not json", "{}"):
    d = archive([bad], cfg)
    rc, out = run(d)
    expect("a bad config fails: %s" % cfg, rc == 1 and "FAIL" in out, out)

# 10. an outcome word the kit does not know, taught by the archive's config
d = archive([dict(bad, outcome="done")], FROM)
rc, out = run(d)
expect("an unknown outcome word is not found", rc == 0, out)
d = archive([dict(bad, outcome="done")], {"from": "2026-11-12", "outcomeMap": {"done": "found"}})
rc, out = run(d)
expect("outcomeMap {done: found} makes it found, so it fails", rc == 1, out)

# 11. fields: status for outcome, date for when
d = archive([{"date": "2026-11-13", "status": "yield", "src": "S"}], FROM)
rc, out = run(d)
expect("the alternative field names (date, status) are read", rc == 1, out)

# 11b. `fields` in the config: an archive that keeps its work date in another column (Falco: searchedOn; `when` is the year of the record)
falco = {"when": "1887", "searchedOn": "2026-11-13", "src": "MC55-VNL", "what": "Nascite 1889", "outcome": "hit", "key": "f-1"}
d = archive([falco], FROM)
rc, out = run(d)
expect("without fields, a row dated only in searchedOn is not checked (the gap this closes)", rc == 0 and "0 found rows" in out, out)
d = archive([falco], {"from": "2026-11-12", "fields": {"when": ["searchedOn"]}})
rc, out = run(d)
expect("with fields.when = [searchedOn] the row is read, found, and fails for want of ev", rc == 1 and "f-1" in out, out)
d = archive([dict(falco, ev=[["/imotski/", "Imotski"]])], {"from": "2026-11-12", "fields": {"when": ["searchedOn"]}})
rc, out = run(d)
expect("with fields.when and an ev page that is built it passes", rc == 0 and "1 found rows" in out, out)
d = archive([dict(falco, searchedOn="2026-11-10")], {"from": "2026-11-12", "fields": {"when": ["searchedOn"]}})
rc, out = run(d)
expect("a searchedOn before the gate date is not checked", rc == 0 and "0 found rows" in out, out)
for bad_f in ('{"from": "2026-11-12", "fields": {"when": "searchedOn"}}', '{"from": "2026-11-12", "fields": {"when": []}}', '{"from": "2026-11-12", "fields": []}'):
    d = archive([falco], bad_f)
    rc, out = run(d)
    expect("a malformed fields config fails loudly: %s" % bad_f, rc == 1 and "fields" in out, out)

# 12. rows under {searched: []} and with a _note row
d = archive({"sets": [], "searched": [{"_note": "to the reader"}, bad]}, FROM)
rc, out = run(d)
expect("{searched: []} is read and the _note row skipped", rc == 1 and "row 1" in out, out)

# 13. corrections: a where that is not a built page is a warning, never a failure
cor = [{"when": "13 Nov 2026", "what": "x", "where": "the /imotski/ page"}, {"when": "13 Nov 2026", "what": "y", "where": "/gone/ and /story/"},
       {"when": "1 Nov 2026", "what": "old", "where": "/old-gone/"}, {"when": "13 Nov 2026", "what": "z", "where": "the log, and/or the text"}]
d = archive([good], FROM, corrections=cor)
rc, out = run(d)
expect("a correction whose where is not a built page warns and still exits 0", rc == 0 and "warn" in out and "names /gone/" in out and "names /imotski/" not in out and "names /story/" not in out and "/old-gone/" not in out and "and/or" not in out, out)

# 14. without --dist the paths are only checked for shape, and it says so
d = archive([dict(good, ev=[["/nowhere/", "x"]])], FROM)
r = subprocess.run([sys.executable, SCRIPT], cwd=d, capture_output=True, text=True)
expect("no --dist: shape only, says so", r.returncode == 0 and "NOT verified" in r.stdout, r.stdout)

print("\n%s" % ("check_row_pages_selftest: %d FAILED" % len(fails) if fails else "check_row_pages_selftest: all ok"))
if __name__ == "__main__":
    sys.exit(1 if fails else 0)


def main():
    return 1 if fails else 0
