#!/usr/bin/env python3
"""The gate on the family ribbons and on the direct-line tint: the data behind components/FamilyRibbon.astro and every `is-ours`.

WHY. A family page that says "our line touches this family here" makes a claim about the direct line, and a tint that says "this
person is on our direct line" makes it again, on every card, node, row and page where it appears. The first is easy to type once
and let drift; the second is easy to apply to a person who is not (a namesake, a cousin), or to leave off one who is. So the tint
is not set by hand anywhere: it comes from ONE file, src/data/direct-line.json, which is made from the story's ribbon, and this
checks both directions: nobody is tinted who is not in the file, everybody in the file who is drawn is tinted, and the file
is the story's ribbon. The contract is kit/docs/family-ribbon.md; the story's gate is checkfamilystory.py and this one reuses its reader.

    python3 checkfamilyribbon.py --families src/data/family-lines.json --direct src/data/direct-line.json \\
            --story src/data/story.json --dist dist [--person-base /people/] [--story-page /story/] [--lines src/data/lines.json]
                                [--living living.json] [--strict]
    python3 checkfamilyribbon.py ... --no-dist       the data only; says it did not look at the site
    python3 checkfamilyribbon.py --selftest          build a site around kit/data/family-lines-example.json and plant every fault in it

Rules (the code is printed with every finding):
  D0  direct-line.json does not match kit/data/direct-line-schema.json
  D1  (with --story) `people` and `unlinked` are the story ribbon's cards: the same persons, the same generation numbers, the same chapters
  D2  (with --story) `partners` are the spouses of cards that say spouseDirect, and every such spouse is a partner
  D3  a slug is listed once (people and partners together)
  F0  family-lines.json does not match kit/data/family-ribbon-schema.json
  F1  family ids and pages are unique
  F2  every card has every field (name, years, origin, originGrade, spouse, spouseOrigin, atPlace, atYear, living)
  F3  no ribbon is empty: a family has cards, or a lane that exists in --lines
  F4  the living rule: a living card has no years, no "at" year, and no date anywhere in its text; a minor has an initial for a name,
      no years, no spouse, no link; a person on the archive's private --living list is a living card
  F5  a family of status family-lore has no documented card
  C1  every connection's ourSlug is in direct-line.json (people or partners), and ourGeneration is that person's generation
  C2  every connection's theirSlug is on this family's cards (person or spousePerson) or is a built person page (--dist)
  C3  the relation is one of the kit's; godparent of, godchild of and witness for are said only of a documented relation (grade doc)
  C4  a family has connections or notConnected, not both and not neither; notConnected says what is missing
  C5  a connection with a living party carries no date in its note or names
  C6  the same pair is not connected twice by the same relation
  C7  (with --dist) storyHref resolves: the story page is built, and the chapter's id is in it
  B1  (with --dist) the built family page has a ribbon for the family, a card for each card, each with the same parts
  B2  a built living card shows no date; a built minor shows an initial and no link
  B3  every person link in a built ribbon and block resolves to a built page
  B4  a built card is tinted (is-ours) exactly when its person is in direct-line.json, and says so (data-ours = the slug)
  B5  a built block per connection, our side tinted and naming the person and the generation direct-line.json gives; a not-connected block iff notConnected
  B6  a page with a ribbon has the legend "tinted = our direct line"
  O1  every `is-ours` on any built page names a person in direct-line.json (data-ours = slug, gen:N for an unlinked card, lane:<key> for a lane)
  O2  the story ribbon is tinted on every card that is on the line, and nowhere else
  O3  a person page of someone in direct-line.json has the band "On our direct line · generation n"; a page that is not theirs has none
  O4  a built page with a tinted card, node, row or lane has the legend "tinted = our direct line"
Exit 0 clean (warnings do not fail unless --strict), 1 on any error, 2 on a file that cannot be read or when nothing was checked.
"""
import argparse, copy, json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from checkfamilystory import Site, Doc, Report, schema_errors, has_date, is_initial  # noqa: E402

LEGEND = "tinted = our direct line"
CARD_FIELDS = ["name", "years", "origin", "originGrade", "spouse", "spouseOrigin", "atPlace", "atYear", "living"]
RELATIONS = ["married", "son of", "daughter of", "child of", "father of", "mother of", "parent of", "brother of", "sister of",
             "sibling of", "godparent of", "godchild of", "witness for"]
NEEDS_DOC = {"godparent of", "godchild of", "witness for"}
PARTS = ["fr-g", "fr-n", "fr-y", "fr-f", "fr-s"]


def load(path):
    return json.load(open(path, encoding="utf-8"))


def strip_name(rows):
    return [{k: v for k, v in r.items() if k != "name"} for r in rows]


# ---------------------------------------------------------------- the data
def from_story(story):
    """The direct-line file the story makes (the same as kit/tools/directline.py and kit/lib/directline.js fromStory)."""
    people, partners, unlinked = [], [], []
    for i, c in enumerate((story.get("ribbon") or {}).get("cards") or []):
        if c.get("person"):
            people.append({"slug": c["person"], "generation": i + 1, "storyChapter": c.get("chapter", "")})
        else:
            unlinked.append({"generation": i + 1, "storyChapter": c.get("chapter", "")})
        if c.get("spouseDirect") and c.get("spousePerson"):
            partners.append({"slug": c["spousePerson"], "generation": i + 1, "storyChapter": c.get("chapter", ""), "partnerOf": c.get("person", "")})
    return {"people": people, "partners": partners, "unlinked": unlinked}


def dmap(dl):
    m = {}
    for p in (dl or {}).get("people") or []:
        m.setdefault(p.get("slug"), dict(p, role="line"))
    for p in (dl or {}).get("partners") or []:
        m.setdefault(p.get("slug"), dict(p, role="partner"))
    return m


def check_direct(dl, story, R):
    sch = load(os.path.join(KIT, "data", "direct-line-schema.json"))
    for path, msg in schema_errors(dl, sch, sch):
        R.err("D0", "direct-line.json " + path, msg)
    seen = {}
    for p in (dl.get("people") or []) + (dl.get("partners") or []):
        s = p.get("slug")
        if s in seen:
            R.err("D3", "direct-line.json", "%s is listed more than once" % s)
        seen[s] = 1
    if story is None:
        return
    want = from_story(story)
    for key in ("people", "unlinked"):
        got = strip_name(dl.get(key) or [])
        if got != strip_name(want[key]):
            gs = {(r.get("slug"), r.get("generation"), r.get("storyChapter")) for r in got}
            ws = {(r.get("slug"), r.get("generation"), r.get("storyChapter")) for r in want[key]}
            R.err("D1", "direct-line.json " + key, "is not the story ribbon's: missing %s; extra %s" % (sorted(map(str, ws - gs)) or "none", sorted(map(str, gs - ws)) or "none"))
    got = strip_name(dl.get("partners") or [])
    if got != strip_name(want["partners"]):
        gs = {(r.get("slug"), r.get("generation")) for r in got}
        ws = {(r.get("slug"), r.get("generation")) for r in want["partners"]}
        R.err("D2", "direct-line.json partners", "are not the spouses of the cards that say spouseDirect: missing %s; extra %s" % (sorted(map(str, ws - gs)) or "none", sorted(map(str, gs - ws)) or "none"))


def living_slugs(story):
    out = set()
    for c in ((story or {}).get("ribbon") or {}).get("cards") or []:
        if c.get("living") and c.get("person"):
            out.add(c["person"])
        if (c.get("spouseLiving", c.get("living"))) and c.get("spousePerson"):
            if c.get("spouseLiving") is True:
                out.add(c["spousePerson"])
    return out


def card_text(c):
    return " ".join(str(c.get(k, "")) for k in ("name", "years", "origin", "spouse", "spouseOrigin", "atPlace", "atYear", "title"))


def check_families(fl, dl, story, a, R, lines, living_names):
    sch = load(os.path.join(KIT, "data", "family-ribbon-schema.json"))
    errs = schema_errors(fl, sch, sch)
    for path, msg in errs:
        R.err("F0", "family-lines.json " + path, msg)
    if errs and not isinstance(fl.get("families"), list):
        return
    fams = [f for f in fl.get("families") or [] if isinstance(f, dict)]
    dm = dmap(dl)
    story_lv = living_slugs(story)
    ids, pages = {}, {}
    for f in fams:
        fid = f.get("id", "?")
        if fid in ids:
            R.err("F1", fid, "family id used twice")
        ids[fid] = 1
        if f.get("page") in pages:
            R.err("F1", fid, "page %s is also the page of %s" % (f.get("page"), pages[f["page"]]))
        pages[f.get("page")] = fid
        cards = f.get("cards") or []
        if not cards:
            lane = f.get("lane")
            if not lane:
                R.err("F3", fid, "has no cards and no lane: an empty ribbon says nothing")
            elif lines is not None and not lane_exists(lines, lane):
                R.err("F3", fid, "names the lane %r, which is not in the lines file" % (lane,))
        on_cards = set()
        card_living = {}
        for i, c in enumerate(cards):
            where = "%s card %d (%s)" % (fid, i + 1, c.get("name", "?"))
            miss = [k for k in CARD_FIELDS if k not in c]
            if miss:
                R.err("F2", where, "has no %s: every card has every field (an empty string where it does not apply)" % ", ".join(miss))
            if c.get("person"):
                on_cards.add(c["person"])
            if c.get("spousePerson"):
                on_cards.add(c["spousePerson"])
            if c.get("person"):
                card_living[c["person"]] = bool(c.get("living"))
            living = bool(c.get("living")) or c.get("minor")
            if c.get("name") and str(c["name"]).strip().lower() in living_names and not c.get("living"):
                R.err("F4", where, "is on the archive's private living list but is not a living card")
            if c.get("minor"):
                if not c.get("living"):
                    R.err("F4", where, "a minor must also be living")
                if not is_initial(c.get("name")):
                    R.err("F4", where, "a minor shows an initial and nothing else, not %r" % c.get("name"))
                for k in ("years", "atYear", "spouse", "spouseOrigin", "origin", "atPlace", "person", "spousePerson", "spouseHref", "title"):
                    if c.get(k):
                        R.err("F4", where, "a minor carries no %s" % k)
            elif living:
                if c.get("years"):
                    R.err("F4", where, "a living card carries no years (%r)" % c["years"])
                if c.get("atYear"):
                    R.err("F4", where, "a living card carries no year on its 'at' line (%r)" % c["atYear"])
                if has_date(card_text(c)):
                    R.err("F4", where, "a living card has a date in its text: %r" % card_text(c).strip()[:90])
        if f.get("status") == "family-lore" and any(c.get("originGrade") == "doc" for c in cards):
            R.err("F5", fid, "is family lore (nothing on it is documented) but has a documented card")
        conns = f.get("connections") or []
        nc = f.get("notConnected")
        if conns and nc:
            R.err("C4", fid, "has connections and says it is not connected")
        if not conns and not nc:
            R.err("C4", fid, "has no connections and no notConnected: say where the line touches this family, or what is missing")
        if nc is not None and not str((nc or {}).get("why", "")).strip():
            R.err("C4", fid, "notConnected must say what is missing")
        seen = set()
        for j, cn in enumerate(conns):
            where = "%s connection %d" % (fid, j + 1)
            ent = dm.get(cn.get("ourSlug"))
            if ent is None:
                R.err("C1", where, "ourSlug %r is not in direct-line.json: only a person on the direct line can be 'our line'" % cn.get("ourSlug"))
            elif ent.get("generation") != cn.get("ourGeneration"):
                R.err("C1", where, "ourGeneration %s is not %s's generation in direct-line.json (%s)" % (cn.get("ourGeneration"), cn.get("ourSlug"), ent.get("generation")))
            if cn.get("theirSlug") not in on_cards:
                if a.dist and not a.no_dist:
                    if Site(a.dist).page("%s%s/" % (a.person_base, cn.get("theirSlug"))) is None:
                        R.err("C2", where, "theirSlug %r is on none of the family's cards and is not a built person page" % cn.get("theirSlug"))
                else:
                    R.warn("C2", where, "theirSlug %r is on none of the family's cards (the person page was not looked for: no --dist)" % cn.get("theirSlug"))
            rel = cn.get("relation")
            if rel not in RELATIONS:
                R.err("C3", where, "relation %r is not one of %s" % (rel, ", ".join(RELATIONS)))
            elif rel in NEEDS_DOC and cn.get("grade") != "doc":
                R.err("C3", where, "%r is said only of a documented relation (grade doc), not %r" % (rel, cn.get("grade")))
            parties_living = story_lv & {cn.get("ourSlug"), cn.get("theirSlug")} or card_living.get(cn.get("theirSlug")) or cn.get("theirSlug") in {c.get("spousePerson") for c in cards if c.get("living")}
            if parties_living and has_date(" ".join(str(cn.get(k, "")) for k in ("note", "theirName", "ourName", "theirOrigin"))):
                R.err("C5", where, "a party to this connection is living and its text holds a date: %r" % (cn.get("note", "")[:90]))
            key = (cn.get("ourSlug"), cn.get("theirSlug"), rel)
            if key in seen:
                R.err("C6", where, "the same pair is connected twice by %r" % rel)
            seen.add(key)


def lane_exists(lines, ref):
    sets = lines if isinstance(lines, list) else lines.get("sets") or [lines]
    for s in sets:
        if ref.get("set") and ref["set"] not in (s.get("slug"), s.get("name"), s.get("key")):
            continue
        if any(l.get("key") == ref.get("key") for l in s.get("lanes") or []):
            return True
    return False


# ---------------------------------------------------------------- the built site
def resolves(site, href, base_page, R, code, where, person_base):
    if not href or href.startswith(("http://", "https://", "mailto:")):
        return
    path, _, frag = href.partition("#")
    if not path:
        return
    if site.page(path) is None:
        R.err(code, where, "link %s goes nowhere" % href)
    elif frag and not site.has_id(path, frag):
        R.err("C7" if code == "B3" else code, where, "link %s: no #%s in the page" % (href, frag))


def check_built_family(f, dl, a, R, site, story=None):
    dm = dmap(dl)
    page = f.get("page")
    html = site.page(page)
    if html is None:
        R.err("B1", f.get("id"), "the family page %s is not built" % page)
        return
    doc = Doc(html)
    secs = doc.find(lambda n: n.tag == "section" and "fr" in n.cls() and n.attrs.get("data-family") == f.get("id"))
    cards = f.get("cards") or []
    if not secs:
        if cards or f.get("lane"):
            R.err("B1", f.get("id"), "the built page %s has no ribbon for %s" % (page, f.get("id")))
        return
    sec = secs[0]
    where = "%s on %s" % (f.get("id"), page)
    lis = [n for n in sec.walk() if n.tag == "li" and "fr-c" in n.cls()]
    if cards and len(lis) != len(cards):
        R.err("B1", where, "built %d cards, the data has %d" % (len(lis), len(cards)))
    if not lis:
        R.err("B1", where, "the built ribbon is empty")
    for i, li in enumerate(lis):
        w = "%s card %d" % (where, i + 1)
        classes = {c for k in li.walk() for c in k.cls()}
        miss = [p for p in PARTS if p not in classes]
        if miss:
            R.err("B1", w, "is missing %s: every card has the same parts" % ", ".join(miss))
        person = li.attrs.get("data-person")
        want = dm.get(person) if person else None
        tinted = "is-ours" in li.cls()
        if tinted and not want:
            R.err("B4", w, "is tinted but %r is not in direct-line.json" % person)
        elif want and not tinted:
            R.err("B4", w, "%s is on the direct line (generation %s) and is not tinted" % (person, want.get("generation")))
        if tinted and want and li.attrs.get("data-ours") != person:
            R.err("B4", w, "is tinted but does not say whom (data-ours %r, person %r)" % (li.attrs.get("data-ours"), person))
        if i < len(cards):
            c = cards[i]
            if (c.get("person") or None) != (person or None):
                R.err("B1", w, "is about %r, the data's card is about %r" % (person, c.get("person")))
            if bool(c.get("living")) != (li.attrs.get("data-living") == "1"):
                R.err("B2", w, "living flag differs from the data")
        text = li.all_text()
        if li.attrs.get("data-living") == "1" and has_date(re.sub(r"Gen\. \d+", "", text)):
            R.err("B2", w, "a living card shows a date: %r" % re.sub(r"\s+", " ", text).strip()[:100])
        if li.attrs.get("data-minor") == "1":
            nm = [k for k in li.walk() if "fr-n" in k.cls()]
            if li.find if False else False:
                pass
            if nm and (not is_initial(nm[0].all_text().strip()) or any(k.tag == "a" for k in nm[0].walk())):
                R.err("B2", w, "a minor shows an initial and no link, not %r" % nm[0].all_text().strip())
    # links
    for n in sec.walk():
        if n.tag == "a" and n.attrs.get("href"):
            h = n.attrs["href"]
            if h.startswith("#"):
                if not re.search(r"""\bid\s*=\s*["']%s["']""" % re.escape(h[1:]), html):
                    R.err("B3", where, "link %s: no such id in the page" % h)
            elif h.startswith(a.person_base):
                if site.page(h) is None:
                    R.err("B3", where, "person link %s resolves to no built page" % h)
            else:
                resolves(site, h, page, R, "C7", where, a.person_base)
    # blocks
    blocks = [n for n in sec.walk() if n.tag == "li" and "fr-b" in n.cls()]
    conns = f.get("connections") or []
    nc = [n for n in sec.walk() if "fr-nc" in n.cls()]
    # the blocks are the family's connections plus the story's own marriages (the page may derive those: lib/familyribbon.js marriageConnections)
    allowed = {(c.get("ourSlug"), c.get("theirSlug"), c.get("relation")) for c in conns}
    here = {li.attrs.get("data-person") for li in lis} | {li.attrs.get("data-spouse-person") for li in lis}
    here.discard(None)
    for sc in ((story or {}).get("ribbon") or {}).get("cards") or []:
        if sc.get("person") and sc.get("spousePerson") in here:
            allowed.add((sc["person"], sc["spousePerson"], "married"))
    built = {(b.attrs.get("data-our"), b.attrs.get("data-their"), b.attrs.get("data-relation")) for b in blocks}
    for k in sorted(allowed & {(c.get("ourSlug"), c.get("theirSlug"), c.get("relation")) for c in conns} - built):
        R.err("B5", where, "the connection %s -> %s (%s) is in the data and not on the page" % k)
    for k in sorted(built - allowed, key=str):
        R.err("B5", where, "a block %s -> %s (%s) is on the page and is neither in the data nor one of the story's marriages" % k)
    if not conns and blocks and f.get("notConnected"):
        R.err("B5", where, "built connection blocks for a family that says it is not connected")
    if f.get("notConnected") and not nc:
        R.err("B5", where, "the family says it is not connected and the page shows no 'not connected' block")
    if conns and nc:
        R.err("B5", where, "a 'not connected' block beside connections")
    for b in blocks:
        ours = [k for k in b.walk() if "fr-b-our" in k.cls()]
        slug = ours[0].attrs.get("data-ours") if ours else None
        if not ours or "is-ours" not in ours[0].cls() or slug not in dm:
            R.err("B5", where, "a connection block's our-side is not tinted or names nobody on the direct line (%r)" % slug)
        elif str(dm[slug].get("generation")) != str(b.attrs.get("data-our-generation")):
            R.err("B5", where, "block says generation %s for %s, direct-line.json says %s" % (b.attrs.get("data-our-generation"), slug, dm[slug].get("generation")))
    for n in sec.walk():
        if "is-ours" in n.cls() and n.attrs.get("data-ours") not in dm:
            R.err("O1", where, "an is-ours element names %r, who is not in direct-line.json" % n.attrs.get("data-ours"))
    if LEGEND not in re.sub(r"\s+", " ", " ".join(k.all_text() for k in doc.find(lambda n: "fr-leg" in n.cls()))):
        R.err("B6", where, "the page has a ribbon and no legend '%s'" % LEGEND)


def scan_site(a, dl, story, R, site):
    dm = dmap(dl)
    unl = {u.get("generation") for u in (dl.get("unlinked") or [])}
    seen_band = set()
    n_pages = 0
    for d, ds, fs in os.walk(a.dist):
        for fn in fs:
            if not fn.endswith(".html"):
                continue
            full = os.path.join(d, fn)
            try:
                html = open(full, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if "is-ours" not in html and "ours-band" not in html:
                continue
            rel = "/" + os.path.relpath(d, a.dist).replace(os.sep, "/") + "/"
            rel = rel.replace("/./", "/") if fn == "index.html" else "/" + os.path.relpath(full, a.dist).replace(os.sep, "/")
            doc = Doc(html)
            text = re.sub(r"\s+", " ", doc.root.all_text())
            tinted = [n for n in doc.root.walk() if ("is-ours" in n.cls() or "is-ours-lane" in n.cls()) and "sw" not in n.cls()]
            for n in tinted:
                k = n.attrs.get("data-ours")
                ok = k in dm or (k or "").startswith("lane:") or (k or "").startswith("gen:") and k[4:].isdigit() and int(k[4:]) in unl
                if not ok:
                    R.err("O1", rel, "an is-ours <%s> names %r, who is not in direct-line.json" % (n.tag, k))
            bands = [n for n in doc.root.walk() if "ours-band" in n.cls()]
            if tinted or bands:
                n_pages += 1
            slug = None
            if rel.startswith(a.person_base) and rel != a.person_base:
                slug = rel[len(a.person_base):].strip("/")
            for b in bands:
                if slug is None or slug not in dm or b.attrs.get("data-ours") != slug:
                    R.err("O3", rel, "an 'On our direct line' band on a page that is not that person's (%r)" % b.attrs.get("data-ours"))
                else:
                    seen_band.add(slug)
                    if "generation %s" % dm[slug].get("generation") not in re.sub(r"\s+", " ", b.all_text()):
                        R.err("O3", rel, "the band does not say generation %s" % dm[slug].get("generation"))
            others = [n for n in tinted if "ours-band" not in n.cls()]
            if others and LEGEND not in text:
                R.err("O4", rel, "tinted cards, nodes or rows and no legend '%s'" % LEGEND)
    # O3 reverse: a direct-line person with a built page must have the band
    for slug, e in dm.items():
        if site.page("%s%s/" % (a.person_base, slug)) is not None and slug not in seen_band:
            R.err("O3", a.person_base + slug + "/", "is on the direct line (generation %s) and its page has no band" % e.get("generation"))
    return n_pages


def check_story_page(a, dl, story, R, site):
    html = site.page(a.story_page)
    if html is None:
        R.warn("O2", a.story_page, "the story page is not built; its ribbon's tint was not checked")
        return
    doc = Doc(html)
    cards = doc.find(lambda n: n.tag == "li" and "st-rb" in n.cls())
    if not cards:
        R.warn("O2", a.story_page, "the built story page has no ribbon")
        return
    dm = dmap(dl)
    unl = {u.get("generation") for u in (dl.get("unlinked") or [])}
    for i, li in enumerate(cards):
        person = li.attrs.get("data-person")
        on = (person in dm) if person else ((i + 1) in unl)
        tint = "is-ours" in li.cls()
        if on and not tint:
            R.err("O2", a.story_page, "ribbon card %d is on the direct line and is not tinted" % (i + 1))
        if tint and not on:
            R.err("O2", a.story_page, "ribbon card %d is tinted but is not on the direct line" % (i + 1))
        if tint and li.attrs.get("data-ours") != (person or "gen:%d" % (i + 1)):
            R.err("O2", a.story_page, "ribbon card %d is tinted and does not say whom (data-ours %r)" % (i + 1, li.attrs.get("data-ours")))


def run(a):
    try:
        fl = load(a.families)
        dl = load(a.direct)
        story = load(a.story) if a.story else None
        lines = load(a.lines) if a.lines else None
    except (OSError, ValueError) as e:
        print("checkfamilyribbon: cannot read: %s" % e, file=sys.stderr)
        return 2
    names = set()
    if a.living:
        try:
            raw = load(a.living)
            names = {str(x).strip().lower() for x in (raw.get("names", []) if isinstance(raw, dict) else raw)}
        except (OSError, ValueError) as e:
            print("checkfamilyribbon: cannot read %s: %s" % (a.living, e), file=sys.stderr)
            return 2
    if not a.dist and not a.no_dist:
        print("checkfamilyribbon: pass --dist (or --no-dist, which says plainly that the site was not looked at)", file=sys.stderr)
        return 2
    R = Report()
    check_direct(dl, story, R)
    check_families(fl, dl, story, a, R, lines, names)
    looked = "the data only"
    n_pages = 0
    if a.dist and not a.no_dist:
        if not os.path.isdir(a.dist):
            print("checkfamilyribbon: no such dist %s" % a.dist, file=sys.stderr)
            return 2
        site = Site(a.dist)
        for f in (fl.get("families") or []):
            if isinstance(f, dict):
                check_built_family(f, dl, a, R, site, story)
        n_pages = scan_site(a, dl, story, R, site)
        check_story_page(a, dl, story, R, site)
        looked = "the data and the built site (%d pages carry the tint)" % n_pages
    for code, where, msg in R.errors:
        print("FAIL [%s] %s: %s" % (code, where, msg))
    for code, where, msg in R.warnings:
        print("warn [%s] %s: %s" % (code, where, msg))
    nf = len(fl.get("families") or []) if isinstance(fl, dict) else 0
    print("checkfamilyribbon: %d error(s), %d warning(s) (%d families, %d on the line; looked at %s)" % (len(R.errors), len(R.warnings), nf, len(dmap(dl)), looked))
    if a.no_dist:
        print("checkfamilyribbon: --no-dist: the built pages, their links and the tint were NOT checked")
    if story is None:
        print("checkfamilyribbon: no --story: direct-line.json was not held to the story's ribbon (D1, D2)")
    return 1 if R.errors or (a.strict and R.warnings) else 0


# ---------------------------------------------------------------- the selftest
def _card_html(c, i, dl, joins):
    dm = dmap(dl)
    person = c.get("person")
    ours = person in dm
    living = 1 if c.get("living") else 0
    minor = c.get("minor")
    name = c["name"] if (minor or not person) else '<a href="/people/%s/">%s</a>' % (person, c["name"])
    spouse = ""
    if c.get("spouse"):
        sp = '<a href="/people/%s/">%s</a>' % (c["spousePerson"], c["spouse"]) if c.get("spousePerson") else c["spouse"]
        spouse = "m. %s%s" % (sp, ", " + c["spouseOrigin"] if c.get("spouseOrigin") else "")
    return ('<li class="fr-c fr-c-%s%s" data-living="%d"%s%s%s><span class="fr-g">Gen. %d</span><span class="fr-n">%s</span><span class="fr-y">%s</span>'
            '<span class="fr-f">%s</span>%s<span class="fr-s">%s</span></li>') % (
        c.get("originGrade"), " is-ours" if ours else "", living, ' data-minor="1"' if minor else "",
        ' data-person="%s"' % person if person else "", ' data-ours="%s"' % person if ours else "", i + 1, name,
        "" if living else c.get("years", ""), ("from " + c["origin"]) if c.get("origin") else "", "", spouse)


def _family_page(f, dl, legend=True):
    dm = dmap(dl)
    out = ['<html><body><main><section class="fr" data-family="%s"><div class="fr-rib"><ol>' % f["id"]]
    for i, c in enumerate(f.get("cards") or []):
        out.append(_card_html(c, i, dl, None))
    out.append('</ol></div><div class="fr-conn"><h3>How our line connects</h3>')
    conns = f.get("connections") or []
    if conns:
        out.append('<ul class="fr-bl">')
        for j, cn in enumerate(conns):
            e = dm.get(cn["ourSlug"], {})
            their = '<a href="/people/%s/">%s</a>' % (cn["theirSlug"], cn["theirName"])
            out.append('<li class="fr-b fr-b-%s" id="frb-%s-%d" data-relation="%s" data-our="%s" data-their="%s" data-our-generation="%s"><div class="fr-b-our is-ours" data-ours="%s"><a href="/people/%s/">%s</a></div>'
                       '<div class="fr-b-rel">%s</div><div class="fr-b-their">%s</div><p class="fr-b-foot"><a href="%s">in the story</a></p></li>' % (
                           cn["grade"], f["id"], j + 1, cn["relation"], cn["ourSlug"], cn["theirSlug"], e.get("generation", cn["ourGeneration"]), cn["ourSlug"], cn["ourSlug"], e.get("name", cn["ourSlug"]), cn["relation"], their, cn["storyHref"]))
        out.append("</ul>")
    else:
        out.append('<p class="fr-nc"><b>Not connected to our line yet.</b> %s</p>' % (f.get("notConnected") or {}).get("why", ""))
    out.append("</div>")
    if legend:
        out.append('<p class="fr-leg"><span class="ours-sw"></span>%s</p>' % LEGEND)
    out.append("</section></main></body></html>")
    return "".join(out)


def _story_page(story, dl):
    dm = dmap(dl)
    out = ['<html><body><div class="story"><nav class="st-rib"><ol>']
    for i, c in enumerate(story["ribbon"]["cards"]):
        person = c.get("person")
        on = (person in dm) if person else any(u.get("generation") == i + 1 for u in dl.get("unlinked") or [])
        key = person or "gen:%d" % (i + 1)
        out.append('<li class="st-rb%s"%s%s><span>%s</span></li>' % (" is-ours" if on else "", ' data-person="%s"' % person if person else "", ' data-ours="%s"' % key if on else "", c["name"]))
    out.append('</ol></nav><aside class="st-legend"><span class="ours-sw"></span>%s</aside>' % LEGEND)
    for c in story["chapters"]:
        out.append('<section id="%s"><h2>x</h2></section>' % c["id"])
    out.append("</div></body></html>")
    return "".join(out)


def _person_page(slug, dl):
    e = dmap(dl).get(slug)
    band = ('<p class="ours-band is-ours" data-ours="%s" data-generation="%s"><b>On our direct line · generation %s</b><a href="/story/#%s">in the story →</a></p>' % (slug, e["generation"], e["generation"], e["storyChapter"])) if e else ""
    return "<html><body><article class='ppage'><header><h1>%s</h1>%s</header></article></body></html>" % (slug, band)


def _site(root, fl, dl, story, planted=None):
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)

    def w(path, txt):
        p = os.path.join(root, path.strip("/"), "index.html")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(txt)
    slugs = set(dmap(dl))
    for f in fl["families"]:
        for c in f.get("cards") or []:
            for k in ("person", "spousePerson"):
                if c.get(k):
                    slugs.add(c[k])
        for cn in f.get("connections") or []:
            slugs.add(cn["theirSlug"])
    for s in slugs:
        w("people/" + s, _person_page(s, dl))
    for f in fl["families"]:
        w(f["page"], _family_page(f, dl))
    w("story", _story_page(story, dl))


def selftest():
    base_fl = load(os.path.join(KIT, "data", "family-lines-example.json"))
    base_dl = load(os.path.join(KIT, "data", "direct-line-example.json"))
    story = load(os.path.join(KIT, "data", "story-example.json"))
    res = []

    def ok(label, cond, detail=""):
        res.append(bool(cond))
        print("  %s  %s%s" % ("ok  " if cond else "FAIL", label, ("  [%s]" % detail[:500]) if detail and not cond else ""))

    tmp = tempfile.mkdtemp(prefix="ribbonself_")
    try:
        def gate(fl, dl, st=story, build=True, hand=None, extra=()):
            """Run the gate on the data; the site is built from the same data unless `hand` edits the built files."""
            dist = os.path.join(tmp, "dist")
            if build:
                _site(dist, fl, dl, st)
            if hand:
                hand(dist)
            json.dump(fl, open(os.path.join(tmp, "f.json"), "w"))
            json.dump(dl, open(os.path.join(tmp, "d.json"), "w"))
            json.dump(st, open(os.path.join(tmp, "s.json"), "w"))
            ns = argparse.Namespace(families=os.path.join(tmp, "f.json"), direct=os.path.join(tmp, "d.json"), story=os.path.join(tmp, "s.json"), dist=dist, no_dist=False,
                                    person_base="/people/", story_page="/story/", lines=None, living=None, strict=False)
            for k, v in extra:
                setattr(ns, k, v)
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                rc = run(ns)
            return rc, buf.getvalue()

        def planted(label, code, fl_edit=None, dl_edit=None, hand=None, st_edit=None, extra=()):
            fl, dl, st = copy.deepcopy(base_fl), copy.deepcopy(base_dl), copy.deepcopy(story)
            if fl_edit:
                fl_edit(fl)
            if dl_edit:
                dl_edit(dl)
            if st_edit:
                st_edit(st)
            rc, out = gate(fl, dl, st, hand=hand, extra=extra)
            ok("%s -> %s" % (label, code), rc == 1 and "[%s]" % code in out, out)

        print("the clean example")
        rc, out = gate(base_fl, base_dl)
        ok("the example data and the site built from it pass", rc == 0, out)
        s0 = copy.deepcopy(story)
        rc, out = gate(base_fl, from_story(s0) | {"generationLabel": "generation"})
        ok("direct-line.json made by from_story() passes", rc == 0, out)

        fam = lambda fl, i=0: fl["families"][i]
        print("direct-line.json")
        planted("a person who is not in the story's ribbon", "D1", dl_edit=lambda d: d["people"].append({"slug": "a-cousin", "generation": 3, "storyChapter": "harbour"}))
        planted("a person left out of the file", "D1", dl_edit=lambda d: d["people"].pop())
        planted("a wrong generation number", "D1", dl_edit=lambda d: d["people"][0].update(generation=4))
        planted("a wrong chapter", "D1", dl_edit=lambda d: d["people"][1].update(storyChapter="harbour"))
        planted("a partner nobody marked spouseDirect", "D2", dl_edit=lambda d: d["partners"].append({"slug": "greta", "generation": 2, "storyChapter": "ship", "partnerOf": "pieter-arden-1822"}))
        planted("a spouseDirect spouse that is not a partner", "D2", dl_edit=lambda d: d["partners"].clear())
        planted("a slug listed twice", "D3", dl_edit=lambda d: d["people"].append(dict(d["people"][0])))
        planted("a field the contract does not know", "D0", dl_edit=lambda d: d.update(friends=[]))
        print("the cards")
        planted("a card with a field missing", "F2", fl_edit=lambda fl: fam(fl)["cards"][0].pop("spouseOrigin"))
        planted("a living card with years", "F4", fl_edit=lambda fl: fam(fl)["cards"][2].update(years="1990–"))
        planted("a living card with a date in its title", "F4", fl_edit=lambda fl: fam(fl)["cards"][2].update(title="Born 3 May 1990 at Hollin"))
        planted("a living card with an at-year", "F4", fl_edit=lambda fl: fam(fl)["cards"][2].update(atPlace="Hollin", atYear="2004"))
        planted("a minor with a full name", "F4", fl_edit=lambda fl: fam(fl)["cards"].append({"name": "Karl Brandt", "years": "", "origin": "", "originGrade": "lore", "spouse": "", "spouseOrigin": "", "atPlace": "", "atYear": "", "living": True, "minor": True}))
        planted("a minor with a link", "F4", fl_edit=lambda fl: fam(fl)["cards"].append({"name": "K.", "years": "", "origin": "", "originGrade": "lore", "spouse": "", "spouseOrigin": "", "atPlace": "", "atYear": "", "living": True, "minor": True, "person": "tomas-arden-1790"}))
        with open(os.path.join(tmp, "living.json"), "w") as fh:
            json.dump(["Edric Harrow"], fh)
        planted("a person on the archive's private living list drawn as a deceased card", "F4", extra=(("living", os.path.join(tmp, "living.json")),))
        planted("a family with no cards and no lane", "F3", fl_edit=lambda fl: fam(fl).pop("cards"))
        planted("a family of family lore with a documented card", "F5", fl_edit=lambda fl: (fam(fl, 1).update(status="family-lore"), fam(fl, 1)["cards"][0].update(originGrade="doc")))
        planted("an origin grade that is not doc, inf or lore", "F0", fl_edit=lambda fl: fam(fl)["cards"][0].update(originGrade="probably"))
        planted("two families on one page", "F1", fl_edit=lambda fl: fam(fl, 1).update(page="/brandt/"))
        print("how our line connects")
        planted("a connection to someone not on the direct line", "C1", fl_edit=lambda fl: fam(fl)["connections"][0].update(ourSlug="a-cousin"))
        planted("a connection naming the wrong generation", "C1", fl_edit=lambda fl: fam(fl)["connections"][0].update(ourGeneration=3))
        planted("a connection to a person who is nowhere", "C2", fl_edit=lambda fl: fam(fl)["connections"][0].update(theirSlug="nobody-1700"),
                hand=lambda d: shutil.rmtree(os.path.join(d, "people", "nobody-1700")))
        planted("a relation the kit does not have", "C3", fl_edit=lambda fl: fam(fl)["connections"][0].update(relation="cousin of"))
        planted("a godparent that is only inferred", "C3", fl_edit=lambda fl: fam(fl)["connections"][1].update(relation="godparent of", grade="inf"))
        planted("a grade that is not doc, inf or lore", "F0", fl_edit=lambda fl: fam(fl)["connections"][0].update(grade="sure"))
        planted("a family that is connected and says it is not", "C4", fl_edit=lambda fl: fam(fl).update(notConnected={"why": "x"}))
        planted("a family with neither", "C4", fl_edit=lambda fl: fam(fl, 1).pop("notConnected"))
        planted("a not-connected block that does not say what is missing", "F0", fl_edit=lambda fl: fam(fl, 1).update(notConnected={"why": ""}))
        planted("the same pair connected twice", "C6", fl_edit=lambda fl: fam(fl)["connections"].append(dict(fam(fl)["connections"][0])))
        def living_party(fl):
            fam(fl)["cards"][2]["person"] = "anselm-brandt"
            fam(fl)["connections"].append({"ourSlug": "pieter-arden-1822", "ourGeneration": 2, "theirSlug": "anselm-brandt", "theirName": "Anselm Brandt", "relation": "sibling of", "grade": "lore",
                                           "storyHref": "/story/#ship", "note": "Born 3 May 1990, as the family says"})
        planted("a connection with a living party and a date in its note", "C5", fl_edit=living_party)
        planted("a story link to a chapter that is not there", "C7", fl_edit=lambda fl: fam(fl)["connections"][0].update(storyHref="/story/#no-such-chapter"))
        print("the built page")
        planted("a card missing a part of the card", "B1", hand=lambda d: _edit(d, "/brandt/", lambda h: h.replace('<span class="fr-y">1795–1860</span>', "", 1)))
        planted("a card the page does not draw", "B1", hand=lambda d: _edit(d, "/brandt/", lambda h: re.sub(r'<li class="fr-c[^>]*data-person="ilse-arden-nee-brandt-1795".*?</li>', "", h, count=1, flags=re.S)))
        planted("a person link that goes nowhere", "B3", hand=lambda d: shutil.rmtree(os.path.join(d, "people", "ilse-arden-nee-brandt-1795")))
        planted("a living card that shows a date", "B2", hand=lambda d: _edit(d, "/brandt/", lambda h: h.replace('<span class="fr-y"></span>', '<span class="fr-y">b. 1990</span>', 1)))
        planted("a direct-line card that is not tinted", "B4", hand=lambda d: _edit(d, "/brandt/", lambda h: h.replace(" is-ours", "", 1)))
        planted("a card tinted that is not on the direct line", "B4", hand=lambda d: _edit(d, "/brandt/", lambda h: h.replace('class="fr-c fr-c-inf" data-living="0"', 'class="fr-c fr-c-inf is-ours" data-living="0"', 1)))
        planted("a tint that does not say whom", "B4", hand=lambda d: _edit(d, "/brandt/", lambda h: h.replace(' data-ours="ilse-arden-nee-brandt-1795"', "", 1)))
        planted("a connection block missing", "B5", hand=lambda d: _edit(d, "/brandt/", lambda h: re.sub(r'<li class="fr-b fr-b-inf".*?</li>', "", h, count=1, flags=re.S)))
        planted("our side of a block not tinted", "B5", hand=lambda d: _edit(d, "/brandt/", lambda h: h.replace('class="fr-b-our is-ours"', 'class="fr-b-our"', 1)))
        planted("a block naming the wrong generation", "B5", hand=lambda d: _edit(d, "/brandt/", lambda h: h.replace('data-our-generation="1"', 'data-our-generation="5"', 1)))
        planted("a family that is not connected, with no block that says so", "B5", hand=lambda d: _edit(d, "/harrow/", lambda h: h.replace("Not connected to our line yet.", "Nothing.").replace('class="fr-nc"', 'class="x"')))
        planted("a ribbon with no legend", "B6", hand=lambda d: _edit(d, "/brandt/", lambda h: h.replace(LEGEND, "tinted")))
        planted("a page that is not built", "B1", hand=lambda d: shutil.rmtree(os.path.join(d, "harrow")))
        print("the whole site")
        planted("an is-ours on a page for someone not on the line", "O1", hand=lambda d: _edit(d, "/people/pieter-arden-1822/", lambda h: h.replace("<h1>", '<div class="x is-ours" data-ours="a-cousin">y</div><h1>', 1)))
        planted("an is-ours with no name behind it", "O1", hand=lambda d: _edit(d, "/harrow/", lambda h: h.replace('<li class="fr-c fr-c-doc"', '<li class="fr-c fr-c-doc is-ours"', 1)))
        planted("a story ribbon card on the line that is not tinted", "O2", hand=lambda d: _edit(d, "/story/", lambda h: h.replace(" is-ours", "", 1)))
        planted("a story ribbon card tinted that is not on the line", "O2", hand=lambda d: _edit(d, "/story/", lambda h: h.replace('class="st-rb is-ours" data-person="tomas-arden-1790" data-ours="tomas-arden-1790"', 'class="st-rb is-ours" data-person="tomas-arden-1790" data-ours="other"', 1)))
        planted("a person page of the line with no band", "O3", hand=lambda d: _edit(d, "/people/pieter-arden-1822/", lambda h: re.sub(r'<p class="ours-band.*?</p>', "", h, flags=re.S)))
        planted("a band on a page that is not that person's", "O3", hand=lambda d: _edit(d, "/harrow/", lambda h: h.replace("<main>", '<main><p class="ours-band is-ours" data-ours="tomas-arden-1790">x</p>', 1)))
        planted("a band with the wrong generation", "O3", hand=lambda d: _edit(d, "/people/pieter-arden-1822/", lambda h: h.replace("generation 2", "generation 9")))
        planted("tinted cards on a page with no legend", "O4", hand=lambda d: _edit(d, "/story/", lambda h: h.replace(LEGEND, "tinted")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = len(res) - sum(res)
    print("\ncheckfamilyribbon selftest: %d/%d ok%s" % (sum(res), len(res), "" if not bad else ", %d FAILED" % bad))
    return 0 if not bad else 1


def _edit(dist, page, fn):
    p = os.path.join(dist, page.strip("/"), "index.html")
    txt = open(p).read()
    new = fn(txt)
    if new == txt:
        raise SystemExit("selftest: the edit to %s changed nothing (the fault was not planted)" % page)
    open(p, "w").write(new)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--families")
    ap.add_argument("--direct")
    ap.add_argument("--story")
    ap.add_argument("--lines")
    ap.add_argument("--dist")
    ap.add_argument("--no-dist", action="store_true")
    ap.add_argument("--person-base", default="/people/")
    ap.add_argument("--story-page", default="/story/")
    ap.add_argument("--living")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.families or not a.direct:
        ap.error("--families and --direct are required")
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
