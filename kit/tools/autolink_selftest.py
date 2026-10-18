#!/usr/bin/env python3
"""Prove autolink.py and checklinks.py do what they say, and that each planted fault is caught. Invented fixtures only
(kit/data/autolink-fixtures/).

    python3 kit/tools/autolink_selftest.py

The CLI cases run the tools as a subprocess (exit codes are part of the contract); the matching cases call the module.
Nothing here prints a name from a real archive, and the tools' own output is searched for the invented names to prove
they print counts only.
"""
import os, sys, re, json, shutil, tempfile, subprocess, html.parser
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autolink as al
FIX = os.path.join(os.path.dirname(HERE), "data", "autolink-fixtures")
INDEX = os.path.join(FIX, "index.json")
LIVING = os.path.join(FIX, "living.json")
SITE = os.path.join(FIX, "site")
IDX = json.load(open(INDEX, encoding="utf-8"))
res = []
ALL_OUTPUT = []        # everything either tool printed, searched for names at the end


def case(label, ok, detail=""):
    res.append(bool(ok))
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", label, ("  [" + str(detail)[:200] + "]") if detail and not ok else ""))


def tool(name, args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "ARCHIVE_OUT"}
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, os.path.join(HERE, name)] + args, capture_output=True, text=True, env=env)
    out = p.stdout + p.stderr
    ALL_OUTPUT.append(out)
    return p.returncode, out


def autolink(dist, extra=None, index=INDEX, living=LIVING):
    a = ["--dist", dist, "--index", index]
    if living:
        a += ["--living", living]
    return tool("autolink.py", a + (extra or []))


def gate(dist, extra=None, index=INDEX, living=LIVING, floor=None):
    a = ["--dist", dist, "--index", index, "--floor", floor or os.path.join(os.path.dirname(dist), "floor.json")]
    if living:
        a += ["--living", living]
    return tool("checklinks.py", a + (extra or []))


def fresh():
    t = tempfile.mkdtemp(prefix="autolink-")
    d = os.path.join(t, "dist")
    shutil.copytree(SITE, d)
    return t, d


def snapshot(dist):
    out = {}
    for d, _, fs in os.walk(dist):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, dist)] = open(p, "rb").read()
    return out


def page(dist, rel):
    return open(os.path.join(dist, rel, "index.html"), encoding="utf-8", newline="").read()


def put(dist, rel, text):
    d = os.path.join(dist, rel)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="").write(text)


def added(h):
    return re.findall(r'<a href="([^"]*)" data-autolink>(.*?)</a>', h, re.S)


def stripped(h):
    return re.sub(r'<a href="[^"]*" data-autolink>(.*?)</a>', r"\1", h, flags=re.S)


class Nest(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.depth = 0; self.bad = 0
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.depth += 1
            if self.depth > 1: self.bad += 1
    def handle_endtag(self, tag):
        if tag == "a": self.depth = max(0, self.depth - 1)


def nested_links(h):
    p = Nest(); p.feed(h); return p.bad


def micro(body, idx=None, living=True, scope="main"):
    """Run the module over one fragment inside <main>; returns (output html, scan)."""
    global _IDX
    if idx is None:
        idx = _IDX_L if living else _IDX
    out, sc = al.autolink_html("<html><body><main>%s</main></body></html>" % body, idx, scope)
    return out, sc


def mk_index(obj, living=None, prefixes=None):
    t = tempfile.mkdtemp(prefix="autolink-ix-")
    ip = os.path.join(t, "index.json"); json.dump(obj, open(ip, "w", encoding="utf-8"))
    ln, lu = (set(), set())
    if living is not None:
        lp = os.path.join(t, "living.json"); json.dump(living, open(lp, "w", encoding="utf-8"))
        ln, lu = al.load_living(lp)
    try:
        return al.load_index(ip, ln, lu, prefixes)
    finally:
        shutil.rmtree(t, ignore_errors=True)


_IDX = mk_index(IDX)
_IDX_L = mk_index(IDX, json.load(open(LIVING, encoding="utf-8")))
NAMES = set()
for r in IDX["people"] + IDX["ambiguous"]:
    NAMES.add(r["name"]); NAMES.update(r.get("aliases", []))
SLUGS = {r["url"].strip("/").split("/")[-1] for r in IDX["people"]}

# ------------------------------------------------------------------------------------------------ the clean run
print("a clean run")
t, d = fresh(); before = snapshot(d)
c, out = autolink(d)
case("a clean run exits 0 and adds links", c == 0 and "added 29 links" in out, out)
story = page(d, "story")
exp = [("/people/orsolo-venti/", "Orsolo Venti"), ("/people/marta-arena/", "Marta Arena"),
       ("/people/orsolo-venti/", "Venti Orsolo"), ("/people/elio-marn-costa/", "Elio Marn Costa"), ("/people/elio-marn/", "Elio Marn"),
       ("/people/elio-marn/", "Elio Marn"), ("/people/elio-marn-costa/", "Elio Marn Costa"),
       ("/people/marta-arena/", "Marta Arena"), ("/people/marta-arena/", "Marta Arena")]
case("the story page is linked exactly where the rules say: the first mention in each section, in order", added(story) == exp, added(story))
case("the section boundaries (h2, h3, section) each start the count again",
     [h for h, _ in added(story)].count("/people/orsolo-venti/") == 2 and [h for h, _ in added(story)].count("/people/marta-arena/") == 3, added(story))
case("longest name first: Elio Marn Costa goes to its own person, never to Elio Marn",
     all(h == "/people/elio-marn-costa/" for h, t_ in added(story) if t_ == "Elio Marn Costa") and ("/people/elio-marn/", "Elio Marn Costa") not in added(story))
case("an alias links to the same person as the name, once per section",
     ("/people/orsolo-venti/", "Venti Orsolo") in added(story) and sum(1 for h, _ in added(story) if h == "/people/orsolo-venti/") == 2)
case("a heading is skipped, so is text outside <main> and in the <title>",
     "<h1>The story of Orsolo Venti</h1>" in story and "<h2>Second part: Orsolo Venti</h2>" in story
     and "<header><p>Orsolo Venti is named" in story and "<title>Orsolo Venti and the story</title>" in story)
case("the possessive still names the person (Marta Arena's)", "Marta Arena's cousin" in story)
sk = page(d, "skips")
head, ctrl = sk.split('id="control"')
case("nothing is linked inside a link, heading, nav, code, pre, script, style, svg, button, textarea, select, or data-no-autolink", "data-autolink" not in head, added(head))
case("the same names in plain running text ARE linked (the skips above are not an accident)", len(added(ctrl)) == 11, added(ctrl))
case("an ambiguous name goes to the archive's search address, and an & in it is escaped in the attribute",
     ("/people/?q=Pavel%20Korda", "Pavel Korda") in added(ctrl) and 'href="/people/?q=Kit%20Mallow&amp;kind=dead"' in ctrl)
fm = page(d, "format")
case("ALL-CAPS surname, an entity apostrophe, a no-break space, an ampersand and a combining mark all match, text kept as written",
     [t_ for _, t_ in added(fm)] == ["Hannah SANIGER", "Nino D&#8217;Orsa", "Orsolo&nbsp;Venti", "Tamsin Brightwell", "Wilhelm Ostrander", "Zoe&#776; Quill"], added(fm))
case("a name in an attribute, a comment, an <img alt>, or after </main> is not linked",
     'title="Elio Marn > Costa"' in fm and 'alt="Marta Arena"' in fm and "<footer>Pavel Korda</footer>" in fm and "<!-- Orsolo Venti in a comment" in fm)
lv = page(d, "living")
case("a living name beside a dead one: the dead name inside the living name is NOT linked, a later separate mention is",
     added(lv) == [("/people/marta-arena/", "Marta Arena")] and "Marta Arena Hollis visited" in lv and "LIVIA VANCE were" in lv, added(lv))
case("a page with no <main> is left exactly as it was", open(os.path.join(d, "404.html"), "rb").read() == before["404.html"])
case("not one other byte moves: removing the added wrappers gives back every page exactly",
     all(stripped(open(os.path.join(d, k), encoding="utf-8", newline="").read()) == v.decode("utf-8")
         for k, v in before.items()))
case("never a link inside a link, on any page", all(nested_links(open(os.path.join(d, k), encoding="utf-8").read()) == 0 for k in before))
after = snapshot(d)
c2, out2 = autolink(d)
case("idempotent: a second run exits 0, says it added 0, and changes no byte", c2 == 0 and "added 0 links" in out2 and snapshot(d) == after, out2)
c3, out3 = autolink(d, ["--check"])
case("--check on a processed build exits 0", c3 == 0, out3)
shutil.rmtree(t, ignore_errors=True)

t, d = fresh(); before = snapshot(d)
c, out = autolink(d, ["--check"])
case("--check on an unprocessed build exits 1 and changes nothing", c == 1 and "would add 29" in out and snapshot(d) == before, out)
# the control for the living rule: the same build with NO living list links the name inside the living name
c, out = autolink(d, living=None)
lv0 = page(d, "living")
case("control: without the living list the dead name inside the living name WOULD be linked (so the test above can fail)",
     c == 0 and ("/people/marta-arena/", "Marta Arena") == added(lv0)[0] and lv0.index("data-autolink") < lv0.index("Hollis"), added(lv0))
shutil.rmtree(t, ignore_errors=True)

# CRLF, tabs and a missing final newline survive
t, d = fresh()
fmt = page(d, "format").replace("\n", "\r\n")
put(d, "format", fmt); c, out = autolink(d)
fm2 = page(d, "format")
case("CRLF line endings and a page with no final newline come back byte for byte once the wrappers are removed",
     c == 0 and "\r\n" in fm2 and stripped(fm2) == fmt and len(added(fm2)) == 6, out)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ matching rules
print("matching rules")
def linked_texts(body, **kw):
    out, sc = micro(body, **kw)
    return [t_ for _, t_ in added(out)], out

for text, want, why in [
    ("Marta Arenaria", False, "Arena inside Arenaria"), ("Marta Arenà", False, "an accented letter continues the word"),
    ("xMarta Arena", False, "a letter before"), ("Marta Arena-Rossi", False, "a hyphenated surname"), ("Marta Arenas", False, "a plural"),
    ("Marta Arena.", True, "a full stop after"), ("(Marta Arena)", True, "brackets round"), ("Marta Arena’s", True, "a possessive with a typographic apostrophe"),
    ("Marta Arena’ski", False, "an apostrophe then more letters"), ("Marta   Arena", True, "extra spaces inside the name"),
    ("Marta\nArena", True, "a line break inside the name"), ("Marta d'Arena", False, "an elided form is another name"),
    ("Martha Arena", False, "a different spelling"), ("marta arena", False, "lower case is not the register's capitals form"),
    ("MARTA ARENA", True, "all capitals"), ("Marta ARENA", True, "capitals surname"), ("MARTA Arena", True, "capitals given name"),
    ("_Marta Arena", False, "an underscore before"), ("Marta Arena1", False, "a digit continues the word"), ("Marta_Arena", False, "an underscore joins"),
    ("Zoë Quill", True, "a decomposed diaeresis equals the composed name"), ("Zoe Quill", False, "no diaeresis is another spelling"),
    ("Nino D’Orsa", True, "typographic apostrophe in the name"), ("Nino D'Orsa", True, "straight apostrophe"),
    ("Orsolo Venti", True, "a no-break space"),
]:
    got, _ = linked_texts("<p>%s</p>" % text)
    case("boundaries: %s -> %s (%s)" % (re.sub(r"\s", " ", text), "linked" if want else "left alone", why), bool(got) == want, got)
got, _ = linked_texts("<p>Hannah SANIGER, then HANNAH SANIGER.</p><h2>x</h2><p>HANNAH SANIGER</p>")
case("an ALL-CAPS name keeps its text and is linked once per section", got == ["Hannah SANIGER", "HANNAH SANIGER"], got)
got, _ = linked_texts("<p>An ALL-CAPS single letter or a short caps word does not fake a match: Hannah S and HANNAH SA.</p>")
case("a partial caps surname does not match", got == [], got)

out, sc = micro('<p><a href="/people/hannah-saniger/">H. S.</a></p><p>Hannah Saniger</p>')
case("a person already linked in the section (by any link to the same address) is not linked again", "data-autolink" not in out and sc.covered == 1)
out, sc = micro('<p>Hannah Saniger</p><p><a href="/people/hannah-saniger/#sources">her page</a></p>')
case("...even when that link comes later in the section, and carries a fragment", "data-autolink" not in out and sc.covered == 1)
out, sc = micro('<p><a href="/people/hannah-saniger/">H. S.</a></p><h2>Two</h2><p>Hannah Saniger</p>')
case("...but a link in another section does not count", len(added(out)) == 1)
out, sc = micro('<p>Hannah Saniger</p>', scope="article")
case("a page without the scope element is not touched", out.count("data-autolink") == 0 and not sc.scope_seen)
out, sc = micro('<p>Hannah Saniger</p>', scope="body")
case("--scope picks the element (body here)", len(added(out)) == 1)
out, sc = micro('<p>Hannah Saniger</p><p>Orsolo Venti</p>', idx=mk_index({"people": [{"name": "Hannah Saniger", "url": "/people/a/"}, {"name": "Orsolo Venti", "url": "/people/a/"}]}))
case("two names of one address are linked once per section", len(added(out)) == 1, added(out))
ix = mk_index({"people": [{"name": "Lone Name", "url": "/people/a/"}, {"name": "Lone Name", "url": "/people/b/"}, {"name": "Pair Name", "url": "/people/c/"}, {"name": "Good Name", "url": "/people/g/"}],
               "ambiguous": [{"name": "Pair Name", "url": "/people/?q=Pair%20Name"}, {"name": "Single", "url": "/people/d/"}]})
out, sc = micro("<p>Lone Name, Pair Name, Single, Good Name.</p>", idx=ix)
case("a name that leads to two addresses (or is both unique and ambiguous), and a one-word name, are skipped and counted, not guessed",
     out.count("data-autolink") == 1 and ix.stats["conflicts_skipped"] == 4 and ix.stats["short_skipped"] == 1, ix.stats)
out, sc = micro("<p>Orsolo Venti</p><p>Orsolo Venti</p>")
case("the same name twice in one section: one link", len(added(out)) == 1)

# ------------------------------------------------------------------------------------------------ the living rule and refusals
print("the living rule and the refusals")
def refused(index_obj, extra=None, living=LIVING, tool_name="autolink.py", build=None):
    t_, d_ = fresh()
    ip = os.path.join(t_, "ix.json"); json.dump(index_obj, open(ip, "w", encoding="utf-8"))
    b = snapshot(d_)
    if tool_name == "autolink.py":
        c_, o_ = autolink(d_, extra, index=ip, living=living)
    else:
        c_, o_ = gate(d_, extra, index=ip, living=living)
    same = snapshot(d_) == b
    shutil.rmtree(t_, ignore_errors=True)
    return c_, o_, same

for label, row in [("a name the living list holds", {"name": "Livia Vance", "url": "/people/lv2/"}),
                   ("a name the living list holds, written in capitals", {"name": "LIVIA VANCE", "url": "/people/lv2/"}),
                   ("an alias the living list holds", {"name": "Dora Wick", "aliases": ["Livia Vance"], "url": "/people/dw/"}),
                   ("an address the living list holds", {"name": "Dora Wick", "url": "/people/livia-vance/"})]:
    bad = json.loads(json.dumps(IDX)); bad["people"].append(row)
    for tn in ("autolink.py", "checklinks.py"):
        c, out, same = refused(bad, tool_name=tn)
        case("%s: an index with %s fails with exit 2, names only a count, and changes nothing" % (tn.split(".")[0], label),
             c == 2 and "LIVING: 1 index entry" in out and "Livia" not in out and "Vance" not in out and "livia-vance" not in out and same, out)
bad = json.loads(json.dumps(IDX)); bad["people"].append({"name": "Pavel Korda", "url": "/people/pk/"})
bad["ambiguous"].append({"name": "Livia Vance", "url": "/people/?q=Livia"})
c, out, same = refused(bad)
case("a living name in the ambiguous list fails too", c == 2 and "LIVING" in out, out)
c, out, same = refused(IDX, living=os.path.join(FIX, "nope.json"))
case("an unreadable living list is a refusal, not a run without it", c == 2 and "living list" in out, out)

bad = json.loads(json.dumps(IDX)); bad["people"].append({"name": "Dora Wick", "url": "/admin/dora/"})
c, out, same = refused(bad)
case("an address outside the public prefixes is refused (exit 2)", c == 2 and "outside the public prefixes" in out and same, out)
c, out, same = refused(bad, ["--allow-prefix", "/admin/", "--allow-prefix", "/people/", "--allow-prefix", "/who/"])
case("...unless the archive names that prefix", c == 0, out)
bad = json.loads(json.dumps(IDX)); bad["people"].append({"name": "Dora Wick", "url": "https://elsewhere.example/people/dora/"})
c, out, same = refused(bad)
case("an absolute address is refused", c == 2, out)
bad = {"people": [{"name": "Dora Wick"}]}
c, out, same = refused(bad)
case("an entry with no address is refused", c == 2 and "malformed" in out, out)
for tn in ("autolink.py", "checklinks.py"):
    c, out, same = refused({"people": [], "ambiguous": []}, tool_name=tn)
    case("%s: an empty index is refused (a check that examined nothing has not passed)" % tn.split(".")[0], c == 2 and "empty" in out and same, out)
    c, out, same = refused({"nonsense": 1}, tool_name=tn)
    case("%s: an index with neither list is refused" % tn.split(".")[0], c == 2, out)

t = tempfile.mkdtemp(prefix="autolink-"); empty = os.path.join(t, "dist"); os.makedirs(empty)
for tn, fn in (("autolink", autolink), ("checklinks", gate)):
    c, out = fn(empty)
    case("%s: an empty build is refused" % tn, c == 2 and "nothing was examined" in out, out)
    c, out = fn(os.path.join(t, "missing"))
    case("%s: a build directory that does not exist is refused" % tn, c == 2, out)
put(empty, "x", "<html><body><p>Marta Arena</p></body></html>")
for tn, fn in (("autolink", autolink), ("checklinks", gate)):
    c, out = fn(empty)
    case("%s: pages without the scope element are refused, not passed" % tn, c == 2 and "wrong --scope" in out, out)
    c, out = fn(empty, ["--scope", "body"]) if tn == "autolink" else gate(empty, ["--scope", "body", "--write-floor"])
    case("%s: --scope body finds the page" % tn, c == 0, out)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ the gate
print("the gate")
t, d = fresh(); fl = os.path.join(t, "floor.json")
c, out = gate(d)
case("with no floor, a build that never ran autolink fails: pages above the new-page maximum", c == 1 and "new:" in out, out)
c, out = gate(d, ["--write-floor"])
fj = json.load(open(fl))["pages"]
case("--write-floor starts every page at its current count", c == 0 and fj["/story/"] == 9 and fj["/skips/"] == 11 and fj["/living/"] == 1 and "/index.html" not in fj and "/404.html" not in fj, (out, fj))
case("...and the floor does not hold a page that has no <main>", "/404.html" not in fj and len(fj) == 6, fj)
c, out = gate(d)
case("the same build passes against its own floor", c == 0 and "ok." in out, out)

# a rise
story_html = page(d, "story")
put(d, "story", story_html.replace("</main>", "<h2>More</h2><p>Hannah Saniger and Wilhelm Ostrander.</p></main>"))
c, out = gate(d)
case("RATCHET: a page whose count rises fails, and names the page", c == 1 and "rise: /story/" in out, out)
c, out = gate(d, ["--write-floor"])
case("RATCHET: --write-floor refuses to write while a page has risen", c == 1 and "NOT WRITTEN" in out and json.load(open(fl))["pages"]["/story/"] == 9, out)
put(d, "story", story_html)
# a rise on a person page: masked
pp = page(d, "people/orsolo-venti")
put(d, "people/orsolo-venti", pp.replace("</main>", "<h2>More</h2><p>Wilhelm Ostrander</p><h2>Again</h2><p>Hannah Saniger</p></main>"))
c, out = gate(d)
case("RATCHET: a person page that rose is reported in a group, its address (which is a name) is not printed",
     c == 1 and "1 page(s) under /people/" in out and "orsolo-venti" not in out, out)
put(d, "people/orsolo-venti", pp)
# a fall
c, out = autolink(d)
story_html = page(d, "story")            # from here on the story page is the processed one
c, out = gate(d)
case("RATCHET: counts that fell pass, and the summary says the floor can be lowered", c == 0 and "below their floor" in out, out)
c, out = gate(d, ["--write-floor"])
fj2 = json.load(open(fl))["pages"]
case("--write-floor locks the gain in (every page now 0)", c == 0 and all(v == 0 for v in fj2.values()) and len(fj2) == 6, fj2)
case("after autolink the gate counts 0 on every page: the two tools agree on what a missing link is",
     "0 resolvable names unlinked" in gate(d)[1])
# a floor never goes up by itself
put(d, "story", story_html.replace("</main>", "<h2>More</h2><p>Hannah Saniger</p></main>"))
c, out = gate(d, ["--write-floor"])
case("a floor that is 0 stays 0: --write-floor refuses a rise", c == 1 and json.load(open(fl))["pages"]["/story/"] == 0, out)
put(d, "story", story_html)
# a new page
newp = "<h2>a</h2><p>Hannah Saniger</p><h2>b</h2><p>Hannah Saniger</p><h2>c</h2><p>Hannah Saniger</p>"
put(d, "fresh", "<html><body><main>%s</main></body></html>" % newp)
c, out = gate(d)
case("NEW PAGE: a page not in the floor with 3 unlinked names (the default maximum) passes", c == 0, out)
put(d, "fresh", "<html><body><main>%s<h2>d</h2><p>Hannah Saniger</p></main></body></html>" % newp)
c, out = gate(d)
case("NEW PAGE: a page not in the floor with 4 fails", c == 1 and "new: /fresh/" in out, out)
c, out = gate(d, ["--new-page-max", "4"])
case("NEW PAGE: the maximum is configurable", c == 0, out)
os.remove(os.path.join(d, "fresh", "index.html")); os.rmdir(os.path.join(d, "fresh"))

# stale and living links
base = page(d, "story")
for label, repl, want in [
    ("a data-autolink link whose address is not in the index", '<a href="/people/gone-person/" data-autolink>Orsolo Venti</a>', "not in the index"),
    ("a data-autolink link whose text is not a name of its address", '<a href="/people/marta-arena/" data-autolink>Hannah Saniger</a>', "no longer a name"),
    ("a link added to a person the living list holds (by address)", '<a href="/people/livia-vance/" data-autolink>Someone Else</a>', "living"),
    ("a link added to a person the living list holds (by name)", '<a href="/people/marta-arena/" data-autolink>Livia Vance</a>', "living"),
]:
    put(d, "story", base.replace("</main>", "<p>%s</p></main>" % repl))
    c, out = gate(d)
    case("STALE/LIVING: %s fails" % label, c == 1 and (want + ":" in out or want in out) and "Livia" not in out and "gone-person" not in out, out)
put(d, "story", base.replace("</main>", '<p><a href="/people/gone-person/">a hand-made link to nowhere</a></p></main>'))
c, out = gate(d)
case("a hand-written link (no data-autolink) to an address not in the index is not this gate's business", c == 0, out)
put(d, "story", base)
c, out = gate(d, living=None)
case("the gate runs without a living list too", c == 0, out)
open(fl, "w").write("{not json")
c, out = gate(d)
case("a corrupt floor file is a refusal", c == 2 and "floor" in out, out)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ counts only
print("counts only")
leak = [n for n in sorted(NAMES | SLUGS) if any(n.lower() in o.lower() for o in ALL_OUTPUT)]
case("nothing either tool printed, in %d runs, holds a name, alias or address of anyone in the index" % len(ALL_OUTPUT), not leak, leak)

print("\nautolink_selftest: %d of %d cases ok" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
