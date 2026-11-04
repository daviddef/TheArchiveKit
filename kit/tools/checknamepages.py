#!/usr/bin/env python3
"""Does a NAME page say how many people carry the name, and is it right?

Every archive has two kinds of page about a name. A PERSON page is one man or woman (`/people/george-mountjoy-of-kokstad/`).
A NAME page (`/who/george-mountjoy/`) gathers everyone called that and says how many there are: «2 people of this name».
The number is written by the archive, from a list the archive keeps, and the list and the pages drift apart.

  5 November 2026, Defranceski: /who/ivan-defranceski/ said «3 people of the name» and the archive holds FIVE Ivan Defranceski
    pages. 561 of 2,022 roster rows (register reads, newspapers, household reconstructions) had a person page and had never
    been joined to a name page, so the name page did not count them. 518 name pages were wrong.
  Booyzen, the same day: /who/george-mountjoy/ said «2 people», three person pages exist, and the name page linked ONE.
    /who/george-augustus-kolbe/ said «3», there are six.

A reader who chooses a person and lands on a page that says «3 people» when five exist is told, by the archive, that it has
lost two people. A search engine is told the same thing, and (where the page has one bearer) is pointed at the wrong canonical.

WHAT THIS READS. The BUILD, not the data (ARCHIVE_OUT beats --dist: see outdir.py). It reads this archive only.
  1. every page under a NAME prefix (default /who/), which is a name page;
  2. the number it CLAIMS: the first match of any wording in CLAIMS, looked for in the h1, then the title, then the main text;
  3. the person pages (a page with `data-person-page`) under the PERSON prefixes (default /people/ and /person/) that BELONG to
     the name: their h1, accents and case folded, is the name, or the name followed by a parenthesised qualifier, or by
     « of <place or year>» (Booyzen's «George Mountjoy of Kokstad», Falco's «Pasquale Falco of Angelo Falco…»);
  4. which of those the name page LINKS to.

WHAT IT FAILS ON (each is one finding, and each names the page)
  count     the page claims N and the build holds M person pages of that name. By default N must EQUAL M. With
            --allow-shared-pages (Booyzen, where one person page holds several men of a shared name, a chart for each) N must be
            AT LEAST M, and with --entry-class (the class of one person's card or row on the name page) it must EQUAL the
            number of entries listed. «One person» against two pages fails in both modes.
  unlinked  the name page does not link to a person page of its name (the list of them is printed)
It is ADVISORY about a name page that claims no number at all (a name page may say nothing), and says how many; but a name
page that says nothing still owes its links, so «unlinked» is checked on every name page.

EXIT CODES. 0 clean (or within --max); 1 findings; 2 it could not SEE what it checks: no name page, no person page, or the
build directory is missing. A check that finds nothing because it looked in the wrong place has not found that nothing is wrong.
`--max N` is a ratchet for an archive that starts with findings: fail only when they rise above N.
`--advisory` reports and exits 0 for the same reason checkperson.py does.

LIVING PEOPLE. A living person's page is counted like any other (the name page counts them too) but is never NAMED here: a
slug can end in a birth year, and a living person has no years in a message. They are reported as «a living person's page».

A NEW WORDING is one line in CLAIMS. Nothing else in this file knows how a claim is phrased.
"""
import argparse
import html
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outdir  # noqa: E402

# The wordings seen so far: Defranceski «Ivan Defranceski — 3 people of the name» (h1 and title), Booyzen «2 people of this name»
# and «2 different people in this archive were called George Mountjoy». The number is the first group.
# A number is digits or a word (one to ten): «One person of this name» is a claim of 1.
_N = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
CLAIMS = [
    r"\b" + _N + r" different people of this name\b",
    r"\b" + _N + r" different people in this archive were called\b",
    r"\b" + _N + r" (?:people|person) of (?:the|this) name\b",
    r"\bholds " + _N + r" people called\b",
]
_CLAIM = [re.compile(p, re.I) for p in CLAIMS]
WORDS = {w: i + 1 for i, w in enumerate("one two three four five six seven eight nine ten".split())}


def number(x):
    return int(x) if x.isdigit() else WORDS[x.lower()]


def fold(s):
    s = unicodedata.normalize("NFD", html.unescape(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def pages_under(dist, prefix):
    """(url, html) for every index.html under dist/<prefix>/ (one level of directory per page)."""
    root = os.path.join(dist, prefix.strip("/"))
    out = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name, "index.html")
        if os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                out.append(("/%s/%s/" % (prefix.strip("/"), name), f.read()))
    return out


def h1_of(page):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    return text_of(m.group(1)) if m else ""


def claim_of(page):
    """(number or None, [every distinct number found]). The first number is the h1's, else the title's, else the text's; the
    list is every distinct number in all three, so a page that says two different things is seen."""
    sources = []
    m = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    if m:
        sources.append(text_of(m.group(1)))
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    if m:
        sources.append(text_of(m.group(1)))
    m = re.search(r"<main.*?</main>", page, re.S)
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", m.group(0) if m else page, flags=re.S)
    sources.append(text_of(body))
    found = []
    for src in sources:
        for rx in _CLAIM:
            for mm in rx.finditer(src):
                found.append(number(mm.group(1)))
    return (found[0] if found else None), sorted(set(found))


def name_of(page):
    """The name a name page is about: its h1 before any « — » claim."""
    return re.split(r"\s+[—–-]\s+", h1_of(page))[0].strip()


def belongs(person_h1, name):
    """Is this person page one of the bearers of the name? Folded h1 equals the name, or the name plus a parenthesised
    qualifier, or the name plus « of …»."""
    a = fold(re.sub(r"\s*\(.*?\)\s*$", "", person_h1))
    n = fold(name)
    return bool(n) and (a == n or a.startswith(n + " of "))


def entries_of(page, entry_class):
    """How many entries (cards or rows, one per person) the name page lists, when the archive says which class marks one."""
    if not entry_class:
        return None
    return len(re.findall(r'class="[^"]*\b%s\b[^"]*"' % re.escape(entry_class), page))


def scan(dist, who_prefixes, person_prefixes, entry_class=None):
    persons = []
    for pre in person_prefixes:
        for url, page in pages_under(dist, pre):
            if "data-person-page" not in page:
                continue
            persons.append({"url": url, "h1": h1_of(page), "living": bool(re.search(r'data-living="1"', page))})
    names = []
    for pre in who_prefixes:
        for url, page in pages_under(dist, pre):
            if "data-person-page" in page:
                continue                                    # a person page that lives under the name prefix is not a name page
            links = set(re.findall(r'href="(/[^"#?]+/)"', page))
            n, found = claim_of(page)
            names.append({"url": url, "name": name_of(page), "claim": n, "claims": found, "links": links,
                          "entries": entries_of(page, entry_class)})
    return names, persons


def label(p):
    return "a living person's page" if p["living"] else p["url"]


def check(names, persons, shared=False):
    """(findings, advisories). A finding is one line naming the name page.

    shared=False: one person page is one person, so the claim must EQUAL the number of person pages of the name.
    shared=True: an archive may hold several men of a shared name on ONE page (Booyzen puts a chart for each on it), so the
    claim must be AT LEAST the number of person pages, and, where the name page lists its people as entries, EQUAL to the
    number of entries. «One person» against two pages fails either way."""
    findings, advisories, silent = [], [], 0
    for nm in names:
        bearers = [p for p in persons if belongs(p["h1"], nm["name"])]
        if nm["claim"] is None:
            silent += 1                                      # no number to be wrong; the links below are still owed
        else:
            if len(nm["claims"]) > 1:
                findings.append("%s says %s people in different places" % (nm["url"], " and ".join(map(str, nm["claims"]))))
            if not shared and nm["claim"] != len(bearers):
                findings.append("count: %s says %d people of the name and the build holds %d person pages of it"
                                % (nm["url"], nm["claim"], len(bearers)))
            if shared and nm["claim"] < len(bearers):
                findings.append("count: %s says %d people of the name and the build holds %d person pages of it (a page may hold "
                                "several people, never fewer than one)" % (nm["url"], nm["claim"], len(bearers)))
            if shared and nm.get("entries") is not None and nm["entries"] != nm["claim"]:
                findings.append("entries: %s says %d people and lists %d" % (nm["url"], nm["claim"], nm["entries"]))
        missing = [p for p in bearers if p["url"] not in nm["links"]]
        if missing:
            living = sum(1 for p in missing if p["living"])
            named = [p["url"] for p in missing if not p["living"]]
            findings.append("unlinked: %s does not link to %d of its %d person pages: %s%s"
                            % (nm["url"], len(missing), len(bearers), ", ".join(named) or "none that may be named",
                               ("; and %d living person%s (not named)" % (living, "" if living == 1 else "s")) if living else ""))
    if silent:
        advisories.append("%d name page%s claim%s no number (advisory only)" % (silent, "" if silent == 1 else "s", "s" if silent == 1 else ""))
    return findings, advisories


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--who-prefix", action="append", default=None, help="name pages live under this prefix (default /who/); repeatable")
    ap.add_argument("--person-prefix", action="append", default=None, help="person pages live under this prefix (default /people/ and /person/); repeatable")
    ap.add_argument("--allow-shared-pages", action="store_true",
                    help="one person page may hold several people of a shared name: the claim must be at least the number of pages")
    ap.add_argument("--entry-class", default=None,
                    help="the CSS class of one person's entry (card or row) on a name page; with --allow-shared-pages the claim must equal the entries")
    ap.add_argument("--max", type=int, default=None, help="ratchet: fail only if findings exceed this")
    ap.add_argument("--advisory", action="store_true", help="report and exit 0")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        import checknamepages_selftest
        return checknamepages_selftest.run()
    dist = outdir.resolve(a.dist)
    who = a.who_prefix or ["/who/"]
    per = a.person_prefix or ["/people/", "/person/"]
    if not os.path.isdir(dist):
        print("checknamepages: %s is not a directory; nothing was checked" % dist)
        return 2
    before = outdir.fingerprint(dist)
    names, persons = scan(dist, who, per, a.entry_class)
    if outdir.settled(dist, before, "namepages"):
        return 2
    if outdir.note(dist):
        print(outdir.note(dist))
    if not names:
        print("checknamepages: no name page under %s in %s; nothing was checked" % (", ".join(who), dist))
        return 2
    if not persons:
        print("checknamepages: no person page (data-person-page) under %s in %s; nothing was checked" % (", ".join(per), dist))
        return 2
    findings, adv = check(names, persons, a.allow_shared_pages)
    for f in findings:
        print("  FAIL  " + f)
    for x in adv:
        print("  note  " + x)
    print("checknamepages: %d name pages, %d person pages, %d finding%s" % (len(names), len(persons), len(findings), "" if len(findings) == 1 else "s"))
    if a.advisory:
        return 0
    if a.max is not None:
        return 1 if len(findings) > a.max else 0
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
