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


ANCHOR = r'<a href="([^"]*)" data-autolink="(?:person|near|search)"[^>]*>(.*?)</a>'


def added(h):
    return [(a, b) for a, b in re.findall(ANCHOR, h, re.S)]


def added_marks(h):
    return re.findall(r'<a href="([^"]*)" data-autolink="([a-z]+)"[^>]*>(.*?)</a>', h, re.S)


def stripped(h):
    return re.sub(ANCHOR, r"\2", h, flags=re.S)


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

# ------------------------------------------------------------------------------------------------ resolve: near
print("resolve rules: a shared name decided by a relative named in the section")
NIDX = os.path.join(FIX, "index-near.json")
NLIV = os.path.join(FIX, "living-near.json")
NSITE = os.path.join(FIX, "site-near")
NIX = json.load(open(NIDX, encoding="utf-8"))
for r in NIX["people"] + NIX["ambiguous"]:
    NAMES.add(r["name"]); NAMES.update(r.get("aliases", [])); SLUGS.add(r["url"].strip("/").split("/")[-1])


def fresh_near():
    t_ = tempfile.mkdtemp(prefix="autolink-near-")
    d_ = os.path.join(t_, "dist")
    shutil.copytree(NSITE, d_)
    return t_, d_


def sec_links(h):
    """{heading text: [(href, mark, text)]} for the added links of each <h2> section of the story page."""
    out = {}
    for chunk in h.split("<h2>")[1:]:
        head, _, body = chunk.partition("</h2>")
        out[head.split(":")[0]] = [(a, m, t_) for a, m, t_ in added_marks(body)]
    return out


t, d = fresh_near(); nbefore = snapshot(d)
c, out = autolink(d, index=NIDX, living=NLIV)
case("near: a run exits 0 and reports the three kinds", c == 0 and "added 29 links" in out and "14 to one person" in out
     and "6 to one person decided by a relative" in out and "9 to a search address" in out and "6 resolve rules, 1 relatives shared by two bearers" in out, out)
st = page(d, "story"); S = sec_links(st)
VALE, COE, SEARCH = "/people/nell-orrin-vale/", "/people/nell-orrin-coe/", "/people/?q=Nell%20Orrin"
nell = lambda sec: [(a, m) for a, m, t_ in S[sec] if t_ == "Nell Orrin"]
case("near: the spouse named first decides it (exact link to her page, data-autolink=near), and only once in the section",
     nell("One") == [(VALE, "near")], S["One"])
case("near: the relative named AFTER the name decides it too (the section is read as a whole)", nell("Two") == [(COE, "near")], S["Two"])
case("near: two rules that point at different people in one section fall back to the search link, never a guess",
     nell("Three") == [(SEARCH, "search")], S["Three"])
case("near: a relative of BOTH bearers decides nothing (two rules fire for different people) and the stats count the rule",
     nell("Four") == [(SEARCH, "search")] and al.load_index(NIDX, prefixes=None).stats["rules_shared_near"] == 1, S["Four"])
case("near: nobody beside her, so the search link; a name with no rules at all is a search link as before",
     nell("Five") == [(SEARCH, "search")] and ("/people/?q=Pavel%20Korda", "search", "Pavel Korda") in S["Five"], S["Five"])
case("near: a relative named only in ANOTHER section does not fire", nell("Seven") == [(SEARCH, "search")], S["Seven"])
case("near: a hand-made link to the relative in the section counts as named", nell("Eight") == [(COE, "near")], S["Eight"])
case("near: a relative inside a data-no-autolink block, or only in a heading, does not count",
     nell("Nine") == [(SEARCH, "search")] and nell("Eleven") == [(SEARCH, "search")], (S["Nine"], S["Eleven"]))
case("near: the bearer already linked in the section by hand covers the mention (no second link, no search link)",
     nell("Ten") == [] and "N. O.</a>, " in st, S["Ten"])
case("marks: person links say person, a person page is linked the same way",
     all(m == "person" for a, m, t_ in added_marks(st) if t_ in ("Hugo Vale", "Ivo Coe", "Sam Both", "Marta Arena")), added_marks(st)[:4])
srch = [x for x in re.findall(r'<a [^>]*data-autolink="search"[^>]*>', st)]
case("search: every search link carries class lk-shared, the title, and an aria-label that starts with the visible name",
     srch and all('class="lk-shared"' in x and 'title="Several people share this name: opens the list"' in x
                  and re.search(r'aria-label="(Nell Orrin|Pavel Korda), several people share this name: opens the list"', x) for x in srch), srch[:1])
case("search: no other link carries the class or the title (the cue is for unresolved links only)",
     all("lk-shared" not in x and "title=" not in x for x in re.findall(r'<a [^>]*data-autolink="(?:person|near)"[^>]*>', st)))
pp = page(d, "people/nell-orrin-vale")
case("near: a link made from a rule is a result, never evidence: Ivo Marl is decided by Marta Arena, and that does not also decide Nell Orrin by Ivo Coe",
     [(a, m) for a, m, t_ in S["Twelve"] if t_ in ("Ivo Marl", "Nell Orrin")] == [("/people/ivo-coe/", "near"), (VALE, "near")], S["Twelve"])
case("near: a counter-rule (url null) for a relative of a bearer who cannot be linked turns an otherwise-decided name into a search link, and decides nothing alone",
     nell("Thirteen") == [(SEARCH, "search")] and nell("Fourteen") == [(SEARCH, "search")], (S["Thirteen"], S["Fourteen"]))
case("near: it works on a person page's own text as it does anywhere in scope", added_marks(pp) == [("/people/hugo-vale/", "person", "Hugo Vale"), (VALE, "near", "Nell Orrin")], added_marks(pp))
case("near: not one other byte moves (wrappers removed give back every page exactly)",
     all(stripped(open(os.path.join(d, k), encoding="utf-8", newline="").read()) == v.decode("utf-8") for k, v in nbefore.items()))
case("near: never a link inside a link", all(nested_links(open(os.path.join(d, k), encoding="utf-8").read()) == 0 for k in nbefore))
nafter = snapshot(d)
c2, out2 = autolink(d, index=NIDX, living=NLIV)
case("near: idempotent: a second run adds 0 and changes no byte", c2 == 0 and "added 0 links" in out2 and snapshot(d) == nafter, out2)
c3, out3 = autolink(d, ["--check"], index=NIDX, living=NLIV)
case("near: --check on a processed build exits 0", c3 == 0, out3)
nfl = os.path.join(t, "floor.json")
c, out = gate(d, index=NIDX, living=NLIV, floor=nfl)
case("near gate: counts exact, near and search separately", c == 0 and "29 data-autolink links checked (14 exact, 6 near, 9 search)" in out, out)

# the gate's planted faults on the processed build
base_story = page(d, "story")
NEARLINK = '<a href="%s" data-autolink="near">Nell Orrin</a>' % VALE
for label, repl, want in [
    ("a near link to an address that is not in the index", NEARLINK.replace(VALE, "/people/nobody-here/"), "not in the index"),
    ("a near link whose section names none of its rule's relatives", '<h2>Fifteen: alone</h2><p>%s</p>' % NEARLINK, "near:"),
    ("a near link to a bearer when the section's relative points at the other bearer", '<h2>Fifteen: x</h2><p>Ivo Coe and %s</p>' % NEARLINK, "near:"),
    ("a near link on a name that has no rule at all", '<h2>Fifteen: x</h2><p>Hugo Vale and <a href="/people/hugo-vale/" data-autolink="near">Pavel Korda</a></p>', "near:"),
    ("a person link marked near", '<h2>Fifteen: x</h2><p><a href="/people/hugo-vale/" data-autolink="near">Hugo Vale</a></p>', "near:"),
    ("a mark the tool never writes", '<h2>Fifteen: x</h2><p><a href="/people/hugo-vale/" data-autolink="exact">Hugo Vale</a></p>', "stale:"),
    ("a search link without the class that names it", '<h2>Fifteen: x</h2><p><a href="/people/?q=Nell%20Orrin" data-autolink="search" title="Several people share this name: opens the list">Nell Orrin</a></p>', "search:"),
    ("a search link without the title", '<h2>Fifteen: x</h2><p><a href="/people/?q=Nell%20Orrin" data-autolink="search" class="lk-shared">Nell Orrin</a></p>', "search:"),
    ("a person link that goes to a search address", '<h2>Fifteen: x</h2><p><a href="/people/?q=Nell%20Orrin" data-autolink="person">Nell Orrin</a></p>', "stale:"),
    ("a near link to a person the living list holds", '<h2>Fifteen: x</h2><p>Hugo Vale and <a href="/people/wren-pell/" data-autolink="near">Nell Orrin</a></p>', "living:"),
]:
    put(d, "story", base_story.replace("</main>", "%s</main>" % (repl if repl.startswith("<h2>") else "<h2>Fifteen: x</h2><p>Hugo Vale and %s</p>" % repl)))
    c, out = gate(d, index=NIDX, living=NLIV, floor=nfl)
    case("near gate: %s fails" % label, c == 1 and want in out and "wren-pell" not in out and "nobody-here" not in out, out)
put(d, "story", base_story.replace("</main>", '<h2>Fifteen: x</h2><p>Hugo Vale and %s</p></main>' % NEARLINK))
c, out = gate(d, index=NIDX, living=NLIV, floor=nfl)
case("near gate: control: a near link whose section does name its relative passes (so the faults above can fail)", c == 0, out)
put(d, "story", base_story)
# the same page, the rule's relative is not in the section any more: the link has gone stale
gone = '<a href="/people/hugo-vale/" data-autolink="person">Hugo Vale</a> married '
put(d, "story", base_story.replace(gone, "Someone married "))
assert gone in base_story
c, out = gate(d, index=NIDX, living=NLIV, floor=nfl)
case("near gate: a relative taken out of the text afterwards makes the near link fail (rebuild and re-run)", c == 1 and "near:" in out, out)
put(d, "story", base_story)

# refusals for the rules themselves
def near_refused(mut, label, want, living=NLIV):
    obj = json.loads(json.dumps(NIX)); mut(obj)
    t_, d_ = fresh_near()
    ip = os.path.join(t_, "ix.json"); json.dump(obj, open(ip, "w", encoding="utf-8"))
    b = snapshot(d_)
    for tn in ("autolink.py", "checklinks.py"):
        c_, o_ = (autolink if tn == "autolink.py" else gate)(d_, index=ip, living=living)
        case("%s: %s is refused with exit 2 and nothing changes" % (tn.split(".")[0], label),
             c_ == 2 and want in o_ and snapshot(d_) == b and "wren-pell" not in o_ and "Wren" not in o_, o_)
    shutil.rmtree(t_, ignore_errors=True)

near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/hugo-vale/", "url": "/people/wren-pell/"}),
             "a resolve rule to a living person (planted)", "LIVING: 1 index entry")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/wren-pell/", "url": VALE}),
             "a resolve rule whose relative is a living person (planted)", "LIVING: 1 index entry")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/hugo-vale/", "url": "/people/not-indexed/"}),
             "a rule that decides on a person the index does not list", "does not hold")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/not-indexed/", "url": VALE}),
             "a rule whose relative the index does not list", "does not hold")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/hugo-vale/", "url": "/people/other-bearer/"}) or o["ambiguous"][1].update(
             bearers=["/people/other-bearer/"]), "a rule whose person is listed as a bearer of a DIFFERENT name only", "does not hold")
near_refused(lambda o: o["ambiguous"][0]["bearers"].append("/people/wren-pell/"), "a bearer who is living (planted)", "LIVING: 1 index entry")
near_refused(lambda o: o["ambiguous"][0]["bearers"].append("/admin/x/"), "a bearer outside the public prefixes", "malformed")
near_refused(lambda o: o["ambiguous"][0].update(bearers="nope"), "bearers that is not a list", "malformed")
near_refused(lambda o: o["people"][0].update(bearers=[COE]), "bearers on a people row", "malformed")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": VALE, "url": VALE}), "a rule that points at itself", "malformed")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/hugo-vale/"}), "a rule with no url key (a counter-rule says url: null)", "malformed")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/hugo-vale/", "url": 5}), "a rule whose url is not an address or null", "malformed")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/wren-pell/", "url": None}), "a counter-rule whose relative is a living person (planted)", "LIVING: 1 index entry")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/people/not-indexed/", "url": None}), "a counter-rule whose relative the index does not list", "does not hold")
near_refused(lambda o: o["ambiguous"][0].update(resolve={"a": 1}), "resolve that is not a list", "malformed")
near_refused(lambda o: o["people"][0].update(resolve=[{"near": VALE, "url": COE}]), "resolve on a people row", "malformed")
near_refused(lambda o: o["ambiguous"][0]["resolve"].append({"near": "/admin/x/", "url": VALE}), "a rule outside the public prefixes", "malformed")
near_refused(lambda o: o.update(labels={"shared": 3}), "labels that are not strings", "labels")

# the near window: "beside" is a distance in text, not the whole section (a long page is one section for many families)
FILL = " ".join(["word"] * 100)                      # 499 characters of text between the two names
def nearwin(window, body):
    obj = json.loads(json.dumps(NIX))
    if window is not None:
        obj["nearWindow"] = window
    ix_ = mk_index_obj(obj)
    out_, sc_ = micro(body, idx=ix_)
    return [(a, m) for a, m, t_ in added_marks(out_) if t_ == "Nell Orrin"]
def mk_index_obj(obj):
    t_ = tempfile.mkdtemp(prefix="autolink-ix-"); ip_ = os.path.join(t_, "i.json"); json.dump(obj, open(ip_, "w", encoding="utf-8"))
    try:
        return al.load_index(ip_)
    finally:
        shutil.rmtree(t_, ignore_errors=True)
before_, after_ = "<p>Hugo Vale. %s Nell Orrin.</p>" % FILL, "<p>Nell Orrin. %s Hugo Vale.</p>" % FILL
near_, far_ = "<p>Hugo Vale. %s Nell Orrin.</p>" % ("word " * 20), "<p>Nell Orrin said so. Hugo Vale.</p>"
case("window: by default (120 characters) a relative 500 characters away, before or after, decides nothing: the search link",
     nearwin(None, before_) == [(SEARCH, "search")] and nearwin(None, after_) == [(SEARCH, "search")], (nearwin(None, before_), nearwin(None, after_)))
case("window: ...and one within it decides, before or after", nearwin(None, near_) == [(VALE, "near")] and nearwin(None, far_) == [(VALE, "near")], nearwin(None, near_))
case("window: nearWindow 0 in the index means the whole section", nearwin(0, before_) == [(VALE, "near")] and nearwin(0, after_) == [(VALE, "near")])
case("window: nearWindow 600 reaches it, 100 does not", nearwin(600, before_) == [(VALE, "near")] and nearwin(100, near_) == [(SEARCH, "search")])
case("window: a link counts by where it stands, like a mention",
     nearwin(None, '<p><a href="/people/hugo-vale/">his</a> %s Nell Orrin.</p>' % FILL) == [(SEARCH, "search")]
     and nearwin(None, '<p><a href="/people/hugo-vale/">his</a> Nell Orrin.</p>') == [(VALE, "near")])
case("window: the distance is in text, so markup between the names does not use it up",
     nearwin(None, "<p>Hugo Vale<span class='x' data-a='%s'> and </span><b>Nell Orrin</b>.</p>" % FILL) == [(VALE, "near")])
# the block: a relative counts only in the same paragraph, list item, table row, quotation... as the shared name
case("block: a relative in the NEXT paragraph, list item or table row decides nothing (a section is not one place)",
     nearwin(None, "<p>Hugo Vale.</p><p>Nell Orrin.</p>") == [(SEARCH, "search")]
     and nearwin(None, "<ul><li>Hugo Vale</li><li>Nell Orrin</li></ul>") == [(SEARCH, "search")]
     and nearwin(None, "<table><tr><td>Hugo Vale</td></tr><tr><td>Nell Orrin</td></tr></table>") == [(SEARCH, "search")]
     and nearwin(0, "<p>Hugo Vale.</p><p>Nell Orrin.</p>") == [(SEARCH, "search")])
case("block: ...but in the same one, however many cells or inline elements lie between, it decides",
     nearwin(None, "<table><tr><td>Hugo Vale</td><td>1850</td><td>Nell Orrin</td></tr></table>") == [(VALE, "near")]
     and nearwin(None, "<ul><li><b>Hugo Vale</b> and <i><a href='#'>x</a> Nell Orrin</i></li></ul>") == [(VALE, "near")]
     and nearwin(None, "<blockquote>Nell Orrin, wife of Hugo Vale</blockquote>") == [(VALE, "near")])
case("block: a list item inside a paragraph-less div is its own block; text with no block element around it is one block per section",
     nearwin(None, "<div>Hugo Vale and Nell Orrin</div>") == [(VALE, "near")]
     and nearwin(None, "<div>Hugo Vale</div><p>Nell Orrin.</p>") == [(SEARCH, "search")])
case("block: a hand-made link counts in its own block only",
     nearwin(None, '<p><a href="/people/hugo-vale/">x</a></p><p>Nell Orrin.</p>') == [(SEARCH, "search")])
for bad_w in (-1, "300", True, 1.5):
    near_refused(lambda o, w=bad_w: o.update(nearWindow=w), "nearWindow %r" % (bad_w,), "nearWindow")
t2, d2 = fresh_near(); obj = json.loads(json.dumps(NIX)); obj["nearWindow"] = 0
put(d2, "wide", "<html><body><main><h1>x</h1><p>Hugo Vale. %s Nell Orrin.</p></main></body></html>" % FILL)
ip = os.path.join(t2, "ix.json"); json.dump(obj, open(ip, "w", encoding="utf-8"))
c, out = autolink(d2, index=ip, living=NLIV)
case("window: a build made with nearWindow 0 links the far relative", c == 0 and (VALE, "near") in [(a, m) for a, m, t_ in added_marks(page(d2, "wide"))], out)
c, out = gate(d2, index=ip, living=NLIV, floor=os.path.join(t2, "f.json"))
case("window: the gate, given the same window, passes", c == 0, out)
c, out = gate(d2, ["--near-window", "300"], index=ip, living=NLIV, floor=os.path.join(t2, "f.json"))
case("window: the gate, run with a narrower window than the pass, fails the near link (the two must agree)", c == 1 and "near:" in out, out)
shutil.rmtree(t2, ignore_errors=True)

# labels: configurable text, and off
for label, labels, check in [
    ("custom text", {"shared": "Mehrere Personen tragen diesen Namen"}, lambda x: 'title="Mehrere Personen tragen diesen Namen"' in x and re.search(r'aria-label="(Nell Orrin|Pavel Korda), mehrere Personen tragen diesen Namen"', x)),
    ("an empty text turns the title and aria-label off but keeps the class", {"shared": ""}, lambda x: 'class="lk-shared"' in x and "title=" not in x and "aria-label" not in x),
    ("markup in the text is escaped in the attribute", {"shared": 'A "few" <b>&'}, lambda x: 'title="A &quot;few&quot; &lt;b&gt;&amp;"' in x and "<b>" not in x),
]:
    obj = json.loads(json.dumps(NIX)); obj["labels"] = labels
    t2, d2 = fresh_near(); ip = os.path.join(t2, "ix.json"); json.dump(obj, open(ip, "w", encoding="utf-8"))
    c, out = autolink(d2, index=ip, living=NLIV)
    x = [m for m in re.findall(r'<a [^>]*data-autolink="search"[^>]*>', page(d2, "story")) if "Nell" in m or "lk-shared" in m]
    c2, out2 = gate(d2, index=ip, living=NLIV, floor=os.path.join(t2, "f.json"))
    case("labels: %s; the gate agrees" % label, c == 0 and x and all(check(m) for m in x) and c2 == 0, (out, x[:1], out2))
    shutil.rmtree(t2, ignore_errors=True)

# a build made by the previous kit (a bare data-autolink) still passes the gate
t2, d2 = fresh(); autolink(d2)
legacy = re.sub(r' data-autolink="(?:person|near|search)"[^>]*>', " data-autolink>", page(d2, "story"))
legacy = re.sub(r'<a href="([^"]*)" data-autolink>', r'<a href="\1" data-autolink>', legacy)
put(d2, "story", legacy)
c, out = gate(d2, ["--write-floor"])
case("a page made by the previous kit (bare data-autolink) is still read: exact links by their address", c == 0 and "exact" in out, out)
shutil.rmtree(t2, ignore_errors=True)

# without any resolve rule the tool behaves exactly as before, apart from the marks
t2, d2 = fresh_near(); obj = json.loads(json.dumps(NIX))
for r_ in obj["ambiguous"]:
    r_.pop("resolve", None)
ip = os.path.join(t2, "ix.json"); json.dump(obj, open(ip, "w", encoding="utf-8"))
c, out = autolink(d2, index=ip, living=NLIV)
case("an index with no resolve rule links every Nell Orrin to the search address", c == 0 and "0 to one person decided" in out
     and all(m == "search" for a, m, t_ in added_marks(page(d2, "story")) if t_ == "Nell Orrin"), out)
shutil.rmtree(t2, ignore_errors=True)
shutil.rmtree(t, ignore_errors=True)

# ------------------------------------------------------------------------------------------------ counts only
print("counts only")
leak = [n for n in sorted(NAMES | SLUGS) if any(n.lower() in o.lower() for o in ALL_OUTPUT)]
case("nothing either tool printed, in %d runs, holds a name, alias or address of anyone in the index" % len(ALL_OUTPUT), not leak, leak)

print("\nautolink_selftest: %d of %d cases ok" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
