#!/usr/bin/env python3
"""Link the names on the built pages to their people, once, after the build.

    python3 autolink.py --dist dist --index names.json [--living living.json] [--scope main]
                        [--allow-prefix /people/ --allow-prefix /who/] [--min-words 2] [--check]

WHY (David, 18 October 2026: "why so many names on our narrative pages have no link to their person page?").
Audits of the same day: on the twelve longest pages Mazza links 11% of the names that resolve to one dead person,
Lerena 1.8%, Luwinski 3%; Falco, Blazevic and the rest link in the browser with scripts that run only where an author
typed a helper. One tool, run after the build by every archive, with a gate behind it (checklinks.py).

THE INDEX is supplied by each archive, generated from its own people data (see kit/docs/autolink.md):

    {"people":    [{"name": "Given Family", "aliases": ["Family Given"], "url": "/people/given-family/"}],
     "ambiguous": [{"name": "Given Family", "url": "/people/?q=Given%20Family"}]}

  people     names that resolve to exactly ONE deceased person who has a page
  ambiguous  names borne by several people, sent to the archive's search or disambiguation address
The tool links ONLY what the index lists. A bare first name, an alias nobody listed, a name in a table the archive
marked data-no-autolink: not linked, by design.

WHAT IT DOES. It rewrites the built HTML IN PLACE, adding <a href="..." data-autolink>name</a> around a name in running
text and changing nothing else: not one other byte moves (a tolerant tokenizer finds the text, no page is re-serialised).
  - only inside the scope element (default <main>);
  - never inside <a>, <h1>..<h6>, <nav>, <script>, <style>, <code>, <pre>, <title>, <svg>, form controls, or an element
    that has (or sits under one that has) data-no-autolink;
  - the FIRST mention of a person in each section (the text between <h2>/<h3> boundaries and <section> elements; a page
    with none is one section); a person already linked in that section by any link to the same address is not linked again;
  - longest name first, then the alias; whole words only (Arena is not found in Arenaria, nor in Arena-Rossi, nor in d'Arena);
  - a word written in capitals matches ("Given FAMILY"), the text stays as written;
  - idempotent: a second run changes nothing. --check changes nothing and exits 1 if a run would.

THE LIVING RULE (the project's hardest). --living is a JSON list of the names, aliases and addresses of living or held-out
people, supplied by the archive from its own living gate. It is used three ways:
  1. an index entry (name, alias or address) that the living list also holds is a faulty index: the run STOPS, exit 2,
     and says only HOW MANY entries, never which;
  2. a living name is searched for in the text too: if it overlaps a name the index lists ("Maria Rossi Bianchi" is
     living, "Maria Rossi" is dead), the dead name is NOT linked there;
  3. an address outside the public prefixes (--allow-prefix, repeatable; default /people/ and /who/) is refused, exit 2.

EXIT CODES: 0 done / nothing to do; 1 --check found work to do; 2 refused (empty index, empty build, living conflict,
address outside the prefixes, unreadable input). Prints counts only, never a person's name.
"""
import os
import re
import sys
import json
import html as _html
import argparse
import unicodedata
from urllib.parse import unquote, unquote_plus

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import outdir as _outdir  # noqa: E402  ARCHIVE_OUT beats --dist (kit/tools/outdir.py)

DEFAULT_PREFIXES = ["/people/", "/who/"]
SKIP_TAGS = {"a", "h1", "h2", "h3", "h4", "h5", "h6", "nav", "script", "style", "code", "pre", "title", "svg", "math",
             "button", "select", "option", "optgroup", "datalist", "textarea", "input", "template", "iframe", "object", "canvas"}
RAW_TEXT = {"script", "style", "textarea", "title"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SECTION_TAGS = {"h2", "h3", "section"}

TOKEN = re.compile(r'<!--.*?-->|<!\[CDATA\[.*?\]\]>|<![^>]*>|<\?.*?\?>|</[A-Za-z][^>]*>|<[A-Za-z](?:"[^"]*"|\'[^\']*\'|[^>"\'])*>', re.S)
TAGNAME = re.compile(r"</?([A-Za-z][^\s/>]*)")
ATTR = re.compile(r'([^\s"\'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'=<>`]+)))?')
ENT = re.compile(r"&(#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
WORD = re.compile(r"[^\W_]+(?:['\-][^\W_]+)*")
APOS = {"’": "'", "‘": "'", "ʼ": "'", "´": "'"}
DASH = {"‐": "-", "‑": "-"}


class Refusal(Exception):
    """The run must stop with exit 2. The message carries counts only, never a name."""


# ----------------------------------------------------------------------------------------------------- text folding
def norm_name(s):
    """A name as the matcher holds it: NFC, one space between words, straight apostrophes and hyphens."""
    s = unicodedata.normalize("NFC", s or "")
    s = "".join(APOS.get(c, DASH.get(c, c)) for c in s)
    return " ".join(s.split())


def name_key(s):
    return norm_name(s).casefold()


def norm_url(u):
    """Compare addresses by path (with a trailing slash) and decoded query; the fragment never counts."""
    u = _html.unescape(str(u or "")).strip().split("#")[0]
    path, _, query = u.partition("?")
    path = unquote(path)
    if path and not path.endswith("/") and not re.search(r"\.[A-Za-z0-9]+$", path):
        path += "/"
    return path + ("?" + unquote_plus(query) if query else "")


def fold(raw):
    """The text of one text node as the matcher reads it, with where each character came from in the raw HTML.
    Entities are decoded, whitespace runs become one space, typographic apostrophes and hyphens are straightened,
    combining marks are composed. Returns (string, starts, ends): offsets into `raw`."""
    chars, S, E = [], [], []
    i, n = 0, len(raw)
    while i < n:
        c = raw[i]
        j = i + 1
        piece = c
        if c == "&":
            m = ENT.match(raw, i)
            if m:
                dec = _html.unescape(m.group(0))
                if dec != m.group(0):
                    piece, j = dec, m.end()
        for ch in piece:
            if ch.isspace():
                if chars and chars[-1] == " ":
                    E[-1] = j
                else:
                    chars.append(" "); S.append(i); E.append(j)
                continue
            ch = APOS.get(ch, DASH.get(ch, ch))
            if unicodedata.category(ch).startswith("M") and chars and chars[-1] != " ":
                comp = unicodedata.normalize("NFC", chars[-1] + ch)
                if len(comp) == 1:
                    chars[-1] = comp; E[-1] = j
                    continue
            chars.append(ch); S.append(i); E.append(j)
        i = j
    return "".join(chars), S, E


def _is_mark(ch):
    return unicodedata.category(ch).startswith("M")


def boundary_before(F, i):
    if i <= 0:
        return True
    p = F[i - 1]
    if p.isalnum() or p == "_" or _is_mark(p):
        return False
    if p in "-'" and i >= 2 and F[i - 2].isalnum():
        return False
    return True


def boundary_after(F, j):
    n = len(F)
    if j >= n:
        return True
    c = F[j]
    if c.isalnum() or c == "_" or _is_mark(c):
        return False
    if c == "-" and j + 1 < n and F[j + 1].isalnum():
        return False
    if c == "'" and j + 1 < n and F[j + 1].isalnum():
        # a possessive ("Arena's") still names the person; "Arena'x" or "Arena'ski" is another word
        return F[j + 1] in "sS" and (j + 2 >= n or not F[j + 2].isalnum())
    return True


def _caps_equal(seg, word):
    """The source writes the word in capitals (a register transcription): SANIGER matches Saniger."""
    return (seg == seg.upper() and sum(1 for ch in seg if ch.isalpha()) >= 2 and seg.upper() == word.upper())


# ----------------------------------------------------------------------------------------------------- the index
class Entry:
    __slots__ = ("kind", "words", "text", "url", "alias", "key")

    def __init__(self, kind, name, url, alias):
        self.kind = kind                      # "person" | "ambiguous" | "living"
        self.text = norm_name(name)
        self.words = tuple(self.text.split(" "))
        self.url = url or ""                  # already normalized by the caller
        self.alias = alias
        self.key = self.text.casefold()


class Index:
    def __init__(self):
        self.entries = []         # every Entry the matcher searches for (living ones included)
        self.by_first = {}        # first-word key -> [Entry] longest first
        self.urls = set()         # addresses the index may link to
        self.raw_url = {}         # normalized address -> address as the archive wrote it
        self.names_by_url = {}    # normalized address -> {name key}
        self.living_urls = set()
        self.living_names = set()
        self.stats = {"people": 0, "ambiguous": 0, "aliases": 0, "conflicts_skipped": 0, "short_skipped": 0, "living_terms": 0}

    def _add(self, e):
        self.entries.append(e)
        m = WORD.match(e.text)
        if m:
            self.by_first.setdefault(m.group(0).casefold(), []).append(e)


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def load_living(path):
    """The living list: strings starting with "/" are addresses, anything else a name or alias. A list, or an object
    whose values are lists (the shape is the archive's; only the strings matter)."""
    if not path:
        return set(), set()
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Refusal("the living list %s cannot be read (%s): a run without it is not safe" % (path, type(e).__name__))
    names, urls = set(), set()
    for s in _strings(data):
        s = s.strip()
        if not s:
            continue
        (urls if s.startswith("/") else names).add(norm_url(s) if s.startswith("/") else name_key(s))
    return names, urls


def load_index(path, living_names=frozenset(), living_urls=frozenset(), prefixes=None, min_words=2):
    """Read the archive's index. Raises Refusal for anything that makes a run unsafe or meaningless."""
    prefixes = prefixes or DEFAULT_PREFIXES
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Refusal("the index %s cannot be read (%s)" % (path, type(e).__name__))
    if not isinstance(data, dict):
        raise Refusal("the index must be an object with \"people\" and \"ambiguous\" lists")
    idx = Index()
    idx.living_names, idx.living_urls = set(living_names), set(living_urls)
    pending = []          # (kind, name, alias?, url)
    bad_shape = bad_prefix = 0
    for kind, field in (("person", "people"), ("ambiguous", "ambiguous")):
        rows = data.get(field) or []
        if not isinstance(rows, list):
            raise Refusal("index.%s must be a list" % field)
        for r in rows:
            if not isinstance(r, dict) or not isinstance(r.get("name"), str) or not r["name"].strip() \
                    or not isinstance(r.get("url"), str) or not r["url"].startswith("/"):
                bad_shape += 1
                continue
            nu = norm_url(r["url"])
            if not any(nu.startswith(p) for p in prefixes):
                bad_prefix += 1
                continue
            idx.stats["people" if kind == "person" else "ambiguous"] += 1
            idx.raw_url.setdefault(nu, r["url"])
            pending.append((kind, r["name"], False, nu))
            for al in (r.get("aliases") or []):
                if isinstance(al, str) and al.strip():
                    idx.stats["aliases"] += 1
                    pending.append((kind, al, True, nu))
    if bad_shape:
        raise Refusal("%d index entr%s malformed (each needs a name and a root-relative url)" % (bad_shape, "y is" if bad_shape == 1 else "ies are"))
    if bad_prefix:
        raise Refusal("%d index entr%s an address outside the public prefixes %s" % (bad_prefix, "y has" if bad_prefix == 1 else "ies have", ", ".join(prefixes)))
    if not pending:
        raise Refusal("the index is empty: a run that examined nothing has not passed")
    # LIVING: an index entry the living list also holds is a faulty index. Count, never name.
    hits = sum(1 for (_, name, _, nu) in pending if name_key(name) in idx.living_names or nu in idx.living_urls)
    if hits:
        raise Refusal("LIVING: %d index entr%s the living list also holds. The index is faulty; nothing was linked. "
                      "Fix the archive's index generator." % (hits, "y is one that" if hits == 1 else "ies are ones that"))
    # one name must lead to one address; a name that leads to two (or is both unique and ambiguous) is skipped
    owners = {}
    for (kind, name, alias, nu) in pending:
        owners.setdefault(name_key(name), set()).add(nu)
    clash = {k for k, v in owners.items() if len(v) > 1}
    seen = set()
    for (kind, name, alias, nu) in pending:
        k = name_key(name)
        if len(k.split(" ")) < min_words:
            idx.stats["short_skipped"] += 1
            continue
        if k in clash:
            idx.stats["conflicts_skipped"] += 1
            continue
        if (k, nu) in seen:
            continue
        seen.add((k, nu))
        idx._add(Entry(kind, name, nu, alias))
        idx.urls.add(nu)
        idx.names_by_url.setdefault(nu, set()).add(k)
    for u in {nu for (_, _, _, nu) in pending}:     # an address the index holds stays "known" even if all its names were skipped
        idx.urls.add(u)
    for k in sorted(idx.living_names):
        if k:
            idx._add(Entry("living", k, "", False))
            idx.stats["living_terms"] += 1
    for lst in idx.by_first.values():
        lst.sort(key=lambda e: (-len(e.text), e.alias))
    if not any(e.kind != "living" for e in idx.entries):
        raise Refusal("every index entry was skipped (too short or in conflict): nothing to link")
    return idx


# ----------------------------------------------------------------------------------------------------- matching
def find_matches(raw, idx):
    """All matches in one text node: [(raw_start, raw_end, Entry)], after longest-first / living-first resolution.
    Returns (accepted, living_blocked_count)."""
    if not idx.by_first or not raw.strip():
        return [], 0
    F, S, E = fold(raw)
    n = len(F)
    found = []
    i = 0
    while i < n:
        if F[i].isalnum() and boundary_before(F, i):
            m = WORD.match(F, i)
            cands = idx.by_first.get(m.group(0).casefold()) if m else None
            if cands:
                for e in cands:
                    j = i
                    ok = True
                    last = len(e.words) - 1
                    for k, w in enumerate(e.words):
                        seg = F[j:j + len(w)]
                        if len(seg) != len(w) or not (seg == w or _caps_equal(seg, w)
                                                      or (e.kind == "living" and seg.casefold() == w.casefold())):
                            ok = False
                            break
                        j += len(w)
                        if k < last:
                            if j >= n or F[j] != " ":
                                ok = False
                                break
                            j += 1
                    if ok and boundary_after(F, j):
                        found.append((i, j, e))
            i = m.end() if m else i + 1
        else:
            i += 1
    if not found:
        return [], 0
    living = [(a, b) for (a, b, e) in found if e.kind == "living"]
    dead = [t for t in found if t[2].kind != "living"]
    blocked = 0
    keep = []
    for (a, b, e) in dead:
        if any(a < lb and la < b for (la, lb) in living):
            blocked += 1
        else:
            keep.append((a, b, e))
    keep.sort(key=lambda t: (-(t[1] - t[0]), t[2].alias, t[0]))
    taken, out = [], []
    for (a, b, e) in keep:
        if any(a < tb and ta < b for (ta, tb) in taken):
            continue
        taken.append((a, b))
        out.append((S[a], E[b - 1], e))
    out.sort(key=lambda t: t[0])
    return out, blocked


# ----------------------------------------------------------------------------------------------------- one page
class Scan:
    def __init__(self):
        self.scope_seen = False
        self.inserts = []          # [(raw_start, raw_end, url_raw, kind)]
        self.covered = 0           # mentions left alone because the section already links that person
        self.living_blocked = 0
        self.autolinks = []        # existing data-autolink links in scope: {"href": normalized, "text": folded text}
        self.mentions = 0          # resolvable mentions in eligible text
        self.sections = 0


def _attrs(tag_src):
    body = tag_src[1:]
    m = TAGNAME.match(tag_src)
    body = tag_src[m.end():] if m else body
    out = {}
    for am in ATTR.finditer(body):
        v = am.group(2) if am.group(2) is not None else am.group(3) if am.group(3) is not None else am.group(4)
        out[am.group(1).lower()] = _html.unescape(v) if v is not None else ""
    return out


def scan_html(html, idx, scope="main"):
    """Find what an autolink run would add to one page. Pure: the page is not changed."""
    sc = Scan()
    scope = scope.lower()
    stack = []                 # [name, is_skip, is_scope]
    n_scope = n_skip = 0
    section = 0
    texts = []                 # (raw_start, raw_end, section) of text in eligible places
    linked = set()             # (section, normalized href) of every <a href> in scope
    cur_auto = None
    pos, L = 0, len(html)

    def pop_to(k):
        nonlocal n_scope, n_skip
        while len(stack) > k:
            nm, sk, sp = stack.pop()
            n_skip -= 1 if sk else 0
            n_scope -= 1 if sp else 0

    while pos < L:
        m = TOKEN.search(html, pos)
        end_text = m.start() if m else L
        if end_text > pos:
            if n_scope:
                if n_skip == 0:
                    texts.append((pos, end_text, section))
                if cur_auto is not None:
                    cur_auto["raw"].append(html[pos:end_text])
        if not m:
            break
        tok = m.group(0)
        pos = m.end()
        if tok.startswith("<!") or tok.startswith("<?"):
            continue
        nm = TAGNAME.match(tok).group(1).lower()
        if tok.startswith("</"):
            k = next((x for x in range(len(stack) - 1, -1, -1) if stack[x][0] == nm), -1)
            if k >= 0:
                if nm == "section" and n_scope:
                    section += 1
                pop_to(k)
            if nm == "a" and cur_auto is not None:
                cur_auto["text"] = fold("".join(cur_auto.pop("raw")))[0]
                sc.autolinks.append(cur_auto)
                cur_auto = None
            continue
        attrs = _attrs(tok)
        selfclose = tok.endswith("/>")
        if nm == "a":                                   # <a> does not nest: a new one closes the old
            k = next((x for x in range(len(stack) - 1, -1, -1) if stack[x][0] == "a"), -1)
            if k >= 0:
                pop_to(k)
                cur_auto = None
        if n_scope and nm in SECTION_TAGS:
            section += 1
        if nm == scope and not selfclose:
            if n_scope == 0:
                section += 1
            sc.scope_seen = True
        if n_scope and nm == "a" and "href" in attrs:
            linked.add((section, norm_url(attrs["href"])))
            if "data-autolink" in attrs:
                cur_auto = {"href": norm_url(attrs["href"]), "raw": [], "text": ""}
        if nm in RAW_TEXT and not selfclose:
            c = re.compile(r"</%s\s*>" % nm, re.I).search(html, pos)
            pos = c.end() if c else L
            continue
        if nm in VOID or selfclose:
            continue
        is_skip = nm in SKIP_TAGS or "data-no-autolink" in attrs
        stack.append([nm, is_skip, nm == scope])
        n_skip += 1 if is_skip else 0
        n_scope += 1 if nm == scope else 0
    sc.sections = section
    # second pass: the first plain mention of each person in each section
    for (a, b, sec) in texts:
        ms, blocked = find_matches(html[a:b], idx)
        sc.living_blocked += blocked
        for (ms_, me_, e) in ms:
            sc.mentions += 1
            key = (sec, e.url)
            if key in linked:
                sc.covered += 1
                continue
            linked.add(key)
            sc.inserts.append((a + ms_, a + me_, idx.raw_url.get(e.url, e.url), e.kind))
    sc.inserts.sort()
    return sc


def apply_inserts(html, inserts):
    out, last = [], 0
    for (a, b, url, _kind) in inserts:
        out.append(html[last:a])
        out.append('<a href="%s" data-autolink>' % url.replace("&", "&amp;").replace('"', "&quot;"))
        out.append(html[a:b])
        out.append("</a>")
        last = b
    out.append(html[last:])
    return "".join(out)


def autolink_html(html, idx, scope="main"):
    sc = scan_html(html, idx, scope)
    return apply_inserts(html, sc.inserts), sc


# ----------------------------------------------------------------------------------------------------- the build
def html_pages(dist):
    out = []
    for d, ds, fs in os.walk(dist):
        ds[:] = sorted(x for x in ds if x not in ("node_modules", "_astro", ".git"))
        for f in sorted(fs):
            if f.lower().endswith(".html"):
                out.append(os.path.join(d, f))
    return out


def page_url(dist, path):
    rel = os.path.relpath(path, dist).replace(os.sep, "/")
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def read_page(path):
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as fh:
        return fh.read()


def write_page(path, text):
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write(text)


def prepare(a):
    prefixes = a.allow_prefix or list(DEFAULT_PREFIXES)
    prefixes = [p if p.endswith("/") else p + "/" for p in prefixes]
    ln, lu = load_living(a.living)
    idx = load_index(a.index, ln, lu, prefixes, a.min_words)
    return idx, prefixes


def main(argv=None):
    ap = argparse.ArgumentParser(description="Link the names on the built pages to their people (see the docstring).")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--index", required=True)
    ap.add_argument("--living")
    ap.add_argument("--scope", default="main")
    ap.add_argument("--allow-prefix", action="append", default=[])
    ap.add_argument("--min-words", type=int, default=2)
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if a run would")
    a = ap.parse_args(argv)
    dist = _outdir.resolve(a.dist)
    try:
        idx, _ = prepare(a)
        pages = html_pages(dist) if os.path.isdir(dist) else []
        if not pages:
            raise Refusal("no built page under %s: nothing was examined" % dist)
    except Refusal as e:
        print("autolink: REFUSED. %s" % e)
        return 2
    n = _outdir.note(dist)
    if n:
        print(n)
    scanned = changed = people = ambig = covered = blocked = 0
    for p in pages:
        html = read_page(p)
        sc = scan_html(html, idx, a.scope)
        if not sc.scope_seen:
            continue
        scanned += 1
        covered += sc.covered
        blocked += sc.living_blocked
        if not sc.inserts:
            continue
        changed += 1
        people += sum(1 for t in sc.inserts if t[3] == "person")
        ambig += sum(1 for t in sc.inserts if t[3] == "ambiguous")
        if not a.check:
            write_page(p, apply_inserts(html, sc.inserts))
    if scanned == 0:
        print("autolink: REFUSED. none of the %d pages has a <%s>: wrong --scope, or nothing was built" % (len(pages), a.scope))
        return 2
    verb = "would add" if a.check else "added"
    st = idx.stats
    print("autolink: %d pages, %d with <%s>; %s %d links on %d pages (%d to one person, %d to a search address); "
          "%d mentions already covered by a link in their section; %d left alone beside a living name; "
          "index: %d people, %d ambiguous, %d aliases, %d skipped as short, %d skipped as ambiguous or in conflict, %d living terms"
          % (len(pages), scanned, a.scope, verb, people + ambig, changed, people, ambig, covered, blocked,
             st["people"], st["ambiguous"], st["aliases"], st["short_skipped"], st["conflicts_skipped"], st["living_terms"]))
    if a.check and changed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
