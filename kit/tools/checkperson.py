#!/usr/bin/env python3
"""Does this archive's BUILT people pages say what the estate means by a people page?

Eight archives draw a person eight ways: eight sets of section names, three date
styles in one chart, six words for one source, a living person's page that is
indexable in two of them. PERSON-PAGE-SPEC.md says what one page is; kit/lib/
person.js and the PersonPage component make it cheap to be that page; THIS reads
what a reader is actually handed and says where it is not.

IT READS THE BUILD, NOT THE TEMPLATE. A people page is whatever the browser gets.
A check of the template grades the intention, and the whole finding behind this
tool is that seven templates intended the same thing. It opens every
`<dist>/<people>/<slug>/index.html` (ARCHIVE_OUT beats --dist, as everywhere in
this kit: see outdir.py) and reads the HTML with the standard library only.

IT WORKS ON A PAGE THAT HAS NOT BEEN MIGRATED. Pages built with PersonPage carry
`data-person-page`; those are held to the whole spec (section order, headings,
ids). Every other person page is LEGACY: it is held only to what can be said of
any people page, whatever drew it. The report counts both, because «0 FAIL» on a
build where 0 of 1,961 pages use the component is not the same sentence as «0
FAIL» on a build where all of them do.

WHAT IT CHECKS, each as a named category
  h1        exactly one
  sections  (canonical pages) the six headings, in order, none misspelt; the first
            three present; anything else is counted as local, not failed
  chart     a family chart is drawn, or the page says why not (.pempty)
  living    a page that says it is living (data-living=1) or is listed in
            --living-urls (from the archive's own data; noindex alone does not make
            a page living, since a dead person is noindexed when a living relative
            is drawn on it): noindex, no photograph, no date on the
            person's own node, no year in the body outside a chart, not in the
            sitemap, no birth or death data in JSON-LD
  dates     every chart date is «b. 1854», «d. 1920», «1854–1920», «13 Dec 1854»
            with a label, «c. 1854»; never ISO, never month-first, never a single
            date with no label (Falco's chart dates were the date of the act that
            named someone, unlabelled, and read as births)
  evidence  every grade chip is one of the five words; «Ungraded» is a FAIL
  source    every word under a chart node is a canonical source word
            (advisory: legacy archives use their own, and this counts which)
  images    alt text present; inside a figure; with a caption
  names     (advisory) no ALL-CAPS surname, no h1 longer than 60 characters
  jsonld    (--require-jsonld) a Person for everyone not living; none carrying a
            birth date for anyone living

ADVISORY BY DEFAULT. It reports and exits 0, because no archive meets the spec
yet and a gate that fails everywhere is a gate that gets removed. `--strict` exits
1 on any FAIL. `--max N` is the ratchet: exit 1 only when the FAIL count rises
above N, so a backlog can be held where it is while it is paid down. It exits 2,
in either mode, when it could not SEE a people page at all: a check that finds
nothing because it looked in the wrong place has not found that nothing is wrong
(no dist, or fewer than --min-pages people pages).

  python3 checkperson.py --dist dist --people /people/
  python3 checkperson.py --dist dist --people /person/ --living-urls living.txt --sitemap dist/sitemap.xml --strict
"""

import argparse
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outdir  # noqa: E402

SECTIONS = [("family", "Family"), ("record", "What the record says"), ("sources", "Where this comes from"),
            ("namesakes", "Others of the same name"), ("media", "Photographs and papers"), ("notes", "Notes and corrections")]
HEADINGS = [h for _, h in SECTIONS]
REQUIRED = HEADINGS[:3]
GRADES = {"Documented", "Probable", "Inferred", "Family", "Disputed"}
SOURCE_WORDS = {"a record read here", "an index entry, not read", "image held, not yet read", "family tree, unverified",
                "inferred", "disputed", "named here only"}
MON = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
DT_OK = [
    re.compile(r"^(?:b|d|bapt|m|fl)\. (?:c\. )?(?:\d{1,2} (?:%s) )?\d{4}$" % MON),     # a labelled single date
    re.compile(r"^(?:c\. )?\d{4}–(?:c\. )?\d{4}$"),                                  # a year range, en dash, no spaces
    re.compile(r"^(?:c\. )?\d{4}–$"),                                                # born, no death known (open range)
]
YEAR = re.compile(r"\b(1[5-9][0-9]{2}|20[0-9]{2})\b")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Node:
    __slots__ = ("tag", "attrs", "kids", "text", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.kids, self.text, self.parent = tag, dict(attrs), [], [], parent

    def cls(self):
        return (self.attrs.get("class") or "").split()

    def walk(self):
        yield self
        for k in self.kids:
            yield from k.walk()

    def content(self):
        out = []
        for t in self.text_nodes():
            out.append(t)
        return re.sub(r"\s+", " ", "".join(out)).strip()

    def text_nodes(self):
        for item in self.text:
            if isinstance(item, str):
                yield item
            else:
                yield from item.text_nodes()


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", [], None)
        self.cur = self.root
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        self.cur.text.append(n)
        if tag not in VOID:
            self.cur = n
            if tag in ("script", "style"):
                self._skip += 1

    def handle_startendtag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        self.cur.text.append(n)

    def handle_endtag(self, tag):
        c = self.cur
        while c is not None and c.tag != tag:
            c = c.parent
        if c is not None and c.parent is not None:
            if tag in ("script", "style"):
                self._skip = max(0, self._skip - 1)
            self.cur = c.parent

    def handle_data(self, data):
        if self._skip == 0:
            self.cur.text.append(data)
        else:
            self.cur.text.append("")
            self.cur.attrs["_script"] = self.cur.attrs.get("_script", "") + data


def parse(path):
    t = Tree()
    with open(path, encoding="utf-8", errors="replace") as f:
        t.feed(f.read())
    return t.root


def find(root, tag=None, cls=None):
    for n in root.walk():
        if tag and n.tag != tag:
            continue
        if cls and cls not in n.cls():
            continue
        yield n


def under(n, cls):
    p = n.parent
    while p is not None:
        if cls in p.cls():
            return True
        p = p.parent
    return False


def audit_page(root, rel_url, living_urls, sitemap, require_jsonld):
    """-> (kinds_of_page, [(category, severity, message)])"""
    out = []
    main = next(find(root, "main"), None) or root
    art = next((n for n in find(main) if "data-person-page" in n.attrs), None)
    canonical = art is not None
    robots = " ".join((m.attrs.get("content") or "") for m in find(root, "meta") if (m.attrs.get("name") or "").lower() == "robots").lower()
    noindex = "noindex" in robots
    flagged_living = (art is not None and art.attrs.get("data-living") == "1")
    # noindex alone does NOT make a person living: Falco noindexes 24 dead people because a living relative is
    # drawn on their page. Living is what the page declares (data-living=1) or the archive's own list says.
    living = flagged_living or rel_url in living_urls

    h1s = list(find(root, "h1"))
    if len(h1s) != 1:
        out.append(("h1", "FAIL", f"{len(h1s)} h1 elements"))
    else:
        t = h1s[0].content()
        if len(t) > 60:
            out.append(("names", "warn", f"h1 is {len(t)} characters; a qualifier belongs in a line under the heading: {t[:50]}…"))
        if re.search(r"\b[A-ZÀ-Þ]{3,}\b", t):
            out.append(("names", "warn", f"ALL-CAPS token in the h1: {t[:50]}"))

    h2s = [h.content() for h in find(main, "h2")]
    if canonical:
        order = [HEADINGS.index(h) for h in h2s if h in HEADINGS]
        if order != sorted(order):
            out.append(("sections", "FAIL", "canonical headings out of order: " + " > ".join(h2s)))
        for r in REQUIRED:
            if r not in h2s:
                out.append(("sections", "FAIL", f"required section missing: {r}"))
        for sec in find(art, "section"):
            if "psec" in sec.cls() and "psec-local" not in sec.cls():
                h = next(find(sec, "h2"), None)
                want = dict(SECTIONS).get(sec.attrs.get("id"))
                if h is not None and want and h.content() != want:
                    out.append(("sections", "FAIL", f"#{sec.attrs.get('id')} is headed '{h.content()}', not '{want}'"))
    else:
        odd = [h for h in h2s if h not in HEADINGS]
        if odd:
            out.append(("sections", "warn", f"{len(odd)} of {len(h2s)} h2 are not a spec heading, e.g. '{odd[0][:40]}'"))

    charts = [f for f in find(main, "figure") if "ptree" in f.cls()]
    if not charts and not list(find(main, None, "pempty")):
        out.append(("chart", "FAIL", "no family chart, and no sentence saying why not"))

    for dt in find(main, "span", "dt"):
        txt = dt.content()
        if not txt:
            continue
        if not any(rx.match(txt) for rx in DT_OK):
            why = ("ISO date" if re.search(r"\d{4}-\d{2}-\d{2}|\d{4}-[A-Za-z]{3}-\d", txt)
                   else "month-first date" if re.search(r"(%s)[a-z]* \d{1,2}[ ,]" % MON, txt)
                   else "single date with no label" if re.match(r"^(?:c\. )?(?:\d{1,2} (?:%s)[a-z]* )?\d{4}$" % MON, txt)
                   else "spaced or mixed range" if re.search(r"\d – |\d - |\d-\d", txt)
                   else "not a canonical chart date")
            out.append(("dates", "FAIL", f"{why}: '{txt[:40]}'"))

    for ev in find(main, "span"):
        if "ev" in ev.cls():
            w = ev.content()
            if w not in GRADES:
                out.append(("evidence", "FAIL", f"grade chip reads '{w[:40]}', not one of the five"))
    for via in find(main, "span", "via"):
        if under(via, "ptree"):
            w = via.content()
            core = re.sub(r"^superseded — ", "", re.sub(r" · direct line$", "", w))
            if not w or core in SOURCE_WORDS or re.match(r"^(generation \d+|direct line|living — name only|several people of this name — not linked)$", w) \
                    or core.startswith("unmarked:"):
                if core.startswith("unmarked:"):
                    out.append(("source", "FAIL", f"a source word was not recognised: {w[:60]}"))
                continue
            out.append(("source", "warn", f"non-canonical source word: '{w[:40]}'"))

    for img in find(main, "img"):
        src = (img.attrs.get("src") or "").strip()
        if not src or img.attrs.get("id") == "lb-img":
            continue
        if living:
            out.append(("living", "FAIL", "a photograph on a living person's page"))
        if "alt" not in img.attrs or not (img.attrs.get("alt") or "").strip():
            out.append(("images", "FAIL", f"image without alt text: {src[-50:]}"))
        fig = img.parent
        while fig is not None and fig.tag != "figure":
            fig = fig.parent
        if fig is None or not list(find(fig, "figcaption")):
            out.append(("images", "warn", f"image without a figcaption: {src[-50:]}"))

    ld = [n.attrs.get("_script", "") for n in find(root, "script") if n.attrs.get("type") == "application/ld+json"]
    ld_person = any('"Person"' in x for x in ld)
    if living:
        if not noindex:
            out.append(("living", "FAIL", "a living person's page is not noindex"))
        if any(re.search(r'"(birthDate|deathDate|birthPlace|deathPlace)"', x) for x in ld):
            out.append(("living", "FAIL", "birth or death data in JSON-LD for a living person"))
        for n in find(main, "div"):
            if "me" in n.cls() and "node" in n.cls():
                d = next(find(n, "span", "dt"), None)
                if d is not None and d.content():
                    out.append(("living", "FAIL", "a date on the living person's own chart node"))
        body = []
        for n in main.walk():
            if n.tag in ("p", "li", "td", "dd", "div", "span") and not under(n, "ptree") and "ptree" not in n.cls():
                for x in n.text:
                    if isinstance(x, str):
                        body.append(x)
        # the h1 is a name; a year inside a name is not a date
        h1t = h1s[0].content() if h1s else ""
        if YEAR.search(" ".join(body).replace(h1t, "")):
            out.append(("living", "FAIL", "a year in the body of a living person's page"))
        if sitemap is not None and rel_url in sitemap:
            out.append(("living", "FAIL", "a living person's page is listed in the sitemap"))
    elif require_jsonld and not ld_person:
        out.append(("jsonld", "FAIL", "no Person structured data"))
    return canonical, living, out


def load_sitemap(path, host_hint=None):
    if not path or not os.path.exists(path):
        return None
    urls = set()
    for u in re.findall(r"<loc>([^<]+)</loc>", open(path, encoding="utf-8").read()):
        urls.add(re.sub(r"^https?://[^/]+", "", html.unescape(u)))
    return urls


def audit(dist, people, living_urls=(), sitemap=None, require_jsonld=False):
    """-> dict(pages, canonical, living, findings[(url, cat, sev, msg)], seen_redirects)"""
    base = os.path.join(dist, people.strip("/"))
    if not os.path.isdir(base):
        raise FileNotFoundError(f"no {people} under {dist}")
    res = dict(pages=0, canonical=0, living=0, findings=[], redirects=0)
    for slug in sorted(os.listdir(base)):
        p = os.path.join(base, slug, "index.html")
        if not os.path.isfile(p):
            continue
        root = parse(p)
        if any((m.attrs.get("http-equiv") or "").lower() == "refresh" for m in find(root, "meta")):
            res["redirects"] += 1
            continue
        url = "/" + people.strip("/") + "/" + slug + "/"
        res["pages"] += 1
        canonical, living, out = audit_page(root, url, set(living_urls), sitemap, require_jsonld)
        res["canonical"] += canonical
        res["living"] += living
        res["findings"] += [(url, c, s, m) for c, s, m in out]
    return res


def report(res, quiet=False, limit=6):
    cats = {}
    for url, c, s, m in res["findings"]:
        cats.setdefault((c, s), []).append((url, m))
    n_fail = sum(len(v) for (c, s), v in cats.items() if s == "FAIL")
    n_warn = sum(len(v) for (c, s), v in cats.items() if s == "warn")
    print(f"  people pages  {res['pages']} examined ({res['canonical']} built with PersonPage, {res['pages'] - res['canonical']} legacy), "
          f"{res['living']} declared living, {res['redirects']} redirect pages skipped")
    for (c, s), items in sorted(cats.items(), key=lambda kv: (kv[0][1] != "FAIL", kv[0][0])):
        pages = len({u for u, _ in items})
        print(f"  {s:5s} {c:9s} {len(items)} finding(s) on {pages} page(s)")
        if not quiet:
            kinds = {}
            for u, m in items:
                kinds.setdefault(re.sub(r"['\"].*", "", m)[:70], []).append(u)
            for k, us in sorted(kinds.items(), key=lambda kv: -len(kv[1]))[:limit]:
                print(f"        {len(us):5d}  {k}  →  {us[0]}")
    if not cats:
        print("  ok    no finding on any page")
    return n_fail, n_warn


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--people", default="/people/", help="where the person pages are: /people/ or /person/")
    ap.add_argument("--living-urls", help="a file of URL paths, one per line, known to be living (from the archive's own data)")
    ap.add_argument("--sitemap", help="a sitemap.xml to check living pages are absent from")
    ap.add_argument("--require-jsonld", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any FAIL")
    ap.add_argument("--max", type=int, default=None, help="ratchet: exit 1 only if FAILs exceed this")
    ap.add_argument("--min-pages", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    dist = outdir.resolve(a.dist)
    living = set()
    if a.living_urls:
        living = {l.strip() for l in open(a.living_urls) if l.strip()}
    sm = load_sitemap(a.sitemap)
    try:
        res = audit(dist, a.people, living, sm, a.require_jsonld)
    except FileNotFoundError as e:
        print(f"  --    people     COULD NOT SEE ANY PEOPLE PAGE: {e}. That is not a pass. Build first, or point ARCHIVE_OUT at the build.")
        return 2
    if res["pages"] < a.min_pages:
        print(f"  --    people     COULD NOT SEE ANY PEOPLE PAGE: {res['pages']} under {a.people} (need {a.min_pages}). That is not a pass.")
        return 2
    if a.json:
        print(json.dumps(res, indent=1))
    n_fail, n_warn = report(res, a.quiet)
    verdict = "FAIL" if n_fail else "ok"
    print(f"  {verdict:5s} people     {n_fail} FAIL and {n_warn} advisory finding(s) across {res['pages']} page(s)"
          + ("" if a.strict or a.max is not None else "  (advisory: pass --strict or --max to gate)"))
    if a.max is not None:
        return 1 if n_fail > a.max else 0
    return 1 if (a.strict and n_fail) else 0


if __name__ == "__main__":
    sys.exit(main())
