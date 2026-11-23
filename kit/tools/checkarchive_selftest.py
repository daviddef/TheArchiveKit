#!/usr/bin/env python3
"""Prove checkarchive.py reads a percent-encoded accent in a link, and still fails what it should.

Astro writes the target and canonical of a redirect to a slug that is not plain ASCII percent-encoded
(/people/alfia-cannav%C3%B2/), and the sitemap the same; the built page is a directory under the accent itself
(dist/people/alfia-cannavò/). checkarchive.py looked an encoded href up as written, so the links check reported
"no such page" for a page that is built and correct, and the crawl never reached it. Each case builds a small dist
in a temporary directory with ONE departure and runs the real script on it.

    python3 kit/tools/checkarchive_selftest.py
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "checkarchive.py")

ACC = "alfia-cannavò"            # a slug with o grave, as the folder is named
ENC = "alfia-cannav%C3%B2"            # the same, as Astro writes it in an href, a canonical, a sitemap <loc>
FILLER = 16                           # the script refuses a dist under 15 pages


def page(title, body="", head=""):
    return "<!doctype html><html><head><title>%s</title>%s</head><body>%s</body></html>" % (title, head, body)


def write(dist, route, text):
    d = os.path.join(dist, route.strip("/"))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html") if route.strip("/") else os.path.join(dist, "index.html"), "w", encoding="utf-8") as f:
        f.write(text)


def build(links=(), stub_to=None, sitemap=(), person_body=None):
    """A dist: a home page linking to `links`, filler pages, an accented person page, an optional /who/ redirect."""
    dist = tempfile.mkdtemp(prefix="checkarchive-")
    anchors = "".join('<a href="/filler/%d/">f%d</a>' % (i, i) for i in range(FILLER))
    anchors += "".join('<a href="%s">x</a>' % h for h in links)
    write(dist, "/", page("Home", anchors))
    for i in range(FILLER):
        write(dist, "/filler/%d/" % i, page("Filler %d" % i, "<p>x</p>"))
    write(dist, "/people/" + ACC + "/", page("The person", person_body or '<h2 id="notes">Notes</h2>'))
    if stub_to is not None:
        write(dist, "/who/alfia-cannavo/", page(
            "Redirecting to: " + stub_to,
            head='<meta http-equiv="refresh" content="0;url=%s"><meta name="robots" content="noindex">'
                 '<link rel="canonical" href="%s">' % (stub_to, stub_to)))
    if sitemap:
        with open(os.path.join(dist, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0"?><urlset>%s</urlset>'
                    % "".join("<url><loc>https://example.org%s</loc></url>" % u for u in sitemap))
    return dist


def run(dist):
    p = subprocess.run([sys.executable, TOOL, "--dist", dist, "--base", ""], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, p.stdout


bad = 0


def case(name, ok, out=""):
    global bad
    print("  %s  %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        bad += 1
        print("        " + out.strip().replace("\n", "\n        ")[:900])


print("an accent in a slug, written percent-encoded")
rc, out = run(build(links=["/people/" + ACC + "/"]))
case("the accent written as the folder is named passes", rc == 0, out)
rc, out = run(build(links=["/people/%s/" % ENC]))
case("a link to the encoded address of a built page passes", rc == 0, out)
rc, out = run(build(links=["/people/%s/#notes" % ENC]))
case("an encoded link with a fragment that exists passes", rc == 0, out)
rc, out = run(build(links=["/people/%s/" % ENC]))
case("a page linked only by its encoded address is reached (no orphan)", "nothing links to it" not in out and "does not link" not in out, out)
rc, out = run(build(stub_to="/people/%s/" % ENC))
case("a redirect whose canonical is the encoded address of a built page passes", rc == 0, out)
rc, out = run(build(sitemap=["/", "/people/%s/" % ENC]))
case("a sitemap that lists the encoded address of a built page passes", rc == 0, out)

print("what still fails")
rc, out = run(build(links=["/people/%s/" % ENC.replace("%B2", "%B3")]))
case("an encoded link naming a different accent (o acute, not o grave) fails", rc == 1 and "no such page" in out, out)
rc, out = run(build(links=["/people/alfia-cannavo/"]))
case("a link with the accent dropped fails (an accent is a spelling)", rc == 1 and "no such page" in out, out)
rc, out = run(build(links=["/people/alfia-cannav%C3%B2-gone/"]))
case("an encoded link to a page that is not built fails", rc == 1 and "no such page" in out, out)
rc, out = run(build(links=["/people/%s/#missing" % ENC]))
case("an encoded link to a fragment that is not on the page fails", rc == 1 and "#missing" in out, out)
rc, out = run(build(stub_to="/people/%s-gone/" % ENC))
case("a redirect whose encoded canonical leads to nothing built fails", rc == 1 and "no such page" in out, out)
rc, out = run(build(sitemap=["/", "/people/%s-gone/" % ENC]))
case("a sitemap that lists an encoded address that is not built fails", rc == 1 and "sitemap" in out, out)

print("checkarchive selftest: %s" % ("ok" if not bad else "%d FAILED" % bad))
sys.exit(1 if bad else 0)
