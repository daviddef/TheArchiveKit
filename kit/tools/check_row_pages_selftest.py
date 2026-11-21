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


def archive(rows, cfg, pages=("/imotski/", "/story/"), corrections=None, html=None):
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
        open(os.path.join(q, "index.html"), "w", encoding="utf-8").write((html or {}).get(p, "<html></html>"))
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

# 11c. WHO: `peopleFrom` makes a found row name its people (for) or say nobody
PF = {"from": "2026-11-12", "peopleFrom": "2026-11-14"}
ev = [["/imotski/", "Imotski"]]
base = {"when": "2026-11-14", "src": "S", "what": "w", "outcome": "found", "ev": ev, "key": "p-1"}
d = archive([base], PF); rc, out = run(d)
expect("peopleFrom: a found row from that day with no for and no nobody fails", rc == 1 and "p-1" in out and "who it is for" in out, out)
d = archive([dict(base, **{"for": [["/story/", "Ann"]]})], PF); rc, out = run(d)
expect("peopleFrom: a row naming a built person page passes", rc == 0 and "ok" in out, out)
d = archive([dict(base, nobody=True)], PF); rc, out = run(d)
expect("peopleFrom: nobody:true passes", rc == 0, out)
d = archive([dict(base, **{"for": [["/story/", "Ann"]], "nobody": True})], PF); rc, out = run(d)
expect("peopleFrom: for and nobody together fail", rc == 1 and "both" in out, out)
d = archive([dict(base, **{"for": [["/nobody-home/", "Ann"]]})], PF); rc, out = run(d)
expect("peopleFrom: a for page that is not built fails (a living person has no page)", rc == 1 and "not built" in out, out)
d = archive([dict(base, **{"for": [["/story/", "Ann"], ["/story/", "Ann"]]})], PF); rc, out = run(d)
expect("peopleFrom: a page listed twice fails", rc == 1 and "twice" in out, out)
d = archive([dict(base, **{"for": [["/story/", " "]]})], PF); rc, out = run(d)
expect("peopleFrom: an entry with a blank name fails", rc == 1 and "no name" in out, out)
d = archive([dict(base, when="2026-11-13")], PF); rc, out = run(d)
expect("peopleFrom: a found row before that day is not asked for people", rc == 0, out)
d = archive([dict(base, outcome="nothing")], PF); rc, out = run(d)
expect("peopleFrom: a nil row is not asked for people", rc == 0, out)
d = archive([base], {"from": "2026-11-12"}); rc, out = run(d)
expect("without peopleFrom the people rule is off", rc == 0, out)
d = archive([base], {"from": "2026-11-12", "peopleFrom": "tomorrow"}); rc, out = run(d)
expect("a malformed peopleFrom fails loudly", rc == 1 and "peopleFrom" in out, out)

# 12. rows under {searched: []} and with a _note row
d = archive({"sets": [], "searched": [{"_note": "to the reader"}, bad]}, FROM)
rc, out = run(d)
expect("{searched: []} is read and the _note row skipped", rc == 1 and "row 1" in out, out)


# 12b. DEEP LINKS (22 November 2026): from deepFrom an ev entry must reach the passage: an anchor that exists, or a phrase that occurs once; a long page needs one or the other
DF = {"from": "2026-11-12", "deepFrom": "2026-11-14", "deepMinKb": 1}
FILL = "<p>filler text of the page.</p>" * 80
PAGE = ("<html><head><title>head words</title><style>.x{}</style></head><body><h2 id=\"sec-a\">Section A</h2>" + FILL +
        "<p>The Scopliaco of the certificate is <b>Škopljak</b> in Gračišće municipality.</p><p>Fish &amp; chips at the market.</p>"
        "<p>Twice said.</p><div>Twice said.</div><p>across</p><p>blocks</p><script>var hidden='only in script';</script></body></html>")
HT = {"/imotski/": PAGE}
drow = {"when": "2026-11-14", "src": "S", "what": "w", "outcome": "found", "nobody": True, "key": "d-1"}
def deep(ev, cfg=DF, **kw):
    return run(archive([dict(drow, ev=ev, **kw)], cfg, html=HT))
rc, out = deep([["/imotski/", "Imotski"]])
expect("deep: a bare link to a page over deepMinKb fails and names the size", rc == 1 and "d-1" in out and "KB" in out and "changed passage" in out, out)
rc, out = deep([["/story/", "Story"]])
expect("deep: a bare link to a small page passes", rc == 0, out)
rc, out = deep([["/imotski/#sec-a", "Imotski"]])
expect("deep: an anchor that exists passes on a long page", rc == 0 and "deep links checked" in out, out)
rc, out = deep([["/imotski/#nope", "Imotski"]])
expect("deep: an anchor that is not in the page fails", rc == 1 and "#nope" in out, out)
rc, out = deep([["/story/#nope", "Story"]])
expect("deep: a missing anchor fails even on a small page", rc == 1 and "#nope" in out, out)
rc, out = deep([["/imotski/", "Imotski", "Škopljak in Gračišće"]])
expect("deep: a phrase in the page text (inline tags and accents) passes", rc == 0, out)
rc, out = deep([["/imotski/", "Imotski", "SCOPLIACO   of the CERTIFICATE"]])
expect("deep: matching ignores case and spacing, as the browser does", rc == 0, out)
rc, out = deep([["/imotski/", "Imotski", "Fish & chips"]])
expect("deep: an entity in the page matches the phrase as read (&amp; = &)", rc == 0, out)
rc, out = deep([["/imotski/", "Imotski", "Scopliaco of the Gologorica certificate"]])
expect("deep: a phrase that is not in the page fails", rc == 1 and "not in the page" in out, out)
rc, out = deep([["/imotski/", "Imotski", "Twice said."]])
expect("deep: a phrase that occurs twice fails (the link would land on the first)", rc == 1 and "occurs 2 times" in out, out)
rc, out = deep([["/imotski/", "Imotski", "across blocks"]])
expect("deep: a phrase cannot run across two blocks (a text fragment cannot either)", rc == 1 and "not in the page" in out, out)
rc, out = deep([["/imotski/", "Imotski", "only in script"]])
expect("deep: text only in a script is not the reader's text", rc == 1, out)
rc, out = deep([["/imotski/", "Imotski", "head words"]])
expect("deep: text in <head> (the title) is not found either", rc == 1, out)
for ph in ("ab", "**Škopljak** in", "[Škopljak](/x/) in Gračišće", "x" * 121, 5):
    rc, out = deep([["/imotski/", "Imotski", ph]])
    expect("deep: an unusable phrase fails: %r" % (ph if not isinstance(ph, str) else ph[:20]), rc == 1, out)
rc, out = deep([["/story/", "Story"], ["/imotski/", "Imotski"]])
expect("deep: every ev entry is held to it, not only the first (a bare long page second fails)", rc == 1 and "KB" in out, out)
rc, out = deep([["/imotski/", "Imotski", "Škopljak in Gračišće"], ["/imotski/#sec-a", "Imotski again"]])
expect("deep: two deep links to one page pass", rc == 0, out)
d = archive([dict(drow, when="2026-11-13", ev=[["/imotski/", "Imotski"]])], DF, html=HT); rc, out = run(d)
expect("deep: a row before deepFrom is not asked for it", rc == 0, out)
d = archive([dict(drow, ev=[["/imotski/", "Imotski"]])], {"from": "2026-11-12"}, html=HT); rc, out = run(d)
expect("deep: without deepFrom the rule is off", rc == 0 and "deep links" not in out, out)
d = archive([dict(drow, ev=[["/imotski/", "Imotski"]], logOnly=True)], DF, html=HT); rc, out = run(d)
expect("deep: logOnly rows have no pages to deepen", rc == 0, out)
d = archive([dict(drow, outcome="nothing", ev=[["/imotski/", "Imotski"]])], DF, html=HT); rc, out = run(d)
expect("deep: a nil row is not asked for it", rc == 0, out)
d = archive([dict(drow, ev=[["/imotski/", "Imotski"]])], dict(DF, deepMinKb=100), html=HT); rc, out = run(d)
expect("deep: the default-size threshold leaves a 3 KB page bare", rc == 0, out)
for bad_c in (dict(DF, deepFrom="2026-11-01"), dict(DF, deepFrom="soon"), dict(DF, deepMinKb="big"), dict(DF, deepMinKb=-1), dict(DF, deepMinKb=True)):
    d = archive([drow], bad_c, html=HT); rc, out = run(d)
    expect("deep: a malformed config fails loudly: %s" % json.dumps({k: v for k, v in bad_c.items() if k.startswith("deep")}), rc == 1 and "deep" in out, out)

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
