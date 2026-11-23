#!/usr/bin/env python3
"""Prove sitemap.py and menu_inventory.py read a percent-encoded address the way a browser does, and can still fail.
Invented fixtures only. (checkbook.py's own case for the same thing is in checkbook_selftest.py.)

Astro writes a redirect target and a canonical for a slug with an accent percent-encoded (/people/alfia-cannav%C3%B2/),
while the built page is a directory in dist under the unencoded name. Compared as written, they never matched.

    python3 kit/tools/redirect_slugs_selftest.py"""
import os, sys, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import menu_inventory as mi

res = []
def case(label, ok, detail=""):
    res.append(bool(ok)); print("  %s  %s%s" % ("ok  " if ok else "FAIL", label, ("  [" + str(detail)[:200] + "]") if detail and not ok else ""))

ACC = "alfia-cannavò"
ENC = "alfia-cannav%C3%B2"

def write(root, rel, html):
    d = os.path.join(root, rel.strip("/")); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(html)

def page(canon=None):
    link = '<link rel="canonical" href="%s">' % canon if canon else ""
    return "<html><head>%s<title>x</title></head><body><main><p>a page that says something</p></main></body></html>" % link

print("sitemap.py: the canonical of an accented page")
def sitemap(canon):
    t = tempfile.mkdtemp(prefix="smap-")
    try:
        site = os.path.join(t, "site"); os.makedirs(os.path.join(site, "public"))
        open(os.path.join(site, "astro.config.mjs"), "w").write("export default { site: 'https://x.example', };\n")
        dist = os.path.join(site, "dist")
        write(dist, "/", page())
        write(dist, "/people/%s/" % ACC, page(canon))
        write(dist, "/people/other/", page("https://x.example/people/somewhere-else/"))
        r = subprocess.run([sys.executable, os.path.join(HERE, "sitemap.py"), "--dist", dist], cwd=site, capture_output=True, text=True,
                           env=dict(os.environ, ARCHIVE_OUT=""))
        xml = open(os.path.join(dist, "sitemap.xml"), encoding="utf-8").read() if os.path.exists(os.path.join(dist, "sitemap.xml")) else ""
        return r, xml
    finally:
        shutil.rmtree(t, ignore_errors=True)
r, xml = sitemap("https://x.example/people/%s/" % ENC); case("an accented page whose canonical is percent-encoded stays in the sitemap", ACC in xml, r.stdout + r.stderr)
r, xml = sitemap("https://x.example/people/%s/" % ACC); case("the same page with an unencoded canonical stays too", ACC in xml, r.stdout + r.stderr)
r, xml = sitemap("https://x.example/people/somewhere-else/"); case("a canonical naming another page still withholds the page", ACC not in xml and "withheld (canonical names another page)" in r.stdout, r.stdout + r.stderr)
r, xml = sitemap("https://x.example/people/alfia-cannav%C3%B3/"); case("a canonical with a different accent still withholds the page", ACC not in xml, r.stdout + r.stderr)
r, xml = sitemap("https://x.example/people/other/"); case("the page that canonicalises elsewhere (other) is never listed", "people/other/" not in xml, xml)

print("menu_inventory.py: an old address that leads on through a percent-encoded redirect")
t = tempfile.mkdtemp(prefix="minv-")
try:
    stub = '<html><head><meta http-equiv="refresh" content="0; url=%s"></head><body></body></html>'
    write(t, "/people/%s/" % ACC, page())
    write(t, "/who/%s/" % ACC, stub % ("/people/%s/" % ENC))
    write(t, "/who/gone/", stub % ("/people/%s/" % "nobody-built"))
    write(t, "/who/wrong/", stub % "/people/alfia-cannav%C3%B3/")
    ok, fin, kind = mi.resolve(t, "/who/%s/" % ACC); case("an old address whose redirect target is percent-encoded answers", ok and kind == "redirect", (ok, fin, kind))
    ok, fin, kind = mi.resolve(t, "/who/gone/"); case("a redirect to nothing built still does not answer", not ok, (ok, fin, kind))
    ok, fin, kind = mi.resolve(t, "/who/wrong/"); case("an encoded target with the wrong accent still does not answer", not ok, (ok, fin, kind))
finally:
    shutil.rmtree(t, ignore_errors=True)

bad = res.count(False)
print("\nall %d cases behave" % len(res) if not bad else "\n%d FAILED" % bad)
sys.exit(1 if bad else 0)
