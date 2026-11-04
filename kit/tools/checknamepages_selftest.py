#!/usr/bin/env python3
"""Prove checknamepages.py can fail. Invented people only.  python3 kit/tools/checknamepages.py --selftest"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checknamepages as cn  # noqa: E402

PERSON = '<main><article data-person-page="1" data-living="%s"><h1>%s</h1></article></main>'
NAME = '<html><head><title>%s</title></head><body><main><h1>%s</h1>%s</main></body></html>'


def put(dist, url, html):
    d = os.path.join(dist, url.strip("/"))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def link(u):
    return '<a href="%s">x</a>' % u


def build(claim_h1, bearers, linked, extra_text="", living_slug=None, name_h1="Ana Zed"):
    """One name page about Ana Zed, with `bearers` person pages of that name and `linked` of them linked."""
    dist = tempfile.mkdtemp(prefix="checknamepages-")
    slugs = []
    for i, q in enumerate(bearers):
        url = "/people/ana-zed-%d/" % i
        put(dist, url, PERSON % ("1" if living_slug == i else "0", "Ana Zed" + q))
        slugs.append(url)
    put(dist, "/people/someone-else/", PERSON % ("0", "Bo Other"))
    put(dist, "/who/ana-zed/", NAME % ("Ana Zed", claim_h1 or name_h1, "".join(link(u) for u in slugs[:linked]) + extra_text))
    return dist


def run_case(shared=False, entry_class=None, **kw):
    dist = build(**kw)
    try:
        names, persons = cn.scan(dist, ["/who/"], ["/people/", "/person/"], entry_class)
        return cn.check(names, persons, shared), names, persons
    finally:
        shutil.rmtree(dist, ignore_errors=True)


def case_ok(label, cond, res):
    res.append(bool(cond))
    print("  %s  %s" % ("ok  " if cond else "FAIL", label))


def run():
    res = []
    (f, adv), names, persons = run_case(claim_h1="Ana Zed — 3 people of the name", bearers=["", " of Kokstad", " (b. 1900)"], linked=3)
    case_ok("a clean name page (claims 3, three person pages, all linked, a parenthesised qualifier and an «of» qualifier) passes", not f, res)
    case_ok("a person page of another name is not counted", len(persons) == 4 and names[0]["claim"] == 3, res)

    (f, adv), *_ = run_case(claim_h1="Ana Zed — 2 people of the name", bearers=["", " of Kokstad", " of Barkly East"], linked=3)
    case_ok("claims 2 and three person pages exist: a count finding that names the page and both numbers",
            any(x.startswith("count:") and "/who/ana-zed/" in x and "says 2" in x and "holds 3" in x for x in f), res)

    (f, adv), *_ = run_case(claim_h1="Ana Zed — 3 people of the name", bearers=["", " of Kokstad", " of Barkly East"], linked=1)
    case_ok("the number is right but two person pages are not linked: an unlinked finding that lists them",
            not any(x.startswith("count:") for x in f) and any(x.startswith("unlinked:") and "ana-zed-1" in x and "ana-zed-2" in x for x in f), res)

    (f, adv), *_ = run_case(claim_h1="Ana Zed", extra_text="<p>2 different people in this archive were called Ana Zed.</p>", bearers=["", " of Kokstad", " of Barkly East"], linked=3)
    case_ok("a claim in the body text (the Booyzen wording) is read: 2 against three pages fails", any(x.startswith("count:") for x in f), res)

    (f, adv), *_ = run_case(claim_h1="Ana Zed", bearers=["", " of Kokstad"], linked=2)
    case_ok("a name page that claims nothing is advisory only", not f and any("no number" in x for x in adv), res)

    (f, adv), *_ = run_case(claim_h1="Ana Zed", bearers=["", " of Kokstad", " of Barkly East"], linked=1)
    case_ok("a name page that claims nothing still owes its links: the unlinked person pages are a finding",
            not any(x.startswith("count:") for x in f) and any(x.startswith("unlinked:") for x in f) and any("no number" in x for x in adv), res)

    (f, adv), *_ = run_case(claim_h1="Ana Zed — 2 people of the name", extra_text="<p>3 people of this name</p>", bearers=["", " of Kokstad"], linked=2)
    case_ok("a page that says two different numbers is a finding", any("in different places" in x for x in f), res)

    (f, adv), *_ = run_case(claim_h1="Ana Zed — 3 people of the name", bearers=["", " of Kokstad"], linked=1, living_slug=1)
    case_ok("a living person's page is counted but never named in a message",
            any(x.startswith("count:") for x in f) and any("living person" in x and "not named" in x for x in f) and not any("ana-zed-1" in x for x in f), res)

    # BOOYZEN'S SHAPE: one person page holds several men of a shared name, so «4 people» over three pages is clean
    three = ["", " of Kokstad", " of Barkly East"]
    entries4 = "".join('<div class="mate">x</div>' for _ in range(4))
    (f, adv), *_ = run_case(claim_h1="Ana Zed — 4 people of the name", bearers=three, linked=3, shared=True, entry_class="mate", extra_text=entries4)
    case_ok("shared pages: 4 people on 3 person pages, 4 entries listed, all linked, is clean", not f, res)
    (f, adv), *_ = run_case(claim_h1="Ana Zed — 4 people of the name", bearers=three, linked=3)
    case_ok("the same page is a count finding when the archive does not allow shared pages", any(x.startswith("count:") for x in f), res)
    (f, adv), *_ = run_case(claim_h1="Ana Zed — 2 people of the name", bearers=three + [" of Wells"], linked=1, shared=True)
    case_ok("shared pages: claim 2, four person pages, one linked, fails on the count and on the links",
            any(x.startswith("count:") for x in f) and any(x.startswith("unlinked:") for x in f), res)
    (f, adv), *_ = run_case(claim_h1="Ana Zed — 4 people of the name", bearers=three, linked=3, shared=True, entry_class="mate",
                            extra_text="".join('<div class="mate">x</div>' for _ in range(3)))
    case_ok("shared pages: claims 4 and lists 3 entries is a finding", any(x.startswith("entries:") for x in f), res)
    (f, adv), *_ = run_case(claim_h1="Ana Zed — One person of the name", bearers=["", " of Kokstad"], linked=2, shared=True)
    case_ok("«One person» with two person pages fails even where pages may be shared", any(x.startswith("count:") for x in f), res)

    case_ok("accents and case are folded when a person page is matched to a name", cn.belongs("ANA ZÉD (b. 1900)", "Ana Zed") and cn.belongs("Ana Zed of Kokstad", "ana zed"), res)
    case_ok("a longer name is not a bearer of a shorter one", not cn.belongs("Ana Zedler", "Ana Zed") and not cn.belongs("Maria Ana Zed", "Ana Zed"), res)

    d = tempfile.mkdtemp(prefix="checknamepages-")
    try:
        case_ok("an empty build is refused, not passed (exit 2)", cn.main(["--dist", d]) == 2, res)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\nall %d cases behave" % len(res) if all(res) else "\n%d FAILED" % res.count(False))
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(run())
