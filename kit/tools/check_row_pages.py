#!/usr/bin/env python3
"""A found row must say which page of the archive the finding went into.

WHY (David, 12 November 2026: "required for new found rows"). What's new shows, under each search row, the pages the finding went into
(the row's `ev`, kit/lib/pulse.js) and whether the Record Atlas has it. A finding that was read and written into nothing is the fault: it sits in
the log and the archive's pages never say it. So, from a date the archive chooses, every row of searched.json that READS AS FOUND must have

    "ev": [["/path/", "label"], ...]     with at least one path that is a built page of this archive,
 or "logOnly": true                       (the finding is meant to stay in the log; the reason goes in `what`).

Rows before that date are not checked. The date is the archive's, in docs/row-pages.json:

    {"from": "2026-11-12"}                         the gate, on from that day
    {"from": "2026-11-12", "outcomeMap": {"done": "found"}}     an outcome word this archive uses that the kit does not know (as buildPulse's outcomeMap)
    {"from": "2026-11-12", "fields": {"when": ["searchedOn"]}}  the column this archive keeps the work date in, when it is not `when`/`date` (as buildPulse's `fields`:
                                                               a list given here REPLACES the kit's list for that key, exactly as there; keys read: when, outcome, cwhen).
                                                               An archive whose pulse adapter sets `fields` MUST set the same here, or the gate reads the wrong date and checks nothing.

    {"from": "2026-11-12", "peopleFrom": "2026-11-14"}          from that day a found row must also say WHO it is for (below)

WHO (David, 14 November 2026): What's new shows, under a found row, the people the finding is for. From `peopleFrom` (off when the key is absent) every row that
READS AS FOUND must carry

    "for": [["/person/slug/", "Name"], ...]     each path a built page of this archive (the archive's own page for that person), each with a name, none twice,
 or "nobody": true                             the pages were read and no new person came out of them (the reason may go in `what`).

Only people the archive already publishes can be listed: the path must be a built page, so a living person, who has none, cannot be named. `for` and `nobody` together fail.

DEEP LINKS (David, 22 November 2026: "why does a what's-new link not take me directly to the change?"). A link to the top of a 1.6 MB page is not a link to the
finding. From `deepFrom` (off when the key is absent; it must be on or after `from`) every ev entry of a found row must send the reader to the PASSAGE:

    "ev": [["/page/#anchor", "label"], ["/page/", "label", "a phrase as the reader sees it on the page"]]

  * an anchor (`#id`) must be an `id` (or `name`) in the built page;
  * a phrase (third item, plain text, 3-120 characters, no * _ ` or [..](..)) must occur EXACTLY ONCE in the page's visible text (case and spacing as the browser
    matches them); What's new turns it into a text fragment (#:~:text=...), which a browser scrolls to and highlights with no id in the page, and which an
    old browser ignores (it opens the page: the link never breaks). Twice is a fault: the link would land on the first, which may not be the change;
  * a page larger than `deepMinKb` (default 100) KB of HTML must carry one or the other: the top of a long page is not the change. Small pages may stay bare.
  {"from": "2026-11-12", "deepFrom": "2026-11-23", "deepMinKb": 100}

No docs/row-pages.json = the gate is OFF (exit 0, and it says so): an archive turns it on in its pin-bump PR.

"Found" is decided exactly as lib/pulse.js decides it (the same OUTCOME words, the same dates, the same field names); kit/tools/receipts_logic.mjs
runs both on the same words and dates and fails if they disagree. A row whose date pulse.js cannot read is not on /whats-new/ and is not checked here.

ADVISORY ONLY: a correction (corrections.json) dated from the same day whose `where` names a path (/imotski/) that is not a built page is a WARNING,
not a failure.

    python3 check_row_pages.py --dist dist [--searched src/data/searched.json] [--config ../docs/row-pages.json] [--corrections src/data/corrections.json]
    python3 check_row_pages.py --selftest        (check_row_pages_selftest.py does the same)

Defaults: searched.json is src/data/searched.json, or site/src/data/searched.json from the repo root; the config is docs/row-pages.json or ../docs/row-pages.json.
Without --dist the paths are only checked for shape (a "/" path), and it says the pages were not verified.
"""
import argparse
import datetime
import html as htmllib
import json
import os
import re
import sys
import unicodedata

# --- the same words and dates as kit/lib/pulse.js (receipts_logic.mjs holds the two together) ---
OUTCOME = {
    "hit": "found", "yield": "found", "found": "found",
    "nothing": "nil", "nil": "nil", "miss": "nil", "clean": "nil", "null": "nil", "empty": "nil",
    "partial": "partial", "part": "partial", "mixed": "partial",
    "blocked": "blocked", "correction": "corrected",
}
FIELDS = {"when": ["when", "date"], "outcome": ["outcome", "status"], "cwhen": ["when", "date"]}
MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def outcome_of(word, omap=None):
    """pulse.js outcomeOf: the mapped word, else 'no ...' / 'not there' / 'nothing...' is nil, else None (left out, not guessed)."""
    m = dict(OUTCOME)
    m.update(omap or {})
    w = ("" if word is None else str(word)).strip().lower()
    if w in m:
        return m[w]
    if re.match(r"^(no |not there|nothing)", w):
        return "nil"
    return None


def parse_when(s):
    """pulse.js parseWhen: '2026-11-11', '2026-11', '11 Nov 2026', '5 October 2026', 'Sept 2026' -> (iso, exact); anything else None."""
    t = ("" if s is None else str(s)).strip()
    m = re.match(r"^(\d{4})-(\d{2})(?:-(\d{2}))?(?:$|[T\s])", t)
    if m:
        mo = int(m.group(2))
        if mo < 1 or mo > 12:
            return None
        return ("%s-%s-%s" % (m.group(1), m.group(2), m.group(3) or "01"), bool(m.group(3)))
    m = re.match(r"^(?:(\d{1,2})\s+)?([A-Za-z]{3,})\.?\s+(\d{4})$", t)
    if not m:
        return None
    mo = MON.get(m.group(2)[:3].lower())
    if mo is None:
        return None
    day = int(m.group(1)) if m.group(1) else 1
    return ("%s-%02d-%02d" % (m.group(3), mo, day), bool(m.group(1)))


def rows_of(x):
    """pulse.js rowsOf: an array, {rows: []} or {searched: []}; a row with `_note` (a note to the reader) is not an entry."""
    if isinstance(x, list):
        a = x
    elif isinstance(x, dict) and isinstance(x.get("rows"), list):
        a = x["rows"]
    elif isinstance(x, dict) and isinstance(x.get("searched"), list):
        a = x["searched"]
    else:
        a = []
    return [r for r in a if isinstance(r, dict) and "_note" not in r]


def first(r, keys):
    for k in keys:
        if r.get(k) is not None and r.get(k) != "":
            return r[k]
    return ""


def page_exists(dist, path):
    """A site-root path ('/imotski/', '/imotski/#x', '/page.html') is a built page: dist/<path>/index.html (or the .html file itself)."""
    p = re.split(r"[#?]", path, maxsplit=1)[0]
    if not p.startswith("/") or p.startswith("//"):
        return False
    rel = p.strip("/")
    if p.endswith(".html"):
        return os.path.isfile(os.path.join(dist, rel))
    return os.path.isfile(os.path.join(dist, rel, "index.html")) if rel else os.path.isfile(os.path.join(dist, "index.html"))


def ev_paths(r):
    out = []
    for e in r.get("ev") if isinstance(r.get("ev"), list) else []:
        if isinstance(e, list) and e and isinstance(e[0], str) and e[0].startswith("/") and not e[0].startswith("//"):
            out.append(e[0])
    return out


BLOCK_CLOSE = re.compile(r"</(?:p|div|li|ul|ol|h[1-6]|tr|td|th|table|section|article|blockquote|figure|figcaption|dd|dt|dl|summary|details|header|footer|nav|main|aside|pre|form|label|button|option|select)\s*>|<br\s*/?>|<hr\s*/?>", re.I)


def norm(s):
    return " ".join(unicodedata.normalize("NFC", s).casefold().split())


def visible_lines(html):
    """The page's text as a reader gets it, one line per block (a text fragment cannot match across blocks): no scripts, styles, templates, head or comments."""
    h = re.sub(r"(?is)<(script|style|template|noscript|head|svg)\b.*?</\1\s*>", " ", html)
    h = re.sub(r"(?s)<!--.*?-->", " ", h)
    h = BLOCK_CLOSE.sub("\n", h)
    h = re.sub(r"(?s)<[^>]*>", "", h)
    return [l for l in (norm(htmllib.unescape(x)) for x in h.split("\n")) if l]


def anchor_exists(html, a):
    q = re.escape(a)
    return re.search(r"""\s(?:id|name)=(?:"%s"|'%s'|%s(?=[\s>/]))""" % (q, q, q), html) is not None


def page_file(dist, path):
    p = re.split(r"[#?]", path, maxsplit=1)[0]
    rel = p.strip("/")
    if p.endswith(".html"):
        return os.path.join(dist, rel)
    return os.path.join(dist, rel, "index.html") if rel else os.path.join(dist, "index.html")


def deep_problems(r, i, dist, deep_min_kb, F, cache):
    """The deep-link faults of one found row's ev entries (see the docstring)."""
    out = []
    for e in r.get("ev") if isinstance(r.get("ev"), list) else []:
        if not (isinstance(e, list) and e and isinstance(e[0], str) and e[0].startswith("/") and not e[0].startswith("//")):
            continue
        path = e[0]
        if not page_exists(dist, path):
            continue
        base, _, anchor = path.partition("#")
        phrase = e[2] if len(e) > 2 else None
        pf = page_file(dist, path)
        if pf not in cache:
            with open(pf, encoding="utf-8", errors="replace") as fh:
                h = fh.read()
            cache[pf] = (h, len(h.encode("utf-8")) / 1024.0, None)
        h, kb, lines = cache[pf]
        tag = "%s: ev %s" % (label(i, r, F), base)
        if anchor and not anchor_exists(h, anchor):
            out.append("%s has the anchor #%s, which is not an id in the built page" % (tag, anchor))
        if phrase is not None:
            if not isinstance(phrase, str) or not (3 <= len(" ".join(phrase.split())) <= 120):
                out.append("%s: the phrase (third item) must be text of 3 to 120 characters" % tag)
            elif re.search(r"[*_`]|\[[^\]]*\]\([^)]*\)", phrase):
                out.append("%s: the phrase has * _ ` or a markdown link; write it as the reader sees it" % tag)
            else:
                if lines is None:
                    lines = visible_lines(h)
                    cache[pf] = (h, kb, lines)
                n = sum(l.count(norm(phrase)) for l in lines)
                if n == 0:
                    out.append("%s: the phrase «%s» is not in the page's visible text" % (tag, " ".join(phrase.split())[:60]))
                elif n > 1:
                    out.append("%s: the phrase «%s» occurs %d times; the link would land on the first. Lengthen it until it occurs once" % (tag, " ".join(phrase.split())[:60], n))
        if not anchor and phrase is None and kb > deep_min_kb:
            out.append("%s is %d KB: link to the changed passage, not the top. Add an anchor (\"%s#id\") or a phrase from the page as a third item" % (tag, round(kb), base))
    return out


def label(i, r, F=FIELDS):
    k = r.get("key")
    s = " ".join(str(first(r, ["src", "source"]) or first(r, ["what", "scope"])).split())
    return "row %d%s, %s%s" % (i + 1, " [" + k + "]" if isinstance(k, str) and k else "", first(r, F["when"]), " — " + s[:70] if s else "")


def audit(searched, dist, frm, omap=None, corrections=None, fields=None, people_from=None, deep_from=None, deep_min_kb=100):
    """Return (problems, warnings, counts). problems: found rows from `frm` with no built page and no logOnly."""
    F = dict(FIELDS)
    F.update(fields or {})
    problems, warns = [], []
    n_found = n_checked = 0
    cache = {}
    for i, r in enumerate(rows_of(searched)):
        w = parse_when(first(r, F["when"]))
        if not w or w[0] < frm:
            continue
        if outcome_of(first(r, F["outcome"]), omap) != "found":
            continue
        n_found += 1
        if people_from and w[0] >= people_from:
            fl = r.get("for")
            ents = [e for e in fl if isinstance(e, list) and len(e) >= 2 and isinstance(e[0], str) and e[0].startswith("/") and not e[0].startswith("//")] if isinstance(fl, list) else []
            if r.get("nobody") is True and (fl not in (None, [])):
                problems.append("%s: has both `for` and `nobody`" % label(i, r, F))
            elif not ents and r.get("nobody") is not True:
                problems.append("%s: a found row that does not say who it is for (`for` [[\"/person/\", \"Name\"]] or \"nobody\": true)" % label(i, r, F))
            else:
                names = [e[1] for e in ents]
                if len(set(e[0] for e in ents)) != len(ents):
                    problems.append("%s: `for` lists a page twice" % label(i, r, F))
                if any(not isinstance(n, str) or not n.strip() for n in names):
                    problems.append("%s: a `for` entry has no name" % label(i, r, F))
                if dist is not None:
                    gone = [e[0] for e in ents if not page_exists(dist, e[0])]
                    if gone:
                        problems.append("%s: `for` names a page that is not built (%s)" % (label(i, r, F), ", ".join(gone)))
        if r.get("logOnly") is True:
            continue
        paths = ev_paths(r)
        if not paths:
            problems.append("%s: a found row with no `ev` page and no logOnly" % label(i, r, F))
        elif dist is not None and not any(page_exists(dist, p) for p in paths):
            problems.append("%s: none of its ev pages is a built page (%s)" % (label(i, r, F), ", ".join(paths)))
        if deep_from and dist is not None and w[0] >= deep_from:
            problems.extend(deep_problems(r, i, dist, deep_min_kb, F, cache))
        n_checked += 1
    n_cor = 0
    for i, r in enumerate(rows_of(corrections)):
        w = parse_when(first(r, F["cwhen"]))
        where = r.get("where")
        if not w or w[0] < frm or not isinstance(where, str):
            continue
        n_cor += 1
        for p in re.findall(r"(?:^|[\s(\[«\"'])(/[A-Za-z0-9][A-Za-z0-9._~/\-]*)", where):
            if dist is not None and not page_exists(dist, p):
                warns.append("correction %d (%s): `where` names %s, which is not a built page" % (i + 1, first(r, F["cwhen"]), p))
    return problems, warns, {"found": n_found, "checked": n_checked, "corrections": n_cor}


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pick(cands):
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None


def load_config(path):
    """Return (from_iso, omap, fields, people_from, deep_from, deep_min_kb) or raise ValueError. The date must be YYYY-MM-DD: a gate with a misspelt date is not silently off."""
    c = read_json(path)
    if not isinstance(c, dict) or not isinstance(c.get("from"), str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", c["from"]):
        raise ValueError('%s must be {"from": "YYYY-MM-DD"}' % path)
    try:
        datetime.date.fromisoformat(c["from"])
    except ValueError:
        raise ValueError("%s: %s is not a date" % (path, c["from"]))
    om = c.get("outcomeMap") or {}
    if not isinstance(om, dict):
        raise ValueError("%s: outcomeMap must be an object" % path)
    fl = c.get("fields", {})
    if fl is None:
        fl = {}
    if not isinstance(fl, dict) or any(not isinstance(v, list) or not v or any(not isinstance(x, str) or not x for x in v) for v in fl.values()):
        raise ValueError("%s: fields must be an object of non-empty lists of column names, e.g. {\"when\": [\"searchedOn\"]}" % path)
    pf = c.get("peopleFrom")
    if pf is not None:
        if not isinstance(pf, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", pf):
            raise ValueError("%s: peopleFrom must be YYYY-MM-DD" % path)
        try:
            datetime.date.fromisoformat(pf)
        except ValueError:
            raise ValueError("%s: peopleFrom %s is not a date" % (path, pf))
    df = c.get("deepFrom")
    if df is not None:
        if not isinstance(df, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", df):
            raise ValueError("%s: deepFrom must be YYYY-MM-DD" % path)
        try:
            datetime.date.fromisoformat(df)
        except ValueError:
            raise ValueError("%s: deepFrom %s is not a date" % (path, df))
        if df < c["from"]:
            raise ValueError("%s: deepFrom %s is before from %s" % (path, df, c["from"]))
    dk = c.get("deepMinKb", 100)
    if isinstance(dk, bool) or not isinstance(dk, (int, float)) or dk < 0:
        raise ValueError("%s: deepMinKb must be a number of KB, 0 or more" % path)
    return c["from"], {str(k).lower(): v for k, v in om.items()}, {k: v for k, v in fl.items() if k in FIELDS}, pf, df, dk


def main(argv=None):
    ap = argparse.ArgumentParser(description="A found row of searched.json must name a built page of the archive it went into, or say logOnly.")
    ap.add_argument("searched_pos", nargs="?", help="searched.json (same as --searched)")
    ap.add_argument("--searched")
    ap.add_argument("--config")
    ap.add_argument("--corrections")
    ap.add_argument("--dist")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        import check_row_pages_selftest
        return check_row_pages_selftest.main()

    cfg = pick([a.config, "docs/row-pages.json", "../docs/row-pages.json"])
    if not cfg:
        print("check_row_pages: OFF (no docs/row-pages.json; the archive turns the gate on with {\"from\": \"YYYY-MM-DD\"})")
        return 0
    try:
        frm, omap, fields, people_from, deep_from, deep_min_kb = load_config(cfg)
    except (OSError, ValueError) as e:
        print("check_row_pages: FAIL  %s" % e)
        return 1
    sp = a.searched or a.searched_pos or pick(["src/data/searched.json", "site/src/data/searched.json"])
    if not sp or not os.path.exists(sp):
        print("check_row_pages: FAIL  searched.json not found (%s)" % (sp or "tried src/data/ and site/src/data/"))
        return 1
    try:
        searched = read_json(sp)
    except (OSError, ValueError) as e:
        print("check_row_pages: FAIL  %s is not readable JSON: %s" % (sp, e))
        return 1
    cp = a.corrections or pick(["src/data/corrections.json", "site/src/data/corrections.json"])
    corrections = None
    if cp and os.path.exists(cp):
        try:
            corrections = read_json(cp)
        except (OSError, ValueError):
            print("check_row_pages: note  %s is not readable JSON; corrections not checked" % cp)
    dist = a.dist
    if dist is not None and not os.path.isdir(dist):
        print("check_row_pages: FAIL  --dist %s is not a directory (build first)" % dist)
        return 1
    problems, warns, n = audit(searched, dist, frm, omap, corrections, fields, people_from, deep_from, deep_min_kb)
    for w in warns:
        print("  warn  " + w)
    for p in problems:
        print("  FAIL  " + p)
    note = "" if dist is not None else "; pages NOT verified (no --dist)"
    if problems:
        print("check_row_pages: FAIL  %d problem(s) in %d found rows from %s. Each found row names ev: [[\"/page/#anchor\", \"label\", \"phrase on the page\"]] for each page the finding went into (a long page needs the anchor or the phrase), or \"logOnly\": true." % (len(problems), n["found"], frm))
        return 1
    print("check_row_pages: ok  %d found rows from %s, all with a built page or logOnly%s%s; %d advisory warnings" % (n["found"], frm, note, ("; deep links checked from %s" % deep_from) if deep_from and dist is not None else "", len(warns)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
