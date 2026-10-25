#!/usr/bin/env python3
"""Prove the printed-year gate (livingyears.py) catches what it says it catches, and can fail.

    python3 kit/tools/livingyears_selftest.py

A clean synthetic build and its people data are written to a temp directory. The gate must PASS the clean build (and the
controls that look like faults and are not: a dead person's birth beside a death, a person born one year before the line,
a copyright year, a sitemap date), then CATCH one planted fault per detector in a copy of it, then honour an allow-list entry,
an allow-prefix, and refuse to run on an empty build. Every planted value is an invented person on an invented site.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import living_rule as lr  # noqa: E402
import livingyears as ly  # noqa: E402

TODAY = 2026
CUT = lr.cutoff_year(TODAY)          # 1946
bad = []


def check(label, ok, detail=""):
    print("  %s  %s" % ("ok  " if ok else "FAIL", label))
    if not ok:
        bad.append(label)
        if detail:
            print("          " + detail)


def page(body, title="Page"):
    return "<!doctype html><html><head><title>%s</title><meta name=\"description\" content=\"A page\"></head><body><main>%s</main>" \
           "<footer>&copy; %d Testville Archive</footer></body></html>" % (title, body, TODAY)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


PEOPLE = [
    # living by the rule: born on or after the line, no death record
    {"name": "Wilma Quentin", "born": CUT, "died": ""},                                  # the boundary year itself
    {"name": "Percival Ostrander", "born": CUT + 1, "died": "", "citations": ["FamilySearch ark:/1/2"]},   # a citation frees nobody
    {"name": "Ludmilla Farnsworth", "born": CUT + 30, "dead": True},                     # a bare flag is not a death record
    {"name": "Barnaby Thistlewood", "born": 2005, "died": "deceased"},                   # the word alone: still a flag
    # not living: born before the line
    {"name": "Cornelius Ashdown", "born": CUT - 1, "died": ""},
    # dead young: a death RECORD beside a year inside the window
    {"name": "Rosalind Pembroke", "born": CUT + 4, "died": "1999"},
    {"name": "Wilma Quentin", "born": 1801, "died": "1860"},                             # a dead namesake of a living woman
]


def build(root, today=TODAY):
    dist, data = os.path.join(root, "dist"), os.path.join(root, "data")
    for i in range(1, 7):
        write(os.path.join(dist, "page%d" % i, "index.html"),
              page("<p>An ordinary page about a ship, a parish and a register, number %d.</p>" % i))
    # controls that must NOT fire
    write(os.path.join(dist, "people", "rosalind", "index.html"),
          page("<h1>Rosalind Pembroke</h1><p>b. %d, d. 1999, Testville.</p>" % (CUT + 4)))
    write(os.path.join(dist, "people", "cornelius", "index.html"),
          page("<h1>Cornelius Ashdown</h1><p>b. %d in Testville.</p>" % (CUT - 1)))
    write(os.path.join(dist, "people", "wilma-old", "index.html"),
          page("<h1>Wilma Quentin</h1><p>1801-1860. Wilma Quentin, 1801, of Testville.</p>"))
    write(os.path.join(dist, "sitemap.xml"), "<urlset><url><loc>https://x.test/</loc><lastmod>%d-10-25</lastmod></url></urlset>" % today)
    write(os.path.join(dist, "search.json"), json.dumps([{"t": "Rosalind Pembroke", "b": CUT + 4, "d": 1999}, {"t": "Cornelius Ashdown", "b": CUT - 1}]))
    write(os.path.join(data, "people.json"), json.dumps({"people": PEOPLE}))
    return dist, data


def run(dist, data, today=TODAY, allow=None, strict=False):
    out = []
    rc, fails, info = ly.run(dist, data, today, allow, quiet=True, strict_allow=strict, say=lambda s="": out.append(s))
    return rc, fails, info, "\n".join(out)


def planted(label, relpath, content, detector, **kw):
    root = tempfile.mkdtemp(prefix="livingyears-st-")
    try:
        dist, data = build(root)
        write(os.path.join(dist, relpath), content)
        rc, fails, info, out = run(dist, data, **kw)
        check("%s is caught by %s" % (label, detector), rc == 1 and any(f[1] == detector for f in fails),
              "rc=%s detectors=%s %s" % (rc, sorted({f[1] for f in fails}), out[:200]))
    finally:
        shutil.rmtree(root, ignore_errors=True)


print("the clean build and the controls")
root = tempfile.mkdtemp(prefix="livingyears-st-")
try:
    dist, data = build(root)
    rc, fails, info, out = run(dist, data)
    check("a clean build passes", rc == 0, out[:400] + " " + str(fails[:3]))
    check("the line is %d (= %d - %d)" % (CUT, TODAY, lr.LIVING_YEARS), info.get("cut") == CUT == 1946)
    check("the people set follows the rule: 4 living (a citation, a bare flag and the word 'deceased' do not free anyone from it), 1 dead-young",
          info.get("living") == 4 and info.get("dead_young") == 1, str(info))
    check("the gate's own probe passes", ly.probe(TODAY)[0])
finally:
    shutil.rmtree(root, ignore_errors=True)

print("one planted fault per detector")
planted("a birth shape «b. YEAR» in the boundary year with no death", "people/x/index.html",
        page("<h1>Somebody</h1><p>b. %d, Testville, Nowhere</p>" % CUT), "birth-shape")
planted("«born in YEAR» a year after the line", "story/index.html",
        page("<p>She was born in Testville in %d, the youngest of four.</p>" % (CUT + 20)), "birth-shape")
planted("an open span «(YEAR-)»", "story/index.html", page("<p>Ludmilla (%d-) of Testville</p>" % (CUT + 30)), "birth-shape")
planted("a birthDate in JSON-LD", "people/y/index.html",
        "<!doctype html><html><head><title>t</title><script type=\"application/ld+json\">{\"@type\":\"Person\",\"birthDate\":\"%d-04-24\"}</script></head><body><main><p>x</p></main></body></html>" % (CUT + 3),
        "birth-shape")
planted("a birth in a meta description", "people/z/index.html",
        "<!doctype html><html><head><title>t</title><meta name=\"description\" content=\"Somebody, born %d in Testville\"></head><body><main><p>x</p></main></body></html>" % (CUT + 5),
        "birth-shape")
planted("a living person's name beside their own year in a table", "register/index.html",
        page("<table><tr><td>Percival Ostrander</td><td>%d</td><td>Testville</td></tr></table>" % (CUT + 1)), "name-year")
planted("the year BEFORE the name", "timeline/index.html", page("<p>%d: Ludmilla Farnsworth, Testville</p>" % (CUT + 30)), "name-year")
planted("a person with only a bare 'deceased' flag (not a record) and their year", "register/index.html",
        page("<p>Barnaby Thistlewood (2005) of Nowhere</p>"), "name-year")
planted("a data row with a birth year and no death in a built .json", "data/list.json",
        json.dumps([{"name": "Nobody Inparticular", "born": CUT + 2}]), "json-row")
planted("a data row whose only death is a bare flag", "data/list.json",
        json.dumps({"rows": [{"n": "Nobody Inparticular", "b": CUT + 2, "dead": True}]}), "json-row")
planted("a year in an .xml feed", "feed.xml", "<feed><entry><summary>Wilma Quentin, b. %d, of Testville</summary></entry></feed>" % CUT, "birth-shape")
planted("a year in plain .txt", "notes.txt", "Ludmilla Farnsworth %d" % (CUT + 30), "name-year")

print("the boundary and the calendar")
planted("born %d (the line) is caught" % CUT, "story/index.html", page("<p>b. %d</p>" % CUT), "birth-shape")
root = tempfile.mkdtemp(prefix="livingyears-st-")
try:
    dist, data = build(root)
    write(os.path.join(dist, "story", "index.html"), page("<p>b. %d in Testville</p>" % (CUT - 1)))
    rc, fails, info, out = run(dist, data)
    check("born %d (one before the line) is not a living person's year" % (CUT - 1), rc == 0, out[:300])
    write(os.path.join(dist, "story", "index.html"), page("<p>b. %d in Testville</p>" % CUT))
    rc27, fails27, info27, out27 = run(dist, data, today=2027)
    check("the line moves with the calendar: in 2027 it is %d, so b. %d passes (those born then are no longer living)" % (CUT + 1, CUT),
          info27.get("cut") == CUT + 1 and not any(f[0] == "story/index.html" for f in fails27), str(fails27[:2]))
    write(os.path.join(dist, "story", "index.html"), page("<p>b. %d in Testville</p>" % (CUT + 1)))
    rc27, fails27, info27, out27 = run(dist, data, today=2027)
    check("and in 2027 b. %d is caught" % (CUT + 1), any(f[0] == "story/index.html" for f in fails27))
finally:
    shutil.rmtree(root, ignore_errors=True)

print("the escapes are decisions")
root = tempfile.mkdtemp(prefix="livingyears-st-")
try:
    dist, data = build(root)
    write(os.path.join(dist, "bishops", "index.html"), page("<p>Table: Born %d, ordained priest later.</p>" % (CUT + 7)))
    rc, fails, info, out = run(dist, data)
    check("the planted fault is caught before the registry", rc == 1)
    al = ly.Allow()
    al.add("Born %d, ordained priest later." % (CUT + 7), "a bishop's table: the word Born heads a column of ordination years")
    rc, fails, info, out = run(dist, data, allow=al)
    check("a registry entry with a reason removes exactly that text", rc == 0, out[:300])
    al2 = ly.Allow()
    al2.add("a sentence that is nowhere in the build", "reviewed once and the page was since rewritten")
    rc, fails, info, out = run(dist, data, allow=al2)
    check("a stale registry entry is counted", info.get("stale") == 1 and rc == 1)  # the fault is still there
    os.remove(os.path.join(dist, "bishops", "index.html"))
    rc, fails, info, out = run(dist, data, allow=al2, strict=True)
    check("--strict-allow fails a stale entry", rc == 1 and "stale" in out, out[:200])
    rc, fails, info, out = run(dist, data, allow=al2, strict=False)
    check("and without it the stale entry is only counted", rc == 0 and info["stale"] == 1)
    write(os.path.join(dist, "gazetteer.json"), json.dumps([{"name": "Nobody Inparticular", "born": CUT + 2}]))
    al3 = ly.Allow()
    al3.prefixes = ["/gazetteer"]
    rc, fails, info, out = run(dist, data, allow=al3)
    check("--allow-prefix exempts a file that is not about people", rc == 0, out[:200])
    reg = os.path.join(root, "reg.json")
    json.dump({"allow": [{"text": "x", "why": "short"}]}, open(reg, "w"))
    try:
        ly.Allow().load(reg)
        check("a registry entry with a short reason is refused", False)
    except ValueError:
        check("a registry entry with a short reason is refused", True)
    # the four archives' registries are read as they stand
    json.dump({"allow": [{"text": "Giovanni (b. %d)" % CUT, "why": "a registered death, a different household"}]}, open(reg, "w"))
    a = ly.Allow(); a.load(reg)
    check("the Mazza-style registry {allow:[{text,why}]} is read as it stands", len(a.entries) == 1)
    json.dump({"unpublished_deaths": [{"slug": "x", "reason": "a burial"}], "snippets": [{"file": "*", "contains": "abc", "reason": "not a birth: a table heading"}]}, open(reg, "w"))
    a = ly.Allow(); a.load(reg)
    check("the Lerena-style registry {snippets:[{file,contains,reason}]} is read as it stands", len(a.entries) == 1)
    # Lerena-style unpublished_deaths: the data records a death no page prints; their page and name are exempt
    reg2 = os.path.join(root, "reg2.json")
    json.dump({"unpublished_deaths": [{"slug": "percival-ostrander", "reason": "a burial register line, not printed on the page"}]}, open(reg2, "w"))
    al4 = ly.Allow(); al4.load(reg2)
    os.remove(os.path.join(dist, "gazetteer.json"))
    write(os.path.join(dist, "people", "percival-ostrander", "index.html"), page("<h1>Percival Ostrander</h1><p>b. %d, Testville</p>" % (CUT + 1)))
    write(os.path.join(dist, "register", "index.html"), page("<p>Percival Ostrander (%d)</p>" % (CUT + 1)))
    rc0, f0, i0, o0 = run(dist, data)
    rc1, f1, i1, o1 = run(dist, data, allow=al4)
    check("unpublished_deaths: without it the page is a breach, with it the person's page and name are exempt", rc0 == 1 and rc1 == 0, o1[:300])
    os.remove(os.path.join(dist, "register", "index.html"))
    os.remove(os.path.join(dist, "people", "percival-ostrander", "index.html"))
    cfgp = os.path.join(root, "standard.json")
    json.dump({"version": 1, "living_years": {"allow_file": "reg.json", "allow_prefixes": ["/gazetteer"]}}, open(cfgp, "w"))
    c = ly.load_config(cfgp)
    check("standard.json's living_years block names the registry and prefixes", c["allow_file"] == reg and c["allow_prefixes"] == ["/gazetteer"])
finally:
    shutil.rmtree(root, ignore_errors=True)

print("a run that could not look is not a pass")
root = tempfile.mkdtemp(prefix="livingyears-st-")
try:
    dist, data = build(root)
    shutil.rmtree(os.path.join(dist, "people"))
    for i in range(1, 7):
        shutil.rmtree(os.path.join(dist, "page%d" % i))
    rc, *_ = run(dist, data)
    check("an empty build is refused", rc == 1)
    dist, data = build(tempfile.mkdtemp(prefix="livingyears-st-"))
    write(os.path.join(data, "broken.json"), "{ not json")
    rc, fails, info, out = run(dist, data)
    check("an unreadable data file is refused", rc == 1 and "could not be read" in out, out[:200])
    os.remove(os.path.join(data, "broken.json"))
    os.remove(os.path.join(data, "people.json"))
    rc, fails, info, out = run(dist, data)
    check("a data directory with no people in it is refused", rc == 1 and "no person" in out, out[:200])
    rc, fails, info, out = run(dist, os.path.join(data, "nowhere"))
    check("a missing data directory is refused", rc == 1)
finally:
    shutil.rmtree(root, ignore_errors=True)

print("the test can fail")
_cut = lr.cutoff_year
lr.cutoff_year = lambda t=None: _cut(t) + 1
root = tempfile.mkdtemp(prefix="livingyears-st-")
try:
    dist, data = build(root)
    write(os.path.join(dist, "story", "index.html"), page("<p>b. %d in Testville</p>" % CUT))
    rc, *_ = run(dist, data)
    check("a cutoff one year late lets the boundary year through, and the boundary test above would catch it", rc == 0)
finally:
    shutil.rmtree(root, ignore_errors=True)
    lr.cutoff_year = _cut
_dk = lr.death_kind
lr.death_kind = lambda *a, **k: "record" if (_dk(*a, **k) is not None) else None
root = tempfile.mkdtemp(prefix="livingyears-st-")
try:
    dist, data = build(root)
    write(os.path.join(dist, "register", "index.html"), page("<p>Barnaby Thistlewood (2005) of Nowhere</p>"))
    rc, *_ = run(dist, data)
    check("a bare death flag read as a record lets that person's year through (the flag fault above would catch it)", rc == 0)
finally:
    shutil.rmtree(root, ignore_errors=True)
    lr.death_kind = _dk
_probe = ly.Finder.scan_text
ly.Finder.scan_text = lambda self, rel, text: []
ok, why = ly.probe(TODAY)
ly.Finder.scan_text = _probe
check("a detector that finds nothing fails the gate's own probe", not ok)

print("\n%s" % ("all behave" if not bad else "%d FAILED" % len(bad)))
sys.exit(1 if bad else 0)
