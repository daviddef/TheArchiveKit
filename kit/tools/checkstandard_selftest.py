#!/usr/bin/env python3
"""Prove checkstandard.py counts what the linking standard says, that each planted fault moves exactly the count it should,
that the ratchet holds, and that it refuses to pass on nothing. Invented fixtures only (kit/data/standard-fixtures/).

    python3 kit/tools/checkstandard_selftest.py              the cases (about 5 seconds)
    python3 kit/tools/checkstandard_selftest.py --mutations  also break the tool 21 ways, one at a time, and require this
                                                             self-test to notice each (about 2 minutes)

Every fault is planted into a copy of the clean fixture site, one at a time, at the <!--END1--> or <!--END2--> marker of
/story/. Each case also has its CONTROL: the same page without the fault counts 0, so the case can fail. The tool runs as a
subprocess (exit codes are part of its contract). Nothing printed names anyone in the fixtures, and the self-test searches
the tool's output for the invented names to prove it prints counts only.
"""
import os, sys, re, json, shutil, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autolink as al
FIX = os.path.join(os.path.dirname(HERE), "data", "standard-fixtures")
INDEX = os.path.join(FIX, "index.json")
LIVING = os.path.join(FIX, "living.json")
CONFIG = os.path.join(FIX, "standard.json")
SITE = os.path.join(FIX, "site")
IDX = json.load(open(INDEX, encoding="utf-8"))
CFG = json.load(open(CONFIG, encoding="utf-8"))
res = []
ALL_OUTPUT = []
RULES = ["L1", "L2", "L3", "L4", "L5", "EX"]


def case(label, ok, detail=""):
    res.append(bool(ok))
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", label, ("  [" + str(detail)[:300] + "]") if detail and not ok else ""))


def tool(name, args):
    env = {k: v for k, v in os.environ.items() if k != "ARCHIVE_OUT"}
    p = subprocess.run([sys.executable, os.path.join(HERE, name)] + args, capture_output=True, text=True, env=env)
    out = p.stdout + p.stderr
    ALL_OUTPUT.append(out)
    return p.returncode, out


def gate(dist, extra=None, config=CONFIG, index=INDEX, living=LIVING, floor=None):
    a = ["--dist", dist, "--index", index, "--config", config, "--floor", floor or os.path.join(os.path.dirname(dist), "floor.json"), "--table"]
    if living:
        a += ["--living", living]
    return tool("checkstandard.py", a + (extra or []))


def fresh():
    t = tempfile.mkdtemp(prefix="checkstandard-")
    d = os.path.join(t, "dist")
    shutil.copytree(SITE, d)
    return t, d


def page(dist, rel):
    return open(os.path.join(dist, rel, "index.html"), encoding="utf-8", newline="").read()


def put(dist, rel, text):
    d = os.path.join(dist, rel)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="").write(text)


def counts(out):
    """{page url: {rule: n}} from the --table lines."""
    r = {}
    for m in re.finditer(r"^\s+(\S+)\s+L1 (\d+)\s+L2 (\d+)\s+L3 (\d+)\s+L4 (\d+)\s+L5 (\d+)\s+EX (\d+)\s*$", out, re.M):
        r[m.group(1)] = dict(zip(RULES, map(int, m.groups()[1:])))
    return r


BASE = {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5": 0, "EX": 2}


def plant(marker, html, rel="story", cfg=None, index=None, living=LIVING, extra=None):
    """Plant `html` at a marker of /story/ in a fresh copy and return the story page's counts (and the exit code, output)."""
    t, d = fresh()
    s = page(d, rel)
    assert marker in s, marker
    put(d, rel, s.replace(marker, html + marker, 1))
    kw = {}
    if cfg is not None:
        cp = os.path.join(t, "standard.json"); json.dump(cfg, open(cp, "w", encoding="utf-8")); kw["config"] = cp
    if index is not None:
        ip = os.path.join(t, "ix.json"); json.dump(index, open(ip, "w", encoding="utf-8")); kw["index"] = ip
    c, out = gate(d, extra, living=living, **kw)
    shutil.rmtree(t, ignore_errors=True)
    return counts(out).get("/" + rel + "/"), c, out


def moves(label, marker, html, want, **kw):
    """The planted fault moves exactly the counts in `want` (rule: delta) and nothing else."""
    got, c, out = plant(marker, html, **kw)
    exp = dict(BASE)
    for k, v in want.items():
        exp[k] += v
    case(label, got == exp, "got %s want %s" % (got, exp))


# ------------------------------------------------------------------------------------------------ the clean fixture
print("the clean fixture")
t, d = fresh(); fl = os.path.join(t, "floor.json")
c, out = gate(d)
cn = counts(out)
case("the clean site passes with no floor: exit 0, ok", c == 0 and "checkstandard: ok." in out, out)
case("/story/ meets the standard exactly: L1..L5 are 0 and EX is 2 (two deliberate exemptions)", cn.get("/story/") == BASE, cn)
case("/notes/ is clean too", cn.get("/notes/") == {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5": 0, "EX": 0}, cn)
case("/other/ breaks every rule but is not in the config's scope, so it is not examined; a person page and /who/ are never in scope",
     set(cn) == {"/story/", "/notes/"}, cn)
case("a page with no <main> and the entry pages are not counted (and not listed)", "/404.html" not in cn and not any(k.startswith(("/people/", "/who/")) for k in cn))
case("it says what it examined: passages that cite a record, how many are linked, how many scan keys are held",
     "4 passages cite a record (3 linked, 1 exempt)" in out and "5 scan keys held" in out, out)
c2, out2 = gate(d, ["--write-floor"])
fj = json.load(open(fl))
case("--write-floor starts every page at its current count, per rule", c2 == 0 and fj["pages"]["/story/"] == BASE and set(fj["pages"]) == {"/story/", "/notes/"}, fj)
case("the floor holds numbers only: no name, no address of a person", not any(n.lower() in open(fl).read().lower() for n in ("orsolo", "venti", "marta", "elio", "tamsin", "people", "who")), open(fl).read())
c3, out3 = gate(d)
case("the same build passes against its own floor", c3 == 0, out3)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ L1
print("L1: a name the index resolves, with no link in its section")
moves("L1: a person linked in part one but written plain in part two is unlinked in part two", "<!--END2-->",
      "<p>In the end Marta Arena came back.</p>", {"L1": 1})
moves("L1: the register-order alias counts (Venti Orsolo), and the longest name wins", "<!--END2-->",
      "<p>Venti Orsolo wrote it down.</p>", {"L1": 1})
moves("L1: the same unlinked name twice in one section is one missing link", "<!--END2-->",
      "<p>Marta Arena came, and Marta Arena left.</p>", {"L1": 1})
moves("L1: a name inside a data-no-autolink region is not counted (the author's exception)", "<!--END2-->",
      "<div data-no-autolink><p>Marta Arena.</p></div>", {})
moves("L1 control: the same name, linked, counts 0", "<!--END2-->",
      '<p><a href="/people/marta-arena/" data-autolink>Marta Arena</a> again.</p>', {})
moves("L1: a bold unlinked name that HAS an entry is L1, not L2", "<!--END2-->",
      "<p><strong>Tamsin Brightwell</strong> is the same person in part two.</p>", {"L1": 1})
t, d = fresh()
put(d, "story", page(d, "story").replace("<!--END2-->", "<p>Marta Arena. Orsolo Venti. Tamsin Brightwell. Elio Marn. Venti Orsolo.</p><!--END2-->", 1))
put(d, "notes", page(d, "notes").replace("</main>", "<h2>Two</h2><p>Elio Marn and Marta Arena.</p></main>"))
c, out = gate(d)
cn = counts(out)
mini = os.path.join(t, "mini")                     # only the two pages in scope, so checklinks reads the same pages
for rel in ("story", "notes"):
    os.makedirs(os.path.join(mini, rel)); shutil.copy(os.path.join(d, rel, "index.html"), os.path.join(mini, rel, "index.html"))
c2, out2 = tool("checklinks.py", ["--dist", mini, "--index", INDEX, "--living", LIVING, "--floor", os.path.join(t, "none.json")])
case("L1 is checklinks.py's own number on the same pages (5 here): the two gates cannot disagree",
     cn["/story/"]["L1"] == 3 and cn["/notes/"]["L1"] == 2 and "5 resolvable names unlinked in their section on 2 pages" in out2, (cn, out2))
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ L2
print("L2: a person the archive names from a record, with no entry")
moves("L2: a capitalised name-like phrase in bold that matches no entry moves L2 by 1", "<!--END2-->",
      "<p>Signed by <strong>Marta Quill</strong> in the end.</p>", {"L2": 1})
moves("L2: the same phrase twice is counted once per page (the fix is one entry)", "<!--END2-->",
      "<p>Signed by <strong>Marta Quill</strong>; then <strong>Marta Quill</strong>.</p>", {"L2": 1})
moves("L2: a name in a record-reading block (.rec) counts without bold", "<!--END2-->",
      '<div class="rec"><div class="v">The witness was Elio Quill, a carter.</div></div>', {"L2": 1})
moves("L2 control: the same phrase in plain prose is L5 (a form for the author to write in full), not L2", "<!--END2-->",
      "<p>Signed by Marta Quill in the end.</p>", {"L5": 1})
moves("L2: a phrase with an entry (a /who/ name) is not counted: the entry is what L2 asks for", "<!--END2-->",
      '<p>Signed by <strong><a href="/who/tamsin-brightwell/">Tamsin Brightwell</a></strong>.</p>', {})
moves("L2: the register-order alias has an entry too", "<!--END2-->",
      '<div class="rec"><div class="v"><strong><a href="/people/marta-arena/">Arena Marta</a></strong></div></div>', {})
moves("L2: a phrase with no capitalised given name in it is not a person-like phrase (the archive's own names are the vocabulary)", "<!--END2-->",
      "<p>The <strong>Quill Bureau</strong> opened.</p>", {})
moves("L2: an allow entry (with a reason) hides one, and the hiding is counted: EX +1", "<!--END2-->",
      "<p>The notary <strong>Marta Dorin</strong> again.</p>", {"EX": 1})
moves("L2: data-name-exempt hides a region, and that too is counted in EX", "<!--END2-->",
      '<p data-name-exempt="a quotation from the deed, spelled as the deed spells it">Signed by <strong>Marta Quill</strong>.</p>', {"EX": 1})
moves("L2: the config's not_names pattern (the archive's own) removes a false positive without touching the tool", "<!--END2-->",
      "<p>Signed by <strong>Marta Quill</strong>.</p>", {}, cfg=dict(CFG, names=dict(CFG["names"], not_names=["^Marta Quill$"])))
got, c, out = plant("<!--END2-->", "<p>Signed by <strong>Marta Quill</strong>.</p>",
                    index=dict(IDX, people=IDX["people"] + [{"name": "Marta Quill", "url": "/who/tamsin-brightwell/"}]))
exp = dict(BASE); exp["L1"] += 1
case("L2: a name the index lists is not L2 (an unlinked mention of it is L1, which autolink.py then links)", got == exp, (got, exp))

# ------------------------------------------------------------------------------------------------ L3
print("L3: a passage that quotes a record, with no link to it")
moves("L3: a passage citing an act with no link moves L3 by 1", "<!--END2-->",
      "<p>The register says so in act 12 of 1898.</p>", {"L3": 1})
moves("L3: ... and the other patterns count too (film)", "<!--END2-->", "<p>Read on film 31.</p>", {"L3": 1})
moves("L3 control: a link to /sources/ in the passage satisfies it", "<!--END2-->",
      '<p>The register says so in <a href="/sources/venti-1898/">act 12 of 1898</a>.</p>', {})
moves("L3: so does a link to /documents/ or /searched/ with an anchor", "<!--END2-->",
      '<p>Act 12 of 1898, see <a href="/searched/#venti">the search</a>.</p>', {})
moves("L3: so does an external link to a host the config allows", "<!--END2-->",
      '<p>Act 12 of 1898 is at <a href="https://archive.example.test/ark:/1/2">the archive</a>.</p>', {})
moves("L3: a link to a host the config does not allow does not count", "<!--END2-->",
      '<p>Act 12 of 1898 is at <a href="https://elsewhere.example.org/x">a site</a>.</p>', {"L3": 1})
moves("L3: a link to the archive's other narrative page is not a record link", "<!--END2-->",
      '<p>Act 12 of 1898, as <a href="/notes/">the notes</a> say.</p>', {"L3": 1})
moves("L3: an in-page link to a plate counts only when the plate's id exists on the page", "<!--END2-->",
      '<p>Act 12 of 1898, <a href="#plate-1899-act7">plate</a>.</p>', {})
moves("L3: ...and a dead in-page anchor does not", "<!--END2-->",
      '<p>Act 12 of 1898, <a href="#plate-nowhere">plate</a>.</p>', {"L3": 1})
moves("L3: the NEXT block counts when it is a short apparatus line with a record link", "<!--END2-->",
      '<p>Act 12 of 1898 says so.</p><p>Source: <a href="/sources/venti-1898/">the volume</a>.</p>', {})
moves("L3: ...but not when that next block is long prose that happens to link", "<!--END2-->",
      '<p>Act 12 of 1898 says so.</p><p>' + "Long prose about something else entirely, which goes on and on past the limit of what a source line is. " * 3
      + '<a href="/sources/venti-1898/">link</a></p>', {"L3": 1})
moves("L3: ...and not when the link is two blocks away", "<!--END2-->",
      '<p>Act 12 of 1898 says so.</p><p>Nothing.</p><p>Source: <a href="/sources/venti-1898/">the volume</a>.</p>', {"L3": 1})
moves("L3: a component's own mark (data-cite on a link) counts as a record link", "<!--END2-->",
      '<p>Act 12 of 1898 <a href="/anything/" data-cite>cite</a>.</p>', {})
moves("L3: data-cite-exempt with a reason hides the passage, counted in EX", "<!--END2-->",
      '<p data-cite-exempt="the sentence restates the one above, which carries the link">Act 12 of 1898 again.</p>', {"EX": 1})
moves("L3: a passage in a block the config does not name (a table cell) is not a passage", "<!--END2-->",
      "<table><tr><td>act 12 of 1898</td></tr></table>", {})
moves("L3: only the config's patterns find a citation; prose that merely sounds like one is not counted", "<!--END2-->",
      "<p>The register has an entry for the year 1898.</p>", {})

# ------------------------------------------------------------------------------------------------ L4
print("L4: a scan the archive holds, not shown in the section that cites it")
moves("L4: a passage cites a held scan (act 9 of 1901 is on /plates/) with no image in its section: L4 +1, L3 0 (it is linked)", "<!--END2-->",
      '<p>Act 9 of 1901 is <a href="/sources/x/">quoted here</a>.</p>', {"L4": 1})
moves("L4 control: the same passage with the image in the same section counts 0", "<!--END2-->",
      '<p>Act 9 of 1901 is <a href="/sources/x/">quoted here</a>.</p><img src="/plates/1901-act9.jpg" alt="">', {})
got, c, out = plant("<!--END1-->", '<p>Act 9 of 1901 is <a href="/sources/x/">quoted here</a>.</p>')
exp = dict(BASE); exp["L4"] += 1
case("L4: ...the scan sits in part two, the passage in part one: L4 +1 (a gallery elsewhere is not 'beside')", got == exp, got)
moves("L4: a citation of an act whose scan is NOT held is L3's business only", "<!--END2-->",
      '<p>Act 4 of 1903 is <a href="/sources/x/">quoted here</a>.</p>', {})
moves("L4: a pattern the config marks link_only is never required to show a scan", "<!--END2-->",
      '<p>The manifest <a href="/sources/x/">says</a>.</p>', {})
moves("L4: the image key ignores the rest of the file name (act 3 of 1902 is held as 1902-act3-detail.jpg)", "<!--END2-->",
      '<p>Act 3 of 1902 is <a href="/sources/x/">quoted here</a>.</p>', {"L4": 1})
moves("L4: a cite-exempt passage is not asked for its scan", "<!--END2-->",
      '<p data-cite-exempt="shown on the plates page by design, and said so there">Act 9 of 1901.</p>', {"EX": 1})
# the held set can also come from the archive's own list
t, d = fresh(); hk = os.path.join(t, "held.json"); json.dump(["1903-4"], open(hk, "w"))
cfg2 = json.loads(json.dumps(CFG)); cfg2["scans"]["held_keys_file"] = hk
cp = os.path.join(t, "c.json"); json.dump(cfg2, open(cp, "w"))
s = page(d, "story"); put(d, "story", s.replace("<!--END2-->", '<p>Act 4 of 1903 is <a href="/sources/x/">quoted here</a>.</p><!--END2-->', 1))
c, out = gate(d, config=cp)
case("L4: a scan the archive's own list says it holds but has published nowhere is a violation", counts(out)["/story/"]["L4"] == 1, out)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ L5
print("L5: forms the machine cannot resolve")
moves("L5: a bare given name, with no full name containing it earlier in its section, moves L5 by 1", "<!--END2-->",
      "<p>Then Pavel arrived with his cart.</p>", {"L5": 1})
moves("L5: the same bare name twice in one section is one (write it in full once)", "<!--END2-->",
      "<p>Then Pavel arrived. Pavel left.</p>", {"L5": 1})
moves("L5 control: written in full first (an unlinked full name counts for L1, not L5)", "<!--END2-->",
      "<p>Pavel Korda arrived, and Pavel left.</p>", {"L1": 1})
moves("L5 control: a bare name after a linked full name in the same section is fine", "<!--END2-->",
      '<p><a href="/who/tamsin-brightwell/">Tamsin Brightwell</a> came; Tamsin stayed.</p>', {})
moves("L5: ...but the next section starts again (an h2 is a boundary)", "<!--END2-->",
      "<h2>Part three</h2><p>Elio stayed.</p>", {"L5": 1})
moves("L5 control: without the new heading, Elio (written in full above in this section) is fine", "<!--END2-->",
      "<p>Elio stayed.</p>", {})
moves("L1: an h3 is a boundary too, so a name linked above and written plain below it is one missing link", "<!--END2-->",
      "<h3>Aside</h3><p>Elio Marn again.</p>", {"L1": 1})
moves("L5: a surname-first form with no entry (given name first-looking, unresolved) is counted", "<!--END2-->",
      "<p>The groom was Elio Marnetti, they say.</p>", {"L5": 1})
moves("L5: an author's own link around a bare name resolves it (tagged by the author, never guessed)", "<!--END2-->",
      '<p>Then <a href="/who/tamsin-brightwell/">Tamsin</a> arrived.</p>', {})
moves("L5: data-name-exempt (with a reason) hides one and counts it in EX", "<!--END2-->",
      '<p>Then <span data-name-exempt="the deed spells only this name">Pavel</span> arrived.</p>', {"EX": 1})
moves("L5: a name in a heading, a table, code or data-no-autolink is not asked for", "<!--END2-->",
      "<h3>Pavel</h3><table><tr><td>Pavel</td></tr></table><code>Pavel</code><div data-no-autolink>Pavel</div>", {})
moves("L5: a word that is not a given name in the archive's index is not a name (the vocabulary is the archive's)", "<!--END2-->",
      "<p>Then Casimir arrived.</p>", {})
moves("L5: the config can add given names the index does not hold", "<!--END2-->",
      "<p>Then Casimir arrived.</p>", {"L5": 1}, cfg=dict(CFG, names=dict(CFG["names"], given_names=["Casimir"])))
moves("L5: the config can mark a word as a surname, so it is never taken for a bare given name", "<!--END2-->",
      "<p>Then Pavel arrived.</p>", {}, cfg=dict(CFG, names=dict(CFG["names"], surname_words=["Pavel"])))
moves("L5: a function word at the start of a sentence is not a name (Then Pavel is Pavel)", "<!--END2-->",
      "<p>Then Pavel arrived.</p>", {"L5": 1})

# ------------------------------------------------------------------------------------------------ the ratchet
print("the ratchet")
t, d = fresh(); fl = os.path.join(t, "floor.json")
gate(d, ["--write-floor"])
story = page(d, "story")
put(d, "story", story.replace("<!--END2-->", "<p>Act 12 of 1898 says so.</p><!--END2-->", 1))
c, out = gate(d)
case("RATCHET: a page whose L3 rises above its floor fails and names the page and the rule", c == 1 and "rise: /story/ L3 1, floor 0" in out, out)
c, out = gate(d, ["--write-floor"])
case("RATCHET: --write-floor refuses to write while a page has risen", c == 1 and "NOT WRITTEN" in out and json.load(open(fl))["pages"]["/story/"]["L3"] == 0, out)
put(d, "story", story.replace("<!--END2-->", "<p data-cite-exempt=\"restated above\">Act 12 of 1898 says so.</p><!--END2-->", 1))
c, out = gate(d)
case("RATCHET: an exemption is ratcheted too: EX rising from 2 to 3 fails", c == 1 and "rise: /story/ EX 3, floor 2" in out, out)
put(d, "story", story.replace("<!--END2-->", "<p>Then Pavel arrived.</p><!--END2-->", 1))
c, out = gate(d)
case("RATCHET: L5 rising fails", c == 1 and "L5 1, floor 0" in out, out)
put(d, "story", story)
# a fall: lower the floor's tolerance by planting a fault first, writing the floor, then fixing
put(d, "story", story.replace("<!--END2-->", "<p>Act 12 of 1898 says so.</p><p>Then Pavel arrived.</p><!--END2-->", 1))
fl2 = os.path.join(t, "floor2.json")
c, out = gate(d, ["--write-floor"], floor=fl2)
case("a page with faults can enter the floor at its current count (how an archive starts)",
     c == 0 and json.load(open(fl2))["pages"]["/story/"]["L3"] == 1 and json.load(open(fl2))["pages"]["/story/"]["L5"] == 1, out)
c, out = gate(d, floor=fl2)
case("...and then passes against it", c == 0, out)
put(d, "story", story)
c, out = gate(d, floor=fl2)
case("RATCHET: counts that fell pass, and the summary says the floor can be lowered", c == 0 and "below their floor" in out, out)
c, out = gate(d, ["--write-floor"], floor=fl2)
j = json.load(open(fl2))["pages"]["/story/"]
case("--write-floor locks the gain in", c == 0 and j["L3"] == 0 and j["L5"] == 0, j)
put(d, "story", story.replace("<!--END2-->", "<p>Act 12 of 1898 says so.</p><!--END2-->", 1))
c, out = gate(d, floor=fl2)
case("RATCHET: after locking, the old fault is a rise again (a floor never goes up by itself)", c == 1 and "rise: /story/ L3" in out, out)
put(d, "story", story)
# a new page
newp = "<!doctype html><html><body><main><h2>a</h2><p>Act 1 of 1890 x.</p><p>Act 2 of 1890 x.</p><p>Act 3 of 1890 x.</p></main></body></html>"
cfgn = json.loads(json.dumps(CFG)); cfgn["include"] = ["/story/", "/notes/", "/fresh/"]
cpn = os.path.join(t, "cn.json"); json.dump(cfgn, open(cpn, "w"))
put(d, "fresh", newp)
c, out = gate(d, config=cpn, floor=fl)
case("NEW PAGE: a page not in the floor with 3 faults in a rule (the default maximum) passes", c == 0, out)
put(d, "fresh", newp.replace("</main>", "<p>Act 4 of 1890 x.</p></main>"))
c, out = gate(d, config=cpn, floor=fl)
case("NEW PAGE: a page not in the floor with 4 fails, and names the rule", c == 1 and "new: /fresh/ a page not in the floor: L3 4" in out, out)
c, out = gate(d, ["--new-page-max", "4"], config=cpn, floor=fl)
case("NEW PAGE: the maximum is configurable on the command line", c == 0, out)
cfgn["new_page_max"] = 4; json.dump(cfgn, open(cpn, "w"))
c, out = gate(d, config=cpn, floor=fl)
case("NEW PAGE: ...and in the config", c == 0, out)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ structural failures
print("structural failures")
got, c, out = plant("<!--END2-->", '<p data-cite-exempt="">Act 12 of 1898 says so.</p>')
case("an exemption with no reason fails, whatever the floor (exit 1)", c == 1 and "with no reason" in out, out)
got, c, out = plant("<!--END2-->", '<p data-name-exempt>Signed by <strong>Marta Quill</strong>.</p>')
case("...and so does a data-name-exempt with no reason", c == 1 and "with no reason" in out, out)
bad = json.loads(json.dumps(IDX)); bad["people"].append({"name": "Quill Venti", "url": "/who/nobody-here/"})
got, c, out = plant("<!--END2-->", "", index=bad)
case("an index address that is not a built page fails: a name linked to nowhere is the dead end L2 exists to prevent",
     c == 1 and "dead: (index) 1 index address is not a built page" in out and "nobody" not in out, out)
t, d = fresh()
s = page(d, "story")
put(d, "story", s.replace("<!--END2-->", '<p><a href="/people/gone-person/" data-autolink>Orsolo Venti</a></p><!--END2-->', 1))
c, out = gate(d)
case("checklinks' own stale-link check runs in-scope: a data-autolink link to an address not in the index fails", c == 1 and "stale" in out and "gone-person" not in out, out)
put(d, "story", s.replace("<!--END2-->", '<p><a href="/people/livia-vance/" data-autolink>Someone Else</a></p><!--END2-->', 1))
c, out = gate(d)
case("...and a data-autolink link to a living address fails, without printing it", c == 1 and "living" in out and "livia" not in out.lower(), out)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ refusals
print("refusals: a check that examined nothing has not passed")
def refuse(label, mutate_cfg=None, mutate_dist=None, index=INDEX, living=LIVING, want="REFUSED", extra=None, raw_cfg=None):
    t, d = fresh()
    cfg = json.loads(json.dumps(CFG))
    if mutate_cfg:
        mutate_cfg(cfg)
    cp = os.path.join(t, "c.json")
    if raw_cfg is not None:
        open(cp, "w").write(raw_cfg)
    else:
        json.dump(cfg, open(cp, "w"))
    if mutate_dist:
        mutate_dist(d)
    c, out = gate(d, extra, config=cp, index=index, living=living)
    shutil.rmtree(t, ignore_errors=True)
    case("%s -> exit 2" % label, c == 2 and want in out, out)

refuse("an empty config {}", raw_cfg="{}", want="empty")
refuse("a config that is not JSON", raw_cfg="{nope", want="cannot be read")
refuse("a config with no 'include'", lambda c: c.pop("include"), want="include")
refuse("a config with no citation patterns", lambda c: c["citations"].update(patterns=[]), want="citations.patterns")
refuse("a config with no record-link rule", lambda c: c["citations"].pop("record_links"), want="record_links")
refuse("a config with no scans decision", lambda c: c.pop("scans"), want="scans")
refuse("a config that holds no scans must say why: scans.none needs a reason", lambda c: c.update(scans={"none": "x"}), want="reason")
refuse("an allow entry with no reason", lambda c: c["names"]["allow"].append({"phrase": "Marta Zed"}), want="reason")
refuse("a regular expression that does not compile", lambda c: c["citations"]["patterns"].append({"id": "bad", "regex": "(["}), want="regular expression")
refuse("a selector the gate does not read", lambda c: c["names"].update(read_blocks=["div > p"]), want="selector")
refuse("an include pattern that matches no built page (a mistyped page would escape)", lambda c: c["include"].append("/nope/"), want="matched no built page")
refuse("an empty build", mutate_dist=lambda d: shutil.rmtree(d) or os.makedirs(d), want="nothing was examined")
refuse("pages without the scope element", lambda c: c.update(scope="article"), want="wrong scope")
refuse("a build where no passage cites a record: the patterns found nothing, so nothing was examined",
       lambda c: c["citations"].update(patterns=[{"id": "x", "regex": "zzzzqqq", "key": "k"}]), want="matches a citation pattern")
refuse("an allow entry for a living person, without printing it", lambda c: c["names"]["allow"].append({"phrase": "Livia Vance", "reason": "mistaken for a notary"}), want="LIVING")
bad = json.loads(json.dumps(IDX)); bad["people"].append({"name": "Livia Vance", "url": "/people/lv2/"})
t, d = fresh(); ip = os.path.join(t, "ix.json"); json.dump(bad, open(ip, "w"))
c, out = gate(d, index=ip)
case("an index the living list also holds -> exit 2, a count, no name", c == 2 and "LIVING: 1 index entry" in out and "Livia" not in out and "Vance" not in out, out)
json.dump({"people": [], "ambiguous": []}, open(ip, "w"))
c, out = gate(d, index=ip)
case("an empty index -> exit 2", c == 2 and "empty" in out, out)
c, out = gate(d, living=os.path.join(t, "nope.json"))
case("an unreadable living list -> exit 2", c == 2 and "living list" in out, out)
open(os.path.join(t, "f.json"), "w").write("{not json")
c, out = gate(d, floor=os.path.join(t, "f.json"))
case("a corrupt floor file -> exit 2", c == 2 and "floor" in out, out)
json.dump({"pages": {"/story/": {"L9": 1}}}, open(os.path.join(t, "f.json"), "w"))
c, out = gate(d, floor=os.path.join(t, "f.json"))
case("a floor that names a rule that does not exist -> exit 2", c == 2, out)
c, out = gate(os.path.join(t, "missing"))
case("a build directory that does not exist -> exit 2", c == 2, out)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ the config belongs to the archive
print("the config is the archive's, the tool is not loosened")
moves("a stop word the archive adds removes a false positive", "<!--END2-->",
      "<p>Signed by Witnesses Marta Quill.</p>", {}, cfg=dict(CFG, names=dict(CFG["names"], stop_words=["Witnesses"], not_names=["Quill"])))
moves("...without the stop word the run includes it (the tool itself is unchanged)", "<!--END2-->",
      "<p>Signed by Witnesses Marta Quill.</p>", {"L5": 1})
t, d = fresh()
cfgw = dict(CFG, include=["/*"], exclude=["/plates/", "/other/", "/404.html"])
cp = os.path.join(t, "c.json"); json.dump(cfgw, open(cp, "w"))
c, out = gate(d, config=cp)
cn = counts(out)
case("include may be a pattern: /* takes every narrative page but never an entry page (/people/ and /who/ are names)",
     c == 0 and set(cn) == {"/story/", "/notes/"}, (c, cn))
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ the second round (18 Oct 2026)
print("standard 2: keys folded, plates keyed from the archive's data, quotations, single words, never_complete, tables")


def scenario(story="", cfg=None, pages=None, files=None, index=None, living=LIVING, extra=None, marker="<!--END2-->", cfg_fn=None):
    """A fresh copy of the fixture with `story` planted at `marker`, the config changed by `cfg_fn(cfg, tmpdir)`, other pages
    set by `pages` ({rel: html or fn(old)}) and extra files written into the temp dir by `files` ({name: json-able}).
    Returns (the /story/ counts, exit code, output)."""
    t, d = fresh()
    if story:
        s0 = page(d, "story")
        put(d, "story", s0.replace(marker, story + marker, 1))
    for rel, h in (pages or {}).items():
        old = page(d, rel) if os.path.exists(os.path.join(d, rel, "index.html")) else ""
        put(d, rel, h(old) if callable(h) else h)
    for name, data in (files or {}).items():
        json.dump(data, open(os.path.join(t, name), "w", encoding="utf-8"))
    c = json.loads(json.dumps(CFG if cfg is None else cfg))
    if cfg_fn:
        cfg_fn(c, t)
    cp = os.path.join(t, "standard.json")
    json.dump(c, open(cp, "w", encoding="utf-8"))
    kw = {}
    if index is not None:
        ip = os.path.join(t, "ix.json"); json.dump(index, open(ip, "w", encoding="utf-8")); kw["index"] = ip
    if isinstance(living, dict):
        lp = os.path.join(t, "lv.json"); json.dump(living, open(lp, "w", encoding="utf-8")); living = lp
    code, out = gate(d, extra, config=cp, living=living, **kw)
    shutil.rmtree(t, ignore_errors=True)
    return counts(out).get("/story/"), code, out


def delta(label, got, want):
    exp = dict(BASE)
    for k, v in want.items():
        exp[k] += v
    case(label, got == exp, "got %s want %s" % (got, exp))


PLATES_PLUS = lambda old: old.replace("</main>", '<figure><img src="/plates/orchard-deed.jpg" alt="f"></figure>\n<figure><img src="/plates/deed-a.jpg" alt="g"></figure>\n<figure><img src="/plates/orchard.jpg" alt="h"></figure>\n</main>')


def lit_cfg(c, t):
    c["citations"]["patterns"].append({"id": "deed", "flags": "i", "regex": "\\bthe Orchard deed\\b", "key": "Orchard-Deed"})
    c["scans"]["image_patterns"].append({"regex": "/plates/(?P<s>[a-z]+-deed)\\.", "key": "{s}"})


# 1. keys and aliases fold the way text folds
print("1. keys and aliases are folded; a configured key that matches nothing is counted and can fail the gate")
got, code, out = scenario('<p>The Orchard deed <a href="/sources/x/">says so</a>.</p>', pages={"plates": PLATES_PLUS}, cfg_fn=lit_cfg)
delta("1: a literal key written 'Orchard-Deed' meets the plate 'orchard-deed' (case and hyphen folded): L4 +1", got, {"L4": 1})
got, code, out = scenario('<p>The Orchard deed <a href="/sources/x/">says so</a>.</p><img src="/plates/orchard-deed.jpg" alt="">',
                          pages={"plates": PLATES_PLUS}, cfg_fn=lit_cfg)
delta("1 control: with the plate in the same section the same passage counts 0", got, {})
got, code, out = scenario("", cfg_fn=lambda c, t: c["scans"].update(aliases={"zzz unseen": "1900-5"}))
case("1: an alias that matches no citation and no plate is a count-only warning, not a failure",
     code == 0 and "warning: 1 configured scan keys matched no citing passage and no held plate" in out and "zzz" not in out, out)
got, code, out = scenario("", cfg_fn=lambda c, t: c["scans"].update(aliases={"zzz unseen": "1900-5"}), extra=["--strict-config"])
case("1: ... and --strict-config makes it a failure (exit 1), still without the key", code == 1 and "config: 1 configured scan keys matched" in out and "zzz" not in out, out)
got, code, out = scenario("", cfg_fn=lambda c, t: c["scans"].update(aliases={"1902": "1902"}), extra=["--strict-config"])
case("1 control: an alias the run did apply (a year some citation and plate carry) is not a warning; strict passes", code == 0 and "warning" not in out, out)
got, code, out = scenario("", cfg_fn=lambda c, t: c["scans"].update(aliases={"ZZZ  Unseen": "x"}), extra=["--strict-config"])
case("1: the alias key is folded like text (case, double space) before it is compared", code == 1, out)
got, code, out = scenario("", cfg_fn=lambda c, t: c["citations"]["patterns"].append({"id": "ghost", "regex": "zzzzqqq", "key": "ghost-1"}), extra=["--strict-config"])
case("1: a literal pattern key whose pattern hits nothing and whose plate is held nowhere is counted", code == 1 and "1 configured scan keys" in out, out)
got, code, out = scenario("", extra=["--strict-config"])
case("1 control: the clean fixture has nothing unmatched; --strict-config passes", code == 0 and "warning" not in out, out)
t, d = fresh()
cfgz = json.loads(json.dumps(CFG)); cfgz["scans"]["aliases"] = {"zzz": "x"}
json.dump(cfgz, open(os.path.join(t, "cz.json"), "w"))
c1, out1 = gate(d, ["--write-floor", "--strict-config"], config=os.path.join(t, "cz.json"))
case("1: --write-floor refuses while --strict-config has a problem", c1 == 1 and "NOT WRITTEN" in out1 and not os.path.exists(os.path.join(t, "floor.json")), out1)
shutil.rmtree(t, ignore_errors=True)

# 2. plates whose file names carry no locator
print("2. plates keyed from the archive's own data (aliases_file, manifest)")
CITE_A = '<p>Act 11 of 1904 is <a href="/sources/x/">quoted here</a>.</p>'


def aliases_cfg(c, t):
    c["scans"]["aliases_file"] = "aliases.json"


files_a = {"aliases.json": {"deed-a": ["1904-11"]}}
got, code, out = scenario(CITE_A, pages={"plates": PLATES_PLUS}, files=files_a, cfg_fn=aliases_cfg)
delta("2: a plate named 'deed-a.jpg' is keyed 1904-11 by the archive's aliases file: held but not in the passage's section, L4 +1", got, {"L4": 1})
got, code, out = scenario(CITE_A + '<img src="/plates/deed-a.jpg" alt="">', pages={"plates": PLATES_PLUS}, files=files_a, cfg_fn=aliases_cfg)
delta("2 control: the plate in the section counts 0", got, {})
got, code, out = scenario(CITE_A, pages={"plates": PLATES_PLUS})
delta("2 control: without the aliases file nothing keys that plate, so L4 stays 0", got, {})
got, code, out = scenario(CITE_A, pages={"plates": PLATES_PLUS}, files={"aliases.json": {"deed-a.jpg": "1904 11"}}, cfg_fn=aliases_cfg)
delta("2: the plate id may carry its extension and the keys may be a single string (any spelling that folds alike)", got, {"L4": 1})
got, code, out = scenario(CITE_A, pages={"plates": PLATES_PLUS}, files={"aliases.json": {"deed-a": ["1904-11"], "ghost-plate": ["1990-1"]}},
                          cfg_fn=aliases_cfg, extra=["--strict-config"])
case("2: a plate id in the file that no image carries and no citation reaches is counted as unmatched", code == 1 and "1 configured scan keys" in out, out)


def manifest_cfg(c, t):
    c["scans"]["manifest"] = {"file": "plates.json", "id_field": "plate", "key_field": "cites"}


files_m = {"plates.json": [{"plate": "deed-a.jpg", "cites": ["1904-11"], "title": "x"}, {"plate": "orchard.jpg", "cites": None}]}
got, code, out = scenario(CITE_A, pages={"plates": PLATES_PLUS}, files=files_m, cfg_fn=manifest_cfg)
delta("2: a plates manifest (id_field, key_field) keys the same plate; a manifest row with no key is ignored", got, {"L4": 1})
got, code, out = scenario(CITE_A, pages={"plates": PLATES_PLUS}, files=files_m, cfg_fn=lambda c, t: c["scans"].update(manifest={"file": "plates.json", "id_field": "plate"}))
case("2: a manifest without a key_field is refused", code == 2 and "scans.manifest" in out, out)
got, code, out = scenario(CITE_A, files={"aliases.json": ["not", "an", "object"]}, cfg_fn=aliases_cfg)
case("2: an aliases file that is not an object is refused", code == 2 and "aliases_file" in out, out)
got, code, out = scenario(CITE_A, cfg_fn=lambda c, t: c["scans"].update(aliases_file="missing.json"))
case("2: an aliases file that cannot be read is refused", code == 2 and "aliases_file" in out, out)

# 3. quotations
print("3. names.skip_quotes: names inside a quoted transcription are not the archive's claims")


def sq(c, t, sel=None, pairs=None):
    c["names"]["skip_quotes"] = True
    if sel:
        c["names"]["skip_selectors"] = sel
    if pairs:
        c["names"]["quote_pairs"] = pairs


QREC = '<div class="rec"><div class="v">The witness was «Elio Quill, a carter», they say.</div></div>'
got, code, out = scenario(QREC)
delta("3 control: a name inside « » in a record-reading row is counted as L2 when quotations are not skipped", got, {"L2": 1})
got, code, out = scenario(QREC, cfg_fn=sq)
delta("3: ... and not counted with names.skip_quotes", got, {})
got, code, out = scenario('<p>He wrote «Elio Quill and <strong>Marta Quill</strong>» here.</p>', cfg_fn=sq)
delta("3: bold inside « » is skipped too", got, {})
got, code, out = scenario('<p>He wrote «<em>Elio Quill</em> and <strong>Marta Quill</strong>» and Pavel went.</p>', cfg_fn=sq)
delta("3: a quotation that runs through inline elements is skipped whole, and the text after it is read again (Pavel is L5)", got, {"L5": 1})
got, code, out = scenario('<p>«Elio Quill» then <strong>Marta Quill</strong>.</p>', cfg_fn=sq)
delta("3: the text outside the marks still counts (Marta Quill in bold: L2 +1)", got, {"L2": 1})
got, code, out = scenario('<p>An «unclosed quote <strong>Elio Quill</strong></p><p>Signed by <strong>Marta Quill</strong>.</p>', cfg_fn=sq)
delta("3: an unclosed mark does not swallow the next block", got, {"L2": 1})
got, code, out = scenario('<blockquote>Signed by <strong>Marta Quill</strong> and Pavel.</blockquote>')
delta("3 control: a blockquote is read like any prose", got, {"L2": 1, "L5": 1})
got, code, out = scenario('<blockquote>Signed by <strong>Marta Quill</strong> and Pavel.</blockquote>', cfg_fn=sq)
delta("3: <blockquote> is a quotation under skip_quotes", got, {})
got, code, out = scenario('<p>Signed by <q><strong>Marta Quill</strong> and Pavel</q>.</p>', cfg_fn=sq)
delta("3: so is <q>", got, {})
got, code, out = scenario('<div class="xlat">Signed by <strong>Marta Quill</strong>.</div>', cfg_fn=lambda c, t: sq(c, t, [".xlat"]))
delta("3: and an element the config names (names.skip_selectors, here a class)", got, {})
got, code, out = scenario('<div class="xlat">Signed by <strong>Marta Quill</strong>.</div>', cfg_fn=sq)
delta("3 control: the class is read when the config does not name it", got, {"L2": 1})
got, code, out = scenario('<p>Signed by [<strong>Marta Quill</strong>] and Pavel.</p>', cfg_fn=lambda c, t: sq(c, t, pairs=[["[", "]"]]))
delta("3: the pairs are the config's (square brackets here); the text outside is still read", got, {"L5": 1})
got, code, out = scenario("", cfg_fn=lambda c, t: c["names"].update(skip_selectors=[".xlat"]))
case("3: skip_selectors without skip_quotes is refused (it would do nothing)", code == 2 and "skip_quotes" in out, out)

# 4. allow takes single words
print("4. names.allow takes a bare name; a living name is still refused")
allow1 = lambda c, t: c["names"]["allow"].append({"phrase": "Pavel", "reason": "the deed gives only this given name"})
got, code, out = scenario("<p>Then Pavel arrived.</p>", cfg_fn=allow1)
delta("4: an allowed bare given name is no L5; it is counted in EX instead", got, {"EX": 1})
got, code, out = scenario("<p>Then Pavel arrived.</p><h2>Later</h2><p>Pavel again.</p>", cfg_fn=allow1)
delta("4: ... once per section, like any exemption", got, {"EX": 2})
got, code, out = scenario("<p>Then Pavel Korda arrived, then Pavel.</p>", cfg_fn=allow1)
delta("4: the allowed word does not hide a full name (Pavel Korda is an unlinked index name: L1 +1)", got, {"L1": 1})
bare_living = {"living": [{"name": "Livia Vance", "aliases": ["Vance Livia"], "url": "/people/livia-vance/"}, "Pavel"]}
got, code, out = scenario("", cfg_fn=allow1, living=bare_living)
case("4: an allow entry for a name the living list holds is still refused (exit 2, no name)", code == 2 and "LIVING: 1 allow entry" in out and "Pavel" not in out, out)
got, code, out = scenario("", cfg_fn=lambda c, t: c["names"]["allow"].append({"phrase": "Pavel"}))
case("4: a single-word entry needs its reason too", code == 2 and "reason" in out, out)

# 5. a keyed pattern can be a scan key only
print("5. citations.patterns[].scan_only: a key for L4 that is not itself a citation for L3")


def orch(so):
    def f(c, t):
        c["citations"]["patterns"].append(dict({"id": "orch", "flags": "i", "regex": "\\bthe Orchard\\b", "key": "orchard"}, **({"scan_only": True} if so else {})))
        c["scans"]["image_patterns"].append({"regex": "/plates/(?P<s>orchard)\\.", "key": "{s}"})
    return f


t0 = {"plates": PLATES_PLUS}
got, code, out = scenario("<p>The Orchard stood there.</p>", cfg_fn=orch(False), pages=t0)
delta("5 control: a keyed pattern is also a citation: no link, L3 +1 (and L4 +1, the plate is held elsewhere)", got, {"L3": 1, "L4": 1})
got, code, out = scenario("<p>The Orchard stood there.</p>", cfg_fn=orch(True), pages=t0)
delta("5: marked scan_only, it is a scan key and not a citation: L3 stays 0, L4 +1 (the held plate is not in its section)", got, {"L4": 1})
got, code, out = scenario('<p>The Orchard stood there.</p><img src="/plates/orchard.jpg" alt="">', cfg_fn=orch(True), pages=t0)
delta("5: ... with the plate in the section, 0", got, {})
got, code, out = scenario('<p data-cite-exempt="the plate is on the plates page by design">The Orchard stood there.</p>', cfg_fn=orch(True), pages=t0)
delta("5: an exempt passage that would have owed a scan is counted in EX", got, {"EX": 1})
got, code, out = scenario('<p data-cite-exempt="restates the paragraph above, which carries the link">The Orchard stood there.</p>', cfg_fn=orch(True))
delta("5: ... and one that owes nothing is not", got, {})
got, code, out = scenario("", cfg_fn=lambda c, t: c["citations"]["patterns"].append({"id": "orch", "regex": "x", "scan_only": True}))
case("5: scan_only without a key is refused", code == 2 and "scan_only" in out, out)

# 6. never_complete
print("6. names.never_complete: bare names that may never be written in full")
nc = lambda c, t: (c["names"].update(given_names=["Casimir"]), c["names"].update(never_complete=[{"name": "Casimir", "reason": "a living subject whose full name is not shown"}]))
got, code, out = scenario("<p>Then Casimir arrived.</p>", cfg_fn=lambda c, t: c["names"].update(given_names=["Casimir"]))
delta("6 control: the bare given name would be L5", got, {"L5": 1})
got, code, out = scenario("<p>Then Casimir arrived.</p>", cfg_fn=nc)
delta("6: never_complete counts it in EX, not in L5", got, {"EX": 1})
case("6: the run says how many mentions it holds, as a count, and not the name",
     "1 bare name mention held by names.never_complete" in out and "asimir" not in out, out)
got, code, out = scenario("<p>Then Casimir arrived.</p><h2>Later</h2><p>Casimir again.</p>", cfg_fn=nc)
delta("6: ... once per section", got, {"EX": 2})
got, code, out = scenario("<p>Then Casimir arrived.</p>", cfg_fn=nc, living={"living": ["Casimir", {"name": "Livia Vance", "url": "/people/livia-vance/"}]})
delta("6: a living subject's bare name is exactly what it is for: not refused", got, {"EX": 1})
got, code, out = scenario("", cfg_fn=lambda c, t: c["names"].update(never_complete=[{"name": "Elio Marn", "reason": "a name the index lists"}]))
case("6: an entry that is an index name is refused (it would be linkable), without printing it", code == 2 and "never_complete" in out and "Elio" not in out, out)
got, code, out = scenario("", cfg_fn=lambda c, t: c["names"].update(never_complete=[{"name": "Casimir", "reason": "no"}]))
case("6: an entry needs a reason of 8 characters", code == 2 and "never_complete" in out, out)

# 7. allow_prefixes and the exemptions
print("7. allow_prefixes from the config; exemptions counted, and refused without a reason")
FOUND = {"people": IDX["people"] + [{"name": "Zed Marn", "url": "/found/zed-marn/"}], "ambiguous": IDX["ambiguous"]}
found_page = {"found/zed-marn": "<!doctype html><html><body><main><h1>x</h1><p>y</p></main></body></html>"}
got, code, out = scenario("", index=FOUND, pages=found_page)
case("7 control: an index address outside the prefixes the run knows is refused", code == 2 and "outside the public prefixes" in out, out)
got, code, out = scenario("", index=FOUND, pages=found_page, cfg_fn=lambda c, t: c.update(allow_prefixes=["/people/", "/who/", "/found/"]))
case("7: allow_prefixes in the config makes it a CI call of just --config", code == 0 and "ok." in out, out)
got, code, out = scenario("", index=FOUND, pages=found_page, extra=["--allow-prefix", "/people/", "--allow-prefix", "/who/"],
                          cfg_fn=lambda c, t: c.update(allow_prefixes=["/found/"]))
case("7: ... and it adds to the command line's (repeatable) prefixes", code == 0, out)
got, code, out = scenario("", cfg_fn=lambda c, t: c.update(allow_prefixes=["found"]))
case("7: a prefix that is not root-relative is refused", code == 2 and "allow_prefixes" in out, out)
got, code, out = scenario('<p data-name-exempt="  ">Signed by <strong>Marta Quill</strong>.</p>')
case("7: a data-name-exempt with a blank reason fails (exit 1)", code == 1 and "with no reason" in out, out)
got, code, out = scenario('<p data-cite-exempt="   ">Act 12 of 1898 says so.</p>')
case("7: a data-cite-exempt with a blank reason fails (exit 1)", code == 1 and "with no reason" in out, out)
got, code, out = scenario('<p data-cite-exempt="restates the sentence above">Act 12 of 1898 says so.</p><p data-name-exempt="the deed spells it so">Signed by <strong>Marta Quill</strong>.</p>')
delta("7: a data-cite-exempt and a data-name-exempt with reasons are both counted in EX", got, {"EX": 2})

# 8. tables
print("8. tables: narrative | records | skip")
TAB = "<table><tr><td>Then Pavel read act 12 of 1898.</td></tr></table>"
tb = lambda mode, blocks=None: (lambda c, t: (c.update(tables=mode), blocks and c["citations"].update(blocks=blocks)))
got, code, out = scenario(TAB)
delta("8 control: with no 'tables' switch a table is data: names skipped, a cell is not a passage (as before)", got, {})
got, code, out = scenario(TAB, cfg_fn=tb("narrative"))
delta("8: tables: narrative reads names in the cells (L5 Pavel) and each cell is a passage (L3 act 12 of 1898)", got, {"L5": 1, "L3": 1})
got, code, out = scenario(TAB, cfg_fn=tb("records"))
delta("8: tables: records skips the names (they are data) and reads each cell as a passage (L3)", got, {"L3": 1})
got, code, out = scenario(TAB, cfg_fn=tb("skip"))
delta("8: tables: skip reads nothing in a table", got, {})
got, code, out = scenario(TAB, cfg_fn=tb("skip", ["p", "li", "dd", "blockquote", "td"]))
delta("8: ... even when the config's blocks name td", got, {})
got, code, out = scenario(TAB, cfg_fn=lambda c, t: c["citations"].update(blocks=["p", "li", "dd", "blockquote", "td"]))
delta("8 control: without the switch a td named in the blocks is a passage (L3)", got, {"L3": 1})
got, code, out = scenario("<table><tr><td>act 12 of 1898</td><td><a href=\"/sources/x/\">link</a></td></tr></table>", cfg_fn=tb("records", ["p", "li", "dd", "blockquote", "tr"]))
delta("8: a row named in the blocks (tr) is the passage, so a link in another cell covers it, and the cells are not counted again", got, {})
got, code, out = scenario("", cfg_fn=tb("loose"))
case("8: an unknown mode is refused", code == 2 and "tables" in out, out)
got, code, out = scenario("", cfg_fn=lambda c, t: (c.update(tables="records"), c["names"].update(include_tables=True)))
case("8: names.include_tables that contradicts the switch is refused", code == 2 and "include_tables" in out, out)

# 9. a record link the archive's component marks
print("9. a component's own mark")
DR = '<p>Act 12 of 1898 <a href="/anything/" data-rec="act-12">cite</a>.</p>'
got, code, out = scenario(DR)
delta("9 control: data-rec alone is not a mark the gate knows by default (data-cite is)", got, {"L3": 1})
got, code, out = scenario(DR, cfg_fn=lambda c, t: c["citations"]["record_links"].update(markers=["data-cite", "data-rec"]))
delta("9: record_links.markers adds the attribute an archive's own component uses", got, {})

# ------------------------------------------------------------------------------------------------ counts only
print("counts only")
NAMES = set()
for r in IDX["people"] + IDX["ambiguous"]:
    NAMES.add(r["name"]); NAMES.update(r.get("aliases", []))
NAMES |= {"Marta Quill", "Marta Dorin", "Livia Vance", "Elio Quill", "Elio Marnetti", "Casimir", "Zed Marn", "Pavel"}
SLUGS = {r["url"].strip("/").split("/")[-1] for r in IDX["people"]} | {"livia-vance", "gone-person", "nobody-here"}
leak = [n for n in sorted(NAMES | SLUGS) if any(n.lower() in o.lower() for o in ALL_OUTPUT)]
case("nothing the tool printed, in %d runs, holds a name, alias or address of anyone in the fixtures or a passage of text" % len(ALL_OUTPUT), not leak, leak)

MUTATIONS = [
    ("next-block coverage off", "if nxt is not None and nxt.section == b.section", "if False and nxt.section == b.section"),
    ("L4 section test off", "if k not in sec_keys.get(b.section, ()):", "if False:"),
    ("ratchet off", "rose = [k for k in KEYS if c[k] > fl.get(k, new_max)]", "rose = []"),
    ("empty-reason exemption off", "bad_exempt += w.bad_exempt", "pass"),
    ("dead index address off", "if dead:", "if False:"),
    ("no-citation refusal off", 'if info_all["citing"] == 0:', "if False:"),
    ("living allow refusal off", "if n_liv:", "if False:"),
    ("EX not ratcheted", "rose = [k for k in KEYS if", "rose = [k for k in RULES if"),
    ("dead plate anchor accepted", "and href[1:] in ids", ""),
    ("any host accepted", 'if any(host == h or host.endswith("." + h) for h in cfg.rl_hosts):', "if True:"),
    ("write-floor ignores a rise", 'viol = [x for x in viol if x[0] != "new"] + strict\n        if viol:',
     'viol = [x for x in viol if x[0] not in ("new", "rise")] + strict\n        if viol:'),
    ("write-floor ignores --strict-config", 'viol = [x for x in viol if x[0] != "new"] + strict\n        if viol:',
     'viol = [x for x in viol if x[0] != "new"]\n        if viol:'),
    ("link text does not count as a full name", "self.full_seen.setdefault(sec, set()).update(loose(w) for w in ws)\n            return", "return"),
    ("allow list ignored", "if key in c.allow or f.name_exempt:", "if f.name_exempt:"),
    ("unmatched include not refused", "if unmatched:", "if False:"),
    ("section boundaries off", "if self.n_scope and tag in al.SECTION_TAGS:\n            self.section += 1", "pass"),
    ("link_only ignored", "or pid in cfg.link_only", ""),
    ("scans held on other pages ignored", "keys |= image_keys(src, cfg, seen)\n    if cfg.held_keys_file", "pass\n    if cfg.held_keys_file"),
    ("exempt passage still counted", "if b.exempt is not None:\n            if cite or", "if False:\n            if cite or"),
    ("L2 counted per mention", "self.l2.add(key)", "self.l2.add(key + str(len(self.l2)))"),
    ("entry pages in scope", "and not in_public(u)]", "]"),
    ("a new page is never held to the maximum", "if floor is not None and url in floor:", "if False:"),
    # the second round
    ("key not folded", "return loose(template.format(**vals))", "return template.format(**vals)"),
    ("an alias that matches nothing is not counted", "if k not in seen.gvals:\n            n += 1", "if False:\n            n += 1"),
    ("--strict-config ignored", 'strict = [("config", None, cfg_line)] if (a.strict_config and n_unmatched) else []', "strict = []"),
    ("plate keys from the archive's data ignored", "if pid in cfg.plate_keys:\n                out.update", "if False:\n                out.update"),
    ("unmatched plate id not counted", "if pid not in seen.plate_ids and not any(k in seen.ckeys for k in keys):", "if False:"),
    ("quotations not skipped", "segs = self._unquoted(F) if self.cfg.skip_quotes else [F]", "segs = [F]"),
    ("blockquote is not a quotation", 'tag in ("q", "blockquote")', 'tag in ("q",)'),
    ("a quotation mark never closes", "                if self.guil:\n                    self.guil -= 1", "                pass"),
    ("a single-word allow entry ignored", "elif f.name_exempt or w in c.allow:", "elif f.name_exempt:"),
    ("never_complete ignored", "if w in c.never:\n                            self.ex_names += 1", "if False:\n                            self.ex_names += 1"),
    ("an index name accepted in never_complete", "if n_idx:", "if False:"),
    ("scan_only still a citation", "cite = [h for h in hits if not h[3]]", "cite = list(hits)"),
    ("allow_prefixes ignored", "a.allow_prefix + cfg.allow_prefixes", "a.allow_prefix"),
    ("tables: skip reads tables", 'if c.tables == "skip" and f.table:', "if False:"),
    ("tables: narrative does not read cells", 'elif c.tables in ("narrative", "records") and tag in ("td", "th")', 'elif False and tag in ("td", "th")'),
    ("record-link markers ignored", "marked = any(m in a for m in c.rl_markers)", 'marked = "data-cite" in a'),
]


def mutations():
    """Break the tool one way at a time in a temporary copy of the kit and require the self-test to fail each time."""
    kit = os.path.dirname(HERE)
    src = open(os.path.join(HERE, "checkstandard.py"), encoding="utf-8").read()
    missed = 0
    for name, old, new in MUTATIONS:
        if old not in src:
            print("  FAIL  mutation %r: its text is no longer in checkstandard.py (update MUTATIONS)" % name); missed += 1
            continue
        t = tempfile.mkdtemp(prefix="checkstandard-mut-")
        shutil.copytree(os.path.join(kit, "tools"), os.path.join(t, "kit", "tools"), ignore=shutil.ignore_patterns("__pycache__"))
        for d in ("standard-fixtures", "autolink-fixtures"):
            shutil.copytree(os.path.join(kit, "data", d), os.path.join(t, "kit", "data", d))
        open(os.path.join(t, "kit", "tools", "checkstandard.py"), "w", encoding="utf-8").write(src.replace(old, new, 1))
        r = subprocess.run([sys.executable, os.path.join(t, "kit", "tools", "checkstandard_selftest.py")], capture_output=True, text=True)
        ok = r.returncode != 0
        missed += (not ok)
        print("  %s  mutation: %s (%d cases failed)" % ("ok  " if ok else "FAIL", name, r.stdout.count("FAIL")))
        shutil.rmtree(t, ignore_errors=True)
    return missed


print("\ncheckstandard_selftest: %d of %d cases ok" % (sum(res), len(res)))
rc = 0 if all(res) else 1
if "--mutations" in sys.argv and rc == 0:
    print("mutations of the tool")
    miss = mutations()
    print("checkstandard_selftest: %d of %d mutations noticed" % (len(MUTATIONS) - miss, len(MUTATIONS)))
    rc = 1 if miss else 0
sys.exit(rc)
