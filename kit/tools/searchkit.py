#!/usr/bin/env python3
"""The half of the search index that is the same in every archive.

The search BOX became one component in Phase 3. The index behind it did not:
six archives each kept their own builder, 74 to 182 lines, and every one of
them re-implemented the same two things — folding a string so that accents do
not hide a name, and emitting the row contract the shared box reads.

Six implementations of one function is six different answers, and they were:

  Defranceschi  đ Đ ø ł æ            — the most complete, by accident
  Falco         đ Đ                  + lowercase
  Booyzen       đ Đ                  + lowercase
  D'Arcy        ’ æ
  Blazevic      đ Đ ž ć č š          — the last four already handled by NFD
  Mazza         đ Đ                  + lowercase

Each one handles the letters that archive's author happened to meet. Anything
that arrived later is invisible, and two of those were live when this was
written: «Franciscæ Papić» could not be found by typing franciscae on
Blazevic, and «født stuart» could not be found by typing fodt on D'Arcy,
because neither fold knew æ or ø. Defranceschi could find both, for no better
reason than that somebody there had hit the problem first.

What stays per archive is what should: only an archive knows its own data
shapes, which rows are worth indexing, and what its surnames are called. This
module is the mechanism, not the content.
"""
import json
import os
import re
import unicodedata

# Letters that do NOT decompose under NFD, so stripping combining marks never
# reaches them. This is the union of every case the seven archives have
# actually met, plus the rest of the Latin set that behaves the same way —
# because the lesson of the fork is that the next one arrives unannounced.
_LETTERS = {
    "đ": "d", "Đ": "D", "ð": "d", "Ð": "D",
    "ø": "o", "Ø": "O", "œ": "oe", "Œ": "OE",
    "æ": "ae", "Æ": "AE", "ß": "ss",
    "ł": "l", "Ł": "L", "ħ": "h", "Ħ": "H",
    "ı": "i", "İ": "I", "ŧ": "t", "Ŧ": "T",
    "þ": "th", "Þ": "TH", "ĸ": "k", "ŉ": "n",
}
# Punctuation that a reader will not type: curly quotes, dashes of every width.
_PUNCT = {
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-", "­": "",
    " ": " ", "​": "",
}


def fold(s):
    """Lowercase, strip accents, and spell out the letters NFD cannot reach.

    A reader typing Gracisce finds Gračišće, Zubrinic finds Žubrinić, and
    franciscae finds Franciscæ — on every archive, rather than on whichever
    one happened to have met that letter before.
    """
    s = str(s or "")
    for a, b in _PUNCT.items():
        s = s.replace(a, b)
    for a, b in _LETTERS.items():
        s = s.replace(a, b)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def haystack(*parts):
    """The searchable blob for one row: folded, plus a punctuation-free copy.

    Both forms are kept because a reader types a name either way — «D'Arcy»
    and «darcy» must both find it, and a substring match cannot do that from
    one spelling alone.
    """
    text = " ".join(str(p) for p in parts if p)
    a = fold(text)
    b = re.sub(r"[^a-z0-9]+", "", a)
    squashed = re.sub(r"\s+", " ", a).strip()
    return f"{squashed} {b}".strip()


def row(kind, title, sub="", href="", extra=""):
    """One row of the contract all seven archives emit: {k,t,s,h,q}."""
    return {
        "k": kind,
        "t": re.sub(r"\s+", " ", str(title or "")).strip(),
        "s": re.sub(r"\s+", " ", str(sub or "")).strip(),
        "h": str(href or ""),
        "q": haystack(title, sub, extra),
    }


def dedupe(rows):
    """Same kind, same href, same title is the same row. Keeps the first."""
    seen, out = set(), []
    for r in rows:
        key = (r.get("k"), r.get("h"), r.get("t"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def write(rows, *paths, quiet=False):
    """Write the index everywhere it is needed, and say what was written.

    The box fetches /searchindex.json over HTTP, so the file has to reach
    public/. Three archives once shipped a working component, a valid schema
    and a broken search because the index sat in src/data and nothing served
    it. Passing both paths is cheaper than remembering that.
    """
    rows = dedupe(rows)
    for p in paths:
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
    if not quiet:
        kinds = {}
        for r in rows:
            kinds[r["k"]] = kinds.get(r["k"], 0) + 1
        top = ", ".join(f"{k} {n}" for k, n in
                        sorted(kinds.items(), key=lambda x: -x[1])[:6])
        print(f"searchindex: {len(rows)} rows — {top}")
        for p in paths:
            print(f"  → {p}")
    return rows


# ---- reading the built site -------------------------------------------------

_NOINDEX = re.compile(r'name=["\']robots["\'][^>]*noindex', re.I)
_TAG = re.compile(r"<[^>]+>")


def _text(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S | re.I)
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(_TAG.sub(" ", s))).strip()


def pages(dist, base="", skip=(), include_prose=True):
    """Every built page as a row, read from the HTML rather than the routes.

    Reading the rendered page is what lets the index honour the archive's own
    privacy rule without being told it twice: a page that noindexes itself is
    skipped here by reading the same tag a search engine would read. A
    route-built index cannot do that, and several of these archives publish
    noindexed pages for living relatives.
    """
    out = []
    base = "/" + base.strip("/") if base.strip("/") else ""
    for root, _, files in os.walk(dist):
        for f in files:
            if f != "index.html":
                continue
            p = os.path.join(root, f)
            raw = open(p, encoding="utf-8", errors="replace").read()
            if _NOINDEX.search(raw) or "Redirecting to" in raw:
                continue
            rel = os.path.relpath(root, dist).replace(os.sep, "/")
            rel = "" if rel == "." else rel
            if any(rel == s or rel.startswith(s.rstrip("/") + "/") for s in skip):
                continue
            href = f"{base}/{rel}/".replace("//", "/") if rel else f"{base}/"
            m = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S)
            title = _text(m.group(1)) if m else _text(
                (re.search(r"<title[^>]*>(.*?)</title>", raw, re.S) or [None, ""])[1])
            dek = re.search(r'class="[^"]*\bdek\b[^"]*"[^>]*>(.*?)</', raw, re.S)
            sub = _text(dek.group(1))[:160] if dek else ""
            prose = ""
            if include_prose:
                body = re.search(r"<main[^>]*>(.*?)</main>", raw, re.S)
                prose = _text(body.group(1))[:2000] if body else ""
            if title:
                out.append(row("Page", title, sub, href, prose))
    return out
