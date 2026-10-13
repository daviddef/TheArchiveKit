#!/usr/bin/env python3
"""Can checkperson.py still fail?

A people-page check that reports «ok» on a page it cannot read is worse than no
check, and this one has a lot of ways to say nothing: it reads HTML with the
standard library, it recognises a page by a class, it decides a person is living
from three different signals. So every rule below is proved the one way that
counts: plant ONE departure in an otherwise clean page and see the checker name
exactly that departure, and plant the clean page and see it stay quiet.

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


def expect(name, cond, detail=""):
    global fails
    if cond:
        print(f"  ok    {name}")
    else:
        fails += 1
        print(f"  FAIL  {name}{('  ' + detail) if detail else ''}")


CHART = '<figure class="ptree"><div class="tier self"><div class="row"><div class="node me"><span class="nm">A Person</span><span class="dt">1854–1920</span></div></div></div></figure>'
SECTIONS = ('<section class="psec" id="family"><h2>Family</h2>{chart}</section>'
            '<section class="psec" id="record"><h2>What the record says</h2><p>Born at home.</p></section>'
            '<section class="psec" id="sources"><h2>Where this comes from</h2><p>A register.</p></section>')
LD_PERSON = '<script type="application/ld+json">{"@graph":[{"@type":"Person","name":"A Person"}]}</script>'


def page(h1="<h1>A Person</h1>", body=None, chart=CHART, head="", attrs='data-person-page="1" data-living="0"', ld=LD_PERSON):
    body = SECTIONS.format(chart=chart) if body is None else body
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>x</title>{head}{ld}</head>'
            f'<body><main><article class="ppage" {attrs}>{h1}{body}</article></main></body></html>')


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


def one(name, h, want, sev="FAIL", **kw):
    """plant one departure, expect exactly that category (and nothing else at that severity)"""
    r = run({"p": h}, **kw)
    expect(name, cats(r, sev) == [want], f"got {cats(r, sev)} want [{want}]  {[m for _, c, s, m in r['findings']][:3]}")


NOINDEX = '<meta name="robots" content="noindex">'

# ---- the clean page stays quiet (the control that makes every other case mean something)
r = run({"p": page()}, require_jsonld=True)
expect("a clean canonical page raises nothing", r["findings"] == [] and r["pages"] == 1 and r["canonical"] == 1, str(r["findings"]))

# ---- one departure each
one("two h1 elements", page(h1="<h1>A</h1><h1>B</h1>"), "h1")
one("no h1", page(h1=""), "h1")
one("headings out of order",
    page(body='<section class="psec" id="record"><h2>What the record says</h2></section><section class="psec" id="family"><h2>Family</h2>' + CHART + '</section>'
              '<section class="psec" id="sources"><h2>Where this comes from</h2></section>'), "sections")
one("a required section is missing", page(body='<section class="psec" id="family"><h2>Family</h2>' + CHART + '</section>'), "sections")
one("a section wears the wrong heading",
    page(body='<section class="psec" id="family"><h2>Family</h2>' + CHART + '</section><section class="psec" id="record"><h2>What the registers say</h2></section>'
              '<section class="psec" id="sources"><h2>Where this comes from</h2></section>'), "sections")
one("no chart and no sentence saying why", page(chart=""), "chart")
r = run({"p": page(chart='<figure class="ptree"></figure>')})
expect("an empty chart is still a chart", "chart" not in cats(r))
r = run({"p": page(chart='<p class="pempty">This chart is empty.</p>')})
expect("an empty chart that says why is accepted", "chart" not in cats(r))


def with_dt(txt):
    return page(chart=CHART.replace("1854–1920", txt))


for label, dt in [("an ISO date", "b. 1876-10-01"), ("a month-first date", "b. Dec 13 1854"), ("a single date with no label", "13 Dec 1854"),
                  ("a single year with no label", "1854"), ("a spaced range", "1813 – 1876"), ("a hyphen range", "1813-1876")]:
    one(f"chart date: {label}", with_dt(dt), "dates")
for label, dt in [("a labelled full date", "b. 13 Dec 1854"), ("a year range with an en dash", "1813–1876"), ("circa", "b. c. 1854"), ("an open range", "1854–")]:
    r = run({"p": with_dt(dt)})
    expect(f"chart date accepted: {label}", "dates" not in cats(r), str(r["findings"]))
one("a grade chip reading «Ungraded»", page(body=SECTIONS.format(chart=CHART).replace("Born at home.", '<span class="ev ev-ungraded">Ungraded</span>')), "evidence")
one("a grade chip that is not one of the five", page(body=SECTIONS.format(chart=CHART).replace("Born at home.", '<span class="ev ev-candidate">Candidate</span>')), "evidence")
r = run({"p": page(body=SECTIONS.format(chart=CHART).replace("Born at home.", '<span class="ev ev-documented">Documented</span>'))})
expect("a grade chip that is one of the five is accepted", "evidence" not in cats(r))
one("a source word the component did not recognise", page(chart=CHART.replace("</div></div></div>", '<span class="via">unmarked: source word not recognised (“strong”)</span></div></div></div>')), "source")
r = run({"p": page(chart=CHART.replace("</div></div></div>", '<span class="via">Testimony</span></div></div></div>'))})
expect("a legacy source word is advisory, not a FAIL", cats(r, "warn") == ["source"] and cats(r) == [], str(r["findings"]))
one("an image with no alt text", page(body=SECTIONS.format(chart=CHART) + '<figure><img src="/p.jpg"><figcaption>c</figcaption></figure>'), "images")
r = run({"p": page(body=SECTIONS.format(chart=CHART) + '<img src="/p.jpg" alt="a portrait">')})
expect("an image outside a figure is advisory", cats(r, "warn") == ["images"] and cats(r) == [], str(r["findings"]))
r = run({"p": page(body=SECTIONS.format(chart=CHART) + '<figure><img src="/p.jpg" alt="a portrait"><figcaption>c</figcaption></figure>')})
expect("an image with alt, a figure and a caption is accepted", r["findings"] == [], str(r["findings"]))
r = run({"p": page(body=SECTIONS.format(chart=CHART) + '<img id="lb-img" src="" alt="">')})
expect("the empty lightbox image is not a photograph", r["findings"] == [], str(r["findings"]))
r = run({"p": page(h1="<h1>Severa FERNANDEZ</h1>")})
expect("an ALL-CAPS surname is advisory", cats(r, "warn") == ["names"] and cats(r) == [])
r = run({"p": page(h1="<h1>" + "A very long name " * 5 + "</h1>")})
expect("an h1 over 60 characters is advisory", cats(r, "warn") == ["names"])
one("no Person structured data when asked for", page(ld=""), "jsonld", require_jsonld=True)
r = run({"p": page(ld="")})
expect("no Person structured data is fine when not asked for", "jsonld" not in cats(r))

# ---- living: each leak on its own, on an otherwise correct living page
LIVING = dict(head=NOINDEX, attrs='data-person-page="1" data-living="1"', ld="")
nodate = CHART.replace('<span class="dt">1854\u20131920</span>', "")


def living_page(**k):
    """a correct living page (no date on the node), with ONE thing changed"""
    kw = dict(LIVING, chart=nodate)
    kw.update(k)
    return page(**kw)


good = run({"p": living_page()})
expect("a correct living page raises nothing", good["findings"] == [], str(good["findings"]))
expect("a living page is counted as living", good["living"] == 1)
one("living: not noindex", living_page(head=""), "living")
one("living: a photograph", living_page(body=SECTIONS.format(chart=nodate).replace("Born at home.", '<img src="/me.jpg" alt="x">')), "living")
one("living: a year in the body", living_page(body=SECTIONS.format(chart=nodate).replace("Born at home.", "Born in 1985.")), "living")
one("living: a date on their own chart node", living_page(chart=CHART), "living")      # CHART's self node carries a dt
one("living: birth data in JSON-LD", page(head=NOINDEX, attrs='data-person-page="1" data-living="1"', chart=CHART.replace('<span class="dt">1854–1920</span>', ""),
                                         ld='<script type="application/ld+json">{"@graph":[{"@type":"Person","birthDate":"1985"}]}</script>'), "living")
nodate = CHART.replace('<span class="dt">1854–1920</span>', "")
r = run({"p": page(chart=nodate, **LIVING)}, sitemap=["/people/p/"])
expect("living: listed in the sitemap", cats(r) == ["living"] and any("sitemap" in m for _, _, _, m in r["findings"]), str(r["findings"]))
r = run({"p": page(chart=nodate + "", head="", attrs='data-person-page="1" data-living="0"', ld="")}, living_urls={"/people/p/"})
expect("living: flagged by the archive's own list but indexable", any("not noindex" in m for _, _, _, m in r["findings"]), str(r["findings"]))
r = run({"p": page(chart=CHART.replace("1854–1920", "1854–1920"), head="", ld="")})
expect("a dead person's dates are NOT a leak", "living" not in cats(r))
r = run({"p": page(body=SECTIONS.format(chart=CHART).replace("Born at home.", "Born in 1985."), head=NOINDEX, attrs="", ld="")})
expect("a noindex page is NOT assumed living (a dead person with a living relative drawn is noindexed too)", "living" not in cats(r), str(r["findings"]))
r = run({"p": page(body=SECTIONS.format(chart=nodate).replace("Born at home.", "Born in 1985."), head=NOINDEX, attrs="", ld="")}, living_urls={"/people/p/"})
expect("a legacy page the archive's list names as living is held to the living rules", "living" in cats(r), str(r["findings"]))

# ---- legacy pages: held to what can be said of any people page
leg = '<!doctype html><html lang="en"><head><title>x</title></head><body><main><h1>Name</h1><h2>The Record</h2>' + CHART + '<h2>Household</h2></main></body></html>'
r = run({"p": leg})
expect("a legacy page is counted as legacy", r["canonical"] == 0 and r["pages"] == 1)
expect("legacy headings are advisory, not a FAIL", cats(r, "warn") == ["sections"] and cats(r) == [], str(r["findings"]))
red = '<html><head><meta http-equiv="refresh" content="0;url=/people/p/"></head><body></body></html>'
r = run({"p": page(), "old": red})
expect("a redirect page is skipped, not judged", r["pages"] == 1 and r["redirects"] == 1)

# ---- could not see: that is not a pass
d = tempfile.mkdtemp(prefix="checkperson-")
try:
    expect("no people directory: exit 2", checkperson.main(["--dist", d, "--people", "/people/"]) == 2)
    os.makedirs(os.path.join(d, "people"))
    expect("an empty people directory: exit 2", checkperson.main(["--dist", d, "--people", "/people/"]) == 2)
finally:
    shutil.rmtree(d, ignore_errors=True)

# ---- exit codes: advisory 0, strict 1, ratchet
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

print("  all cases behave" if not fails else f"  {fails} failed")
sys.exit(1 if fails else 0)
