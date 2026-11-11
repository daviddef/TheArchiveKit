#!/usr/bin/env python3
"""The ribbon, the search box and /whats-new/ say what they count (kit/docs/whats-new.md).

    python3 checkpulse.py --dist dist            (run from the site directory, after the build)
    python3 checkpulse.py --selftest             (plants each fault in a tiny site and shows it is refused)

WHAT IT REFUSES
  page     no built /whats-new/ page, or one with no timeline at all (a gate that examined nothing has not passed)
  badge    the «N searches» badge is not the number of rows the page draws, or the «N corrected» badge is not the number of correction cards
  ribbon   a built page (home, /whats-new/) without exactly one .pulse ribbon, without its link to /whats-new/, or without a data-search-open button
  popup    a page without exactly one search box (#sdlg), or the old header «Search» pill (class findbtn) still beside the magnifier
  card     a timeline card with no link to a page that exists in the build
Prints counts, never a person's name.
"""
import os
import re
import sys
import argparse
import tempfile

LINK = re.compile(r'<a\b[^>]*\bhref="([^"]+)"')


def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def built(dist, href):
    h = href.split("#")[0].split("?")[0]
    if not h.startswith("/"):
        return True
    t = os.path.join(dist, h.lstrip("/"))
    return os.path.exists(t) or os.path.exists(os.path.join(t, "index.html")) or os.path.exists(t + ".html")


def check(dist, base=""):
    out, bad = [], []
    page = os.path.join(dist, "whats-new", "index.html")
    if not os.path.exists(page):
        return [], ["page: no built /whats-new/ page"]
    html = read(page)
    rows = len(re.findall(r'class="wn-row"', html))
    items = len(re.findall(r'class="wn-day"', html))
    if not items:
        bad.append("page: /whats-new/ has no timeline days")
    m = re.search(r'<b>[^<]*</b>\s*(?:entries since)', html)
    ms = re.search(r'([\d,]+) searches</button>', html)
    mc = re.search(r'([\d,]+) corrected</button>', html)
    if ms and int(ms.group(1).replace(",", "")) != rows:
        bad.append("badge: «%s searches» but the page draws %d rows" % (ms.group(1), rows))
    ncor = len(re.findall(r'data-type="corrected"', html))
    if (mc and int(mc.group(1).replace(",", "")) != ncor) or (not mc and ncor):
        bad.append("badge: the corrected badge says %s and the page draws %d correction cards" % (mc.group(1) if mc else "nothing", ncor))
    for h in set(LINK.findall(html)):
        if h.startswith("/") and not built(dist, h.replace(base, "", 1) if base and h.startswith(base) else h):
            bad.append("card: link to a page that is not built: " + h)
    for name, p in (("home", os.path.join(dist, "index.html")), ("whats-new", page)):
        if not os.path.exists(p):
            continue
        t = read(p)
        if t.count('class="pulse"') != 1:
            bad.append("ribbon: %s has %d .pulse ribbons, not 1" % (name, t.count('class="pulse"')))
        if "/whats-new/" not in t:
            bad.append("ribbon: %s has no link to /whats-new/" % name)
        if "data-search-open" not in t:
            bad.append("ribbon: %s has no data-search-open button" % name)
        if t.count('id="sdlg"') != 1:
            bad.append("popup: %s has %d search boxes, not 1" % (name, t.count('id="sdlg"')))
        if 'class="findbtn"' in t:
            bad.append("popup: %s still carries the old Search pill (findbtn)" % name)
    out.append("pulse: /whats-new/ %d days, %d research rows, %d correction cards; ribbon and search box on home and /whats-new/" % (items, rows, ncor))
    return out, bad


def selftest():
    good_wn = ('<html><body><div class="pulse"><a href="/whats-new/"></a><button data-search-open></button></div><div id="sdlg"></div>'
               '<button>2 searches</button><button>1 corrected</button><li class="wn-day"><div class="wn-row"></div><div class="wn-row"></div>'
               '<li data-type="corrected"></li></li></body></html>')
    good_home = '<html><body><div class="pulse"><a href="/whats-new/"></a><button data-search-open></button></div><div id="sdlg"></div></body></html>'
    plants = {
        "none": (good_wn, good_home, False),
        "badge": (good_wn.replace("2 searches", "3 searches"), good_home, True),
        "no-corr-badge": (good_wn.replace("<button>1 corrected</button>", ""), good_home, True),
        "two-popups": (good_wn, good_home.replace('<div id="sdlg"></div>', '<div id="sdlg"></div><div id="sdlg"></div>'), True),
        "old-pill": (good_wn, good_home + '<a class="findbtn"></a>', True),
        "no-ribbon": (good_wn, good_home.replace('class="pulse"', 'class="x"'), True),
        "no-timeline": (good_wn.replace('class="wn-day"', 'class="z"'), good_home, True),
    }
    ok = True
    for name, (wn, home, should_fail) in plants.items():
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "whats-new"))
        open(os.path.join(d, "whats-new", "index.html"), "w").write(wn)
        open(os.path.join(d, "index.html"), "w").write(home)
        r = check(d)
        failed = bool(r[1])
        if failed != should_fail:
            ok = False
            print("  FAIL  selftest %s: expected %s, got %s %s" % (name, "refusal" if should_fail else "pass", "refusal" if failed else "pass", r[1]))
        else:
            print("  ok    selftest %s: %s" % (name, "refused" if failed else "passes"))
    if check(tempfile.mkdtemp())[1] != ["page: no built /whats-new/ page"]:
        ok = False
        print("  FAIL  selftest empty: an empty build must be refused")
    else:
        print("  ok    selftest empty: an empty build is refused")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--base", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    out, bad = check(a.dist, a.base)
    for o in out:
        print("  ok    " + o)
    for b in bad:
        print("  FAIL  " + b)
    sys.exit(1 if bad else 0)
