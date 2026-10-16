#!/usr/bin/env python3
"""Can checkperson.py still fail?

A people-page check that reports «ok» on a page it cannot read is worse than no
check, and this one has a lot of ways to say nothing: it reads HTML with the
standard library, it recognises a page by a class, it decides a person is living
from two signals. So every rule below is proved the one way that counts: plant ONE
departure in an otherwise clean page and see the checker name exactly that
departure, and plant the clean page and see it stay quiet.

PLANTED VALUES ARE ONES NO LIVING PERSON CAN HAVE. Every date, year and place a fault
carries is 1799 (or the fictional «Testville»), so this file, which is tracked and
public, can never contain a living person's record.

THE THREE RULES THIS WAS EXTENDED FOR (living standard v2, 16 October 2026):
  (a) a living page shows nothing beyond name, relationships, town and country
  (b) a person the archive names, in a chart, has a page
  (c) an h1 never carries a qualifier longer than the name
and the refusal of an empty build (zero pages examined is not a pass).

Nothing shipped is ever broken to test it. Every fixture is built in a temporary
directory (tempfile.mkdtemp(prefix="checkperson-")), as checknav_selftest.py does.

  python3 kit/tools/checkperson_selftest.py

Exit 0 when every case behaves, 1 otherwise. Not wired into `npm test`, which is
checklogic.mjs; run it when checkperson.py or the page markup changes.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checkperson  # noqa: E402

fails = 0
cases = 0


def expect(name, cond, detail=""):
    global fails, cases
    cases += 1
    if cond:
        print(f"  ok    {name}")
    else:
        fails += 1
        print(f"  FAIL  {name}{('  ' + detail) if detail else ''}")


# ---- a clean DEAD person's canonical page
CHART = ('<figure class="ptree"><div class="tier self"><div class="row"><div class="node me"><span class="nm">A Person</span>'
         '<span class="dt">1799–1860</span></div></div></div></figure>')
SECTIONS = ('<section class="psec" id="family"><h2>Family</h2>{chart}</section>'
            '<section class="psec" id="record"><h2>What the record says</h2><p>Born at home.</p></section>'
            '<section class="psec" id="sources"><h2>Where this comes from</h2><p>A register.</p></section>')
LD_PERSON = '<script type="application/ld+json">{"@graph":[{"@type":"Person","name":"A Person"}]}</script>'
NOINDEX = '<meta name="robots" content="noindex">'
SENTENCE = ("A living person (80 or younger, with no death recorded) is named with their relationships "
            "and their town and country, and nothing more.")

# ---- a clean LIVING person's canonical page: the structure PersonPage draws
LIVING_CHART = ('<figure class="ptree"><div class="tier"><div class="lab">Parent</div><div class="row">'
                '<a class="node" href="/people/p/"><span class="nm">A Parent</span><span class="dt">1760–1799</span></a></div></div>'
                '<div class="tier self"><div class="row"><div class="node me"><span class="nm">A Person</span><span class="via living">living</span></div>'
                '<a class="node spouse is-living" href="/people/p/"><span class="mar">married</span><span class="nm">B Person</span></a></div></div>'
                '<figcaption></figcaption></figure>')
LIVING_BODY = ('<p class="pliving">' + SENTENCE + '</p><p class="pplace">Testville, Nowhere</p>'
               '<section class="psec" id="family"><h2 class="psec-h">Family</h2>{chart}</section>'
               '<p class="pfoot small"><a href="/people/">← All the people</a></p>')


def page(h1="<h1>A Person</h1>", body=None, chart=CHART, head="", attrs='data-person-page="1" data-living="0"', ld=LD_PERSON):
    body = SECTIONS.format(chart=chart) if body is None else body
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>x</title>{head}{ld}</head>'
            f'<body><main><article class="ppage" {attrs}>{h1}{body}</article></main></body></html>')


def living(**k):
    """a correct living page, with ONE thing changed"""
    kw = dict(h1="<h1>A Person</h1>", body=LIVING_BODY.format(chart=LIVING_CHART), head=NOINDEX,
              attrs='data-person-page="1" data-living="1"', ld="")
    kw.update(k)
    return page(**kw)


def build(pages, sitemap=None):
    d = tempfile.mkdtemp(prefix="checkperson-")
    for slug, h in pages.items():
        p = os.path.join(d, "people", slug)
        os.makedirs(p)
        open(os.path.join(p, "index.html"), "w", encoding="utf-8").write(h)
    if sitemap:
        open(os.path.join(d, "sitemap.xml"), "w").write("".join(f"<url><loc>https://x.test{u}</loc></url>" for u in sitemap))
    return d


def run(pages, **kw):
    sm = kw.pop("sitemap", None)
    d = build(pages, sm)
    try:
        smx = checkperson.load_sitemap(os.path.join(d, "sitemap.xml")) if sm else None
        res = checkperson.audit(d, "/people/", sitemap=smx, **kw)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return res


def cats(res, sev="FAIL"):
    return sorted({c for _, c, s, _ in res["findings"] if s == sev})


def msgs(res, sev="FAIL"):
    return [m for _, _, s, m in res["findings"] if s == sev]


def one(name, h, want, sev="FAIL", **kw):
    """plant one departure, expect exactly that category (and nothing else at that severity)"""
    r = run({"p": h}, **kw)
    expect(name, cats(r, sev) == [want], f"got {cats(r, sev)} want [{want}]  {msgs(r, sev)[:3]}")


# =============================== the clean controls: what makes every other case mean something
r = run({"p": page()}, require_jsonld=True)
expect("control: a clean canonical page raises nothing", r["findings"] == [] and r["pages"] == 1 and r["canonical"] == 1, str(r["findings"]))
r = run({"p": living()})
expect("control: a clean living page raises nothing", r["findings"] == [] and r["living"] == 1, str(r["findings"]))
r = run({"p": living()}, sitemap=["/people/other/"])
expect("control: a clean living page is quiet when the sitemap does not list it", r["findings"] == [], str(r["findings"]))

# =============================== (a) a living page shows name, relationships, town and country, nothing else
print("  -- (a) a living page shows nothing beyond name, relationships, town and country")
one("living: not noindex", living(head=""), "living")
one("living: a photograph", living(body=LIVING_BODY.format(chart=LIVING_CHART) + '<img src="/me.jpg" alt="x">'), "living")
one("living: a year (1799) in the body", living(body=LIVING_BODY.format(chart=LIVING_CHART).replace("Testville, Nowhere", "Testville, Nowhere 1799")), "living")
one("living: text that is none of name, relationships, place (an occupation)", living(body=LIVING_BODY.format(chart=LIVING_CHART) + "<p>A cooper.</p>"), "living")
one("living: a record section beyond Family",
    living(body=LIVING_BODY.format(chart=LIVING_CHART) + '<section class="psec" id="record"><h2 class="psec-h">What the record says</h2></section>'), "living")
one("living: a sources section, even with nothing in it",
    living(body=LIVING_BODY.format(chart=LIVING_CHART) + '<section class="psec" id="sources"><h2 class="psec-h">Where this comes from</h2></section>'), "living")
one("living: a table", living(body=LIVING_BODY.format(chart=LIVING_CHART) + "<table><tr><td></td></tr></table>"), "living")
one("living: a <time> element", living(body=LIVING_BODY.format(chart=LIVING_CHART) + '<time datetime="1799"></time>'), "living")
one("living: a date on their own chart node", living(body=LIVING_BODY.format(chart=LIVING_CHART.replace('<span class="via living">living</span>', '<span class="dt">1799–1860</span><span class="via living">living</span>'))), "living")
one("living: a source word under their own node",
    living(body=LIVING_BODY.format(chart=LIVING_CHART.replace('<span class="via living">living</span>', '<span class="via">a record read here</span>'))), "living")
one("living: a living relative drawn with a date",
    living(body=LIVING_BODY.format(chart=LIVING_CHART.replace('<span class="nm">B Person</span>', '<span class="nm">B Person</span><span class="dt">1799–</span>'))), "living")
one("living: a living relative drawn with a source word",
    living(body=LIVING_BODY.format(chart=LIVING_CHART.replace('<span class="nm">B Person</span>', '<span class="nm">B Person</span><span class="via">a record read here</span>'))), "living")
one("living: a place that is a street address",
    living(body=LIVING_BODY.format(chart=LIVING_CHART).replace("Testville, Nowhere", "Testville Street, Testville, Nowhere")), "living")
one("living: a place that is an institution",
    living(body=LIVING_BODY.format(chart=LIVING_CHART).replace("Testville, Nowhere", "Testville Hospital, Testville, Nowhere")), "living")
one("living: Person structured data (planted birth 1799)",
    living(ld='<script type="application/ld+json">{"@graph":[{"@type":"Person","birthDate":"1799"}]}</script>'), "living")
one("living: a Person with no dates in it is still structured data",
    living(ld='<script type="application/ld+json">{"@graph":[{"@type":"Person","name":"A Person"}]}</script>'), "living")
r = run({"p": living()}, sitemap=["/people/p/"])
expect("living: listed in the sitemap", cats(r) == ["living"] and any("sitemap" in m for m in msgs(r)), str(r["findings"]))
r = run({"p": page(head="", attrs='data-person-page="1" data-living="0"', ld="", body=SECTIONS.format(chart=CHART))}, living_urls={"/people/p/"})
expect("living: flagged by the archive's own list (computed from living_rule.py) but indexable", any("not noindex" in m for m in msgs(r)), str(r["findings"]))
r = run({"p": living(body=LIVING_BODY.format(chart=LIVING_CHART).replace("Testville, Nowhere", "1799 Test Street, Testville"))})
expect("living: an address-like place is ALSO named as a place fault", any("address" in m for m in msgs(r)), str(msgs(r)))
r = run({"p": living(attrs='data-person-page="1" data-living="1" data-place-refused="1"')})
expect("living: a place the component refused is advisory, not a FAIL", cats(r) == [] and cats(r, "warn") == ["living"], str(r["findings"]))
r = run({"p": page(body=SECTIONS.format(chart=CHART).replace("Born at home.", "Born in 1799."), head=NOINDEX, attrs="", ld="")})
expect("a noindex page is NOT assumed living (a dead person with a living relative drawn is noindexed too)", "living" not in cats(r), str(r["findings"]))
r = run({"p": page(chart=CHART.replace("1799–1860", "1799–1860"), head="", ld="")})
expect("a dead person's dates are NOT a leak", "living" not in cats(r))
leg_living = ('<!doctype html><html lang="en"><head><title>x</title>' + NOINDEX + '</head><body><main><h1>Name</h1>'
              '<p>Born in 1799.</p><figure class="ptree"></figure></main></body></html>')
r = run({"p": leg_living}, living_urls={"/people/p/"})
expect("a LEGACY page the archive's list names as living is held to the living rules", "living" in cats(r), str(r["findings"]))
r = run({"p": leg_living.replace("<p>Born in 1799.</p>", "")}, living_urls={"/people/p/"})
expect("a legacy living page with nothing to find is quiet", cats(r) == [], str(r["findings"]))

# a dead person's page keeps its sections: the living-only restriction must not leak onto it
one("a dead person's page still needs its required sections", page(body='<section class="psec" id="family"><h2>Family</h2>' + CHART + '</section>'), "sections")
r = run({"p": living(body=LIVING_BODY.format(chart=LIVING_CHART))})
expect("a living page does NOT need Record or Sources sections", "sections" not in cats(r))

# =============================== (b) every person the archive names has a page
print("  -- (b) a named person has a page")
NODE_PLAIN = '<div class="node via-read"><span class="nm">C Person</span><span class="dt">1760–1799</span></div>'
with_node = lambda node: page(chart=CHART.replace("</div></div></div></figure>", "</div>" + node + "</div></div></figure>"))
one("nopage: a chart node that names a person and links nowhere", with_node(NODE_PLAIN), "nopage")
one("nopage: a link to a person page that is not in the build",
    with_node('<a class="node via-read" href="/people/ghost/"><span class="nm">C Person</span></a>'), "nopage")
r = run({"p": with_node('<a class="node via-read" href="/people/p/"><span class="nm">C Person</span></a>')})
expect("control: a chart node that links to a page in the build is quiet", cats(r) == [] and cats(r, "warn") == [], str(r["findings"]))
r = run({"p": with_node('<a class="node via-read" href="/people/old/#x"><span class="nm">C Person</span></a>'), "old": '<html><head><meta http-equiv="refresh" content="0;url=/people/p/"></head></html>'})
expect("control: a link to a redirect page resolves (it exists)", cats(r) == [], str(r["findings"]))
r = run({"p": with_node('<div class="node ambiguous"><span class="nm">Several people of this name</span></div>')})
expect("nopage: an ambiguous relative is advisory, not a FAIL", cats(r) == [] and cats(r, "warn") == ["nopage"], str(r["findings"]))
r = run({"p": page(chart=CHART.replace("</figure>", '<figcaption><p class="omit"><span class="omit-r"><span class="nm">D Person</span></span></p></figcaption></figure>'))})
expect("nopage: a name in the «not drawn» list is advisory", cats(r) == [] and cats(r, "warn") == ["nopage"], str(r["findings"]))
r = run({"p": with_node('<div class="node gap"><span class="nm">— withheld —</span></div>')})
expect("a dashed placeholder (the old 'living, withheld' node) is not a named person", "nopage" not in cats(r))
r = run({"p": page(body=SECTIONS.format(chart=CHART) + '<p><a href="/people/">all</a></p>')})
expect("a link to the people index itself is not a person link", "nopage" not in cats(r))

# =============================== (c) an h1 never carries a qualifier longer than the name
print("  -- (c) an h1 with a qualifier longer than the name")
one("h1: a qualifier longer than the name", page(h1="<h1>Al (m. Beatrice Testova the younger, 1799)</h1>"), "h1")
r = run({"p": page(h1="<h1>Anna Testova (the elder)</h1>")})
expect("h1: a short qualifier is not this fault", "h1" not in cats(r), str(r["findings"]))
r = run({"p": page(h1="<h1>Anna Testova</h1>")})
expect("h1: a plain name is quiet", cats(r) == [], str(r["findings"]))

# =============================== the earlier rules
print("  -- the page and the chart")
one("two h1 elements", page(h1="<h1>A</h1><h1>B</h1>"), "h1")
one("no h1", page(h1=""), "h1")
one("headings out of order",
    page(body='<section class="psec" id="record"><h2>What the record says</h2></section><section class="psec" id="family"><h2>Family</h2>' + CHART + '</section>'
              '<section class="psec" id="sources"><h2>Where this comes from</h2></section>'), "sections")
one("a section wears the wrong heading",
    page(body='<section class="psec" id="family"><h2>Family</h2>' + CHART + '</section><section class="psec" id="record"><h2>What the registers say</h2></section>'
              '<section class="psec" id="sources"><h2>Where this comes from</h2></section>'), "sections")
one("no chart and no sentence saying why", page(chart=""), "chart")
r = run({"p": page(chart='<figure class="ptree"></figure>')})
expect("an empty chart is still a chart", "chart" not in cats(r))
r = run({"p": page(chart='<p class="pempty">This chart is empty.</p>')})
expect("an empty chart that says why is accepted", "chart" not in cats(r))


def with_dt(txt):
    return page(chart=CHART.replace("1799–1860", txt))


for label, dt in [("an ISO date", "b. 1799-10-01"), ("a month-first date", "b. Dec 13 1799"), ("a single date with no label", "13 Dec 1799"),
                  ("a single year with no label", "1799"), ("a spaced range", "1799 – 1860"), ("a hyphen range", "1799-1860")]:
    one(f"chart date: {label}", with_dt(dt), "dates")
for label, dt in [("a labelled full date", "b. 13 Dec 1799"), ("a year range with an en dash", "1799–1860"), ("circa", "b. c. 1799"), ("an open range", "1799–")]:
    r = run({"p": with_dt(dt)})
    expect(f"chart date accepted: {label}", "dates" not in cats(r), str(r["findings"]))

print("  -- evidence: two axes (ruling 3)")
SEC = SECTIONS.format(chart=CHART)
one("a grade chip reading «Ungraded»", page(body=SEC.replace("Born at home.", '<span class="ev ev-ungraded">Ungraded</span>')), "evidence")
one("a grade chip that is not one of the five", page(body=SEC.replace("Born at home.", '<span class="ev ev-candidate">Candidate</span>')), "evidence")
r = run({"p": page(body=SEC.replace("Born at home.", '<span class="ev ev-documented">Documented</span>'))})
expect("a grade chip that is one of the five is accepted", "evidence" not in cats(r))
CHIP = '<span class="pchip">{inner}</span>'
one("a grade drawn beside an index entry (it stays ungraded)",
    page(body=SEC.replace("Born at home.", CHIP.format(inner='<span class="ev ev-documented">Documented</span><span class="pv via-indexed">an index entry, not read</span>'))), "evidence")
one("a grade drawn beside an image held (it stays ungraded)",
    page(body=SEC.replace("Born at home.", CHIP.format(inner='<span class="ev ev-family">Family</span><span class="pv via-scanned">image held, not yet read</span>'))), "evidence")
r = run({"p": page(body=SEC.replace("Born at home.", CHIP.format(inner='<span class="pv via-indexed">an index entry, not read</span>')))})
expect("control: an index entry on its own, ungraded, is accepted", r["findings"] == [], str(r["findings"]))
r = run({"p": page(body=SEC.replace("Born at home.", CHIP.format(inner='<span class="ev ev-documented">Documented</span><span class="pv via-read">a record read here</span><span class="pv is-line">direct line</span>')))})
expect("control: a grade beside a record read, with the direct line as its own word, is accepted", r["findings"] == [], str(r["findings"]))
one("a chip source word the component did not recognise",
    page(body=SEC.replace("Born at home.", CHIP.format(inner='<span class="pv via-unmarked">unmarked: source word not recognised (“strong”)</span>'))), "source")
one("a source word the chart did not recognise", page(chart=CHART.replace("</div></div></div>", '<span class="via">unmarked: source word not recognised (“strong”)</span></div></div></div>')), "source")
r = run({"p": page(chart=CHART.replace("</div></div></div>", '<span class="via">Testimony</span></div></div></div>'))})
expect("a legacy source word is advisory, not a FAIL", cats(r, "warn") == ["source"] and cats(r) == [], str(r["findings"]))
for w in ["a record read here", "an index entry, not read", "image held, not yet read", "family tree, unverified", "inferred", "disputed", "named here only"]:
    r = run({"p": page(chart=CHART.replace("</div></div></div>", f'<span class="via">{w}</span></div></div></div>'))})
    expect(f"each of the seven source words is accepted: {w}", r["findings"] == [], str(r["findings"]))

print("  -- images, names, structured data")
one("an image with no alt text", page(body=SEC + '<figure><img src="/p.jpg"><figcaption>c</figcaption></figure>'), "images")
r = run({"p": page(body=SEC + '<img src="/p.jpg" alt="a portrait">')})
expect("an image outside a figure is advisory", cats(r, "warn") == ["images"] and cats(r) == [], str(r["findings"]))
r = run({"p": page(body=SEC + '<figure><img src="/p.jpg" alt="a portrait"><figcaption>c</figcaption></figure>')})
expect("an image with alt, a figure and a caption is accepted", r["findings"] == [], str(r["findings"]))
r = run({"p": page(body=SEC + '<img id="lb-img" src="" alt="">')})
expect("the empty lightbox image is not a photograph", r["findings"] == [], str(r["findings"]))
r = run({"p": page(h1="<h1>Severa FERNANDEZ</h1>")})
expect("an ALL-CAPS surname is advisory", cats(r, "warn") == ["names"] and cats(r) == [])
r = run({"p": page(h1="<h1>" + "A very long name " * 5 + "</h1>")})
expect("an h1 over 60 characters is advisory", cats(r, "warn") == ["names"])
one("no Person structured data when asked for", page(ld=""), "jsonld", require_jsonld=True)
r = run({"p": page(ld="")})
expect("no Person structured data is fine when not asked for", "jsonld" not in cats(r))

print("  -- legacy pages, redirects")
leg = ('<!doctype html><html lang="en"><head><title>x</title></head><body><main><h1>Name</h1><h2>The Record</h2>' + CHART + '<h2>Household</h2></main></body></html>')
r = run({"p": leg})
expect("a legacy page is counted as legacy", r["canonical"] == 0 and r["pages"] == 1)
expect("legacy headings are advisory, not a FAIL", cats(r, "warn") == ["sections"] and cats(r) == [], str(r["findings"]))
red = '<html><head><meta http-equiv="refresh" content="0;url=/people/p/"></head><body></body></html>'
r = run({"p": page(), "old": red})
expect("a redirect page is skipped, not judged", r["pages"] == 1 and r["redirects"] == 1)

# =============================== an empty build is refused: zero pages examined is not a pass
print("  -- an empty build is refused")
d = tempfile.mkdtemp(prefix="checkperson-")
try:
    q = ["--dist", d, "--people", "/people/"]
    expect("no people directory: exit 2", checkperson.main(q) == 2)
    os.makedirs(os.path.join(d, "people"))
    expect("an empty people directory: exit 2", checkperson.main(q) == 2)
    expect("an empty people directory with --strict: still exit 2, not 0", checkperson.main(q + ["--strict"]) == 2)
    expect("an empty people directory with --max 99: still exit 2", checkperson.main(q + ["--max", "99"]) == 2)
    expect("--min-pages 0 cannot be used to wave an empty build through", checkperson.main(q + ["--min-pages", "0"]) == 2)
    os.makedirs(os.path.join(d, "people", "old"))
    open(os.path.join(d, "people", "old", "index.html"), "w").write(red)
    expect("a directory of only redirect pages examined nothing: exit 2", checkperson.main(q) == 2)
    os.makedirs(os.path.join(d, "people", "p"))
    open(os.path.join(d, "people", "p", "index.html"), "w").write(page())
    expect("control: one real page beside the redirect is examined: exit 0", checkperson.main(q + ["--quiet"]) == 0)
    expect("--min-pages 3 with one page: exit 2", checkperson.main(q + ["--min-pages", "3"]) == 2)
finally:
    shutil.rmtree(d, ignore_errors=True)

# =============================== exit codes: advisory by default, --strict, --max
print("  -- advisory by default, --strict, --max")
d = build({"bad": page(h1="<h1>A</h1><h1>B</h1>"), "ok": page()})
try:
    q = ["--dist", d, "--people", "/people/", "--quiet"]
    expect("advisory mode exits 0 with a FAIL present", checkperson.main(q) == 0)
    expect("--strict exits 1 on a FAIL", checkperson.main(q + ["--strict"]) == 1)
    expect("--max 1 holds a backlog of one", checkperson.main(q + ["--max", "1"]) == 0)
    expect("--max 0 fails when the count is above it", checkperson.main(q + ["--max", "0"]) == 1)
finally:
    shutil.rmtree(d, ignore_errors=True)
d = build({"ok": page()})
try:
    expect("--strict exits 0 on a clean build", checkperson.main(["--dist", d, "--people", "/people/", "--quiet", "--strict"]) == 0)
finally:
    shutil.rmtree(d, ignore_errors=True)

print(f"  {cases} cases: " + ("all behave" if not fails else f"{fails} failed"))
sys.exit(1 if fails else 0)
