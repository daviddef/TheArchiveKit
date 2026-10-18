#!/usr/bin/env python3
"""The gate behind the linking standard (kit/docs/linking-standard.md): five counts per narrative page, and none may rise.

    python3 checkstandard.py --dist dist --index names-index.json --config standard.json
                             [--living living.json] [--floor .standardfloor.json] [--write-floor]
                             [--new-page-max 3] [--allow-prefix /people/ --allow-prefix /who/] [--table]

IT READS THE BUILT SITE, the archive's names index (the one autolink.py reads) and one small config the archive owns
(standard.json: see the standard's "adopting it"). It counts, for every page the config puts in scope:

  L1  a name the index resolves, written in running text, with no link to that person in its section
      (exactly checklinks.py's count: the same index, the same matching, the same sections; autolink.py brings it to 0)
  L2  a person-like phrase in bold, or in a record-reading block the config names, that matches NO index entry
      (neither a person page nor a /who/ entry nor an alias): a person the archive read from a record and cannot link to.
      Counted once per distinct phrase per page.
  L3  a passage (a <p>, <li>, <dd>, <blockquote>...) that quotes a record by one of the config's citation patterns and has
      no record link in it, in a block it sits in, or in the next block (a short apparatus line, or a figure)
  L4  a passage whose record scan the archive HOLDS (an image its config can key to the passage's citation) when no image
      with that key sits in the same section of the page
  L5  a form the machine cannot resolve and an author must write in full: a bare given name whose section has not yet
      written a full name containing it, and a capitalised name-like phrase in plain prose that matches no index entry.
      Counted once per distinct (section, form).
  EX  how many would-be violations the page's own exemptions hide (data-cite-exempt, data-name-exempt, config allow
      entries). It is ratcheted too, so an exemption cannot spread unseen.

THE HEURISTICS ARE IMPRECISE AND SAY SO. L2 and L5 guess what is a person from capitalisation and the archive's own given
names; L3 and L4 find a citation only where the config's patterns do. A false positive is cured in the archive's config
(a not_names pattern, a stop word, an allow entry with a reason), never by loosening this tool; a miss is cured by
adding the archive's pattern. Neither changes how the counts are held: they may only go down.

THE RATCHET (.standardfloor.json, committed, one number per rule per page, never a name, never an address of a person):
  rise          a page's count for any rule is above its floor                                         fail
  new page      a page not in the floor with more than --new-page-max (default 3) in any one rule       fail
  --write-floor writes the floor: every number becomes the lower of its old floor and its current count, and a page not
                yet in the floor enters at its current count. REFUSES to write while anything rose or a structural
                failure stands. A floor goes up only when a person edits the file, in a commit that says why.

STRUCTURAL FAILURES (always fail, never ratcheted): an index address that is not a built page (a link to nowhere, the
dead end L2 exists to prevent); a data-autolink link that is stale or points to a living person (checklinks.py's own);
a data-cite-exempt or data-name-exempt with no reason.

REFUSED (exit 2): an empty build, no in-scope page, an include pattern that matched no built page, a config that is
missing, unreadable, empty or invalid (no citation patterns, no record-link rule, no scans decision, an allow entry
without a reason, a bad regex), an index the living list also holds, a living phrase in the config, and a run in which no
passage cites a record at all (the patterns found nothing, so nothing was examined). "A check that examined nothing has
not passed."

Prints counts only, never a person's name or a quoted passage. EXIT CODES: 0 pass; 1 fail; 2 refused.
"""
import os
import re
import sys
import json
import fnmatch
import string
import argparse
import unicodedata
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import autolink as al  # noqa: E402
import checklinks as cl  # noqa: E402
import outdir as _outdir  # noqa: E402

RULES = ("L1", "L2", "L3", "L4", "L5")
KEYS = RULES + ("EX",)
FLOOR_VERSION = 1

DEFAULT_BLOCKS = ["p", "li", "dd", "blockquote"]
AUX_BLOCKS = {"figure"}                      # may be the "next block" that carries the link; never a passage
BOLD = {"strong", "b"}
VOID = al.VOID
DEFAULT_PARTICLES = ["de", "di", "del", "della", "dei", "degli", "da", "dal", "dalla", "la", "le", "lo", "li", "van", "von",
                     "der", "den", "ten", "ter", "du"]
DEFAULT_STOP = ["The", "A", "An", "In", "On", "At", "Of", "And", "Or", "But", "He", "She", "His", "Her", "It", "Its", "This",
                "That", "These", "Those", "When", "Then", "Here", "There", "After", "Before", "By", "For", "From", "With",
                "Not", "No", "If", "As", "So", "Both", "One", "Two", "Three", "Who", "Whose", "What", "Which", "Where", "While",
                "Because", "Since", "Until", "Also", "Only", "Still", "Even", "Each", "Every", "All", "Some", "Any", "Our",
                "Their", "They", "We", "You", "I", "Il", "La", "Lo", "Le", "Gli", "Un", "Una", "Di", "Da", "Del", "Della",
                "Dei", "Degli", "E", "Ed", "Il", "Fu", "Figlio", "Figlia", "Nato", "Nata", "Morto", "Morta", "Marito",
                "Moglie", "Vedova", "Vedovo", "Testimone", "Testimoni", "Sindaco", "Assessore", "Notary", "Notaio",
                "Is", "Was", "Are", "Were", "Be", "Been", "Has", "Have", "Had", "Do", "Does", "Did", "Will", "Would", "Could",
                "Should", "May", "Might", "Must", "Can", "Neither", "Nor", "Whether", "Either", "Yet", "Though", "Although",
                "Why", "How", "Now", "Today", "Perhaps", "Maybe", "Between", "Among", "Under", "Over", "Into", "Upon",
                "Within", "Without", "Across", "Against", "About", "Above", "Below", "During", "Except", "Per", "Another",
                "Other", "Such", "Many", "Most", "More", "Less", "Once", "Twice", "First", "Second", "Third", "Last", "Next",
                "Nothing", "Nobody", "Everyone", "Someone", "Anyone", "See", "Compare", "Note", "Why", "Yes"]
SEL = re.compile(r"^([A-Za-z0-9]*)((?:\.[\w-]+)*)((?:\[[\w:-]+(?:=[^\]]*)?\])*)$")
WORD_RE = re.compile(r"[^\W\d_]+(?:['\-][^\W\d_]+)*", re.U)
IMG_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", re.I | re.S)


# ----------------------------------------------------------------------------------------------------------- helpers
def loose(s):
    """A name as the gate compares it: accents, case, apostrophes and hyphens folded away, one space between words."""
    s = unicodedata.normalize("NFKD", al.norm_name(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("'", "").replace("-", " ")
    return " ".join(s.casefold().split())


def squash(s):
    return " ".join((s or "").split())


class Sel:
    """A tiny selector: tag, .class, [attr], [attr=value]; e.g. 'p.rec', '.rec', 'table', '[data-reads]', 'div.k[data-x=y]'."""
    def __init__(self, text):
        m = SEL.match(text.strip())
        if not m or not text.strip():
            raise al.Refusal("config: %r is not a selector this gate reads (tag, .class, [attr], [attr=value], combined)" % text)
        self.tag = m.group(1).lower()
        self.classes = [c for c in m.group(2).split(".") if c]
        self.attrs = []
        for a in re.findall(r"\[([\w:-]+)(?:=([^\]]*))?\]", m.group(3)):
            self.attrs.append((a[0].lower(), a[1].strip("\"'") if a[1] != "" else None))
        if not (self.tag or self.classes or self.attrs):
            raise al.Refusal("config: %r is not a selector this gate reads" % text)

    def match(self, tag, attrs):
        if self.tag and self.tag != tag:
            return False
        if self.classes:
            have = (attrs.get("class") or "").split()
            if any(c not in have for c in self.classes):
                return False
        for (k, v) in self.attrs:
            if k not in attrs or (v is not None and attrs[k] != v):
                return False
        return True


def _sels(lst, what):
    if not isinstance(lst, list) or not all(isinstance(x, str) for x in lst):
        raise al.Refusal("config: %s must be a list of selector strings" % what)
    return [Sel(x) for x in lst]


def _rx(s, flags, what):
    fl = 0
    for ch in (flags or ""):
        if ch == "i":
            fl |= re.I
        elif ch == "u":
            fl |= re.U
        else:
            raise al.Refusal("config: %s has an unknown regex flag %r (only 'i')" % (what, ch))
    try:
        return re.compile(s, fl)
    except (re.error, TypeError):
        raise al.Refusal("config: %s is not a valid regular expression" % what)


def key_of(template, gd, aliases):
    """The scan key a pattern's named groups give (case, accents and the config's aliases folded), or None when a group the
    template uses was not matched."""
    vals = {}
    for k, v in gd.items():
        if v is not None:
            v = loose(v)
            vals[k] = aliases.get(v, v)
    try:
        used = [f for (_t, f, _s, _c) in string.Formatter().parse(template) if f]
        if any(u not in vals for u in used):
            return None
        return template.format(**vals)
    except (KeyError, IndexError, ValueError):
        return None


# ----------------------------------------------------------------------------------------------------------- the config
class Config:
    pass


def load_config(path):
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise al.Refusal("the config %s cannot be read (%s): a run without it examined nothing" % (path, type(e).__name__))
    if not isinstance(raw, dict) or not raw:
        raise al.Refusal("the config is empty: it must name pages, citation patterns and a record-link rule")
    c = Config()
    c.scope = str(raw.get("scope") or "main").lower()
    inc, exc = raw.get("include"), raw.get("exclude") or []
    if not isinstance(inc, list) or not inc or not all(isinstance(x, str) and x.startswith("/") for x in inc):
        raise al.Refusal("config: 'include' must be a non-empty list of root-relative pages or patterns such as \"/scilla/\" or \"/*\"")
    if not isinstance(exc, list) or not all(isinstance(x, str) for x in exc):
        raise al.Refusal("config: 'exclude' must be a list of patterns")
    c.include, c.exclude = inc, exc
    c.new_page_max = raw.get("new_page_max")
    if c.new_page_max is not None and (not isinstance(c.new_page_max, int) or c.new_page_max < 0):
        raise al.Refusal("config: new_page_max must be a whole number")
    # names -------------------------------------------------------------------------------------------------------
    n = raw.get("names") or {}
    if not isinstance(n, dict):
        raise al.Refusal("config: 'names' must be an object")
    c.entry_prefixes = [p if p.endswith("/") else p + "/" for p in (n.get("entry_prefixes") or al.DEFAULT_PREFIXES)]
    c.read_blocks = _sels(n.get("read_blocks") or [], "names.read_blocks")
    c.name_skip = _sels(n.get("skip") or [], "names.skip")
    c.include_tables = bool(n.get("include_tables", False))
    c.particles = {loose(x) for x in (n.get("particles") or DEFAULT_PARTICLES)}
    c.stop = {loose(x) for x in DEFAULT_STOP} | {loose(x) for x in (n.get("stop_words") or [])}
    c.max_words = int(n.get("max_words") or 5)
    c.given_extra = {loose(x) for x in (n.get("given_names") or [])}
    if n.get("given_names_file"):
        gp = n["given_names_file"]
        gp = gp if os.path.isabs(gp) else os.path.join(os.path.dirname(os.path.abspath(path)), gp)
        try:
            c.given_extra |= {loose(str(x)) for x in json.load(open(gp, encoding="utf-8"))}
        except (OSError, ValueError, TypeError):
            raise al.Refusal("config: names.given_names_file cannot be read as a JSON list")
    c.surname_words = {loose(x) for x in (n.get("surname_words") or [])}
    c.auto_surname_min = int(n.get("auto_surname_min") or 3)
    c.not_names = [_rx(r, "", "names.not_names") for r in (n.get("not_names") or [])]
    c.allow = []
    for a in (n.get("allow") or []):
        if not isinstance(a, dict) or not isinstance(a.get("phrase"), str) or not a["phrase"].strip() \
                or not isinstance(a.get("reason"), str) or len(a["reason"].strip()) < 8:
            raise al.Refusal("config: every names.allow entry needs a phrase and a reason of at least 8 characters")
        c.allow.append(loose(a["phrase"]))
    # citations ---------------------------------------------------------------------------------------------------
    ci = raw.get("citations")
    if not isinstance(ci, dict) or not ci.get("patterns"):
        raise al.Refusal("config: 'citations.patterns' is empty: with no pattern for a record citation nothing is examined")
    c.blocks = _sels(ci.get("blocks") or DEFAULT_BLOCKS, "citations.blocks")
    c.next_max = int(ci.get("next_block_max_chars") or 240)
    c.patterns = []
    seen_ids = set()
    for p in ci["patterns"]:
        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not isinstance(p.get("regex"), str) or p["id"] in seen_ids:
            raise al.Refusal("config: each citation pattern needs a unique 'id' and a 'regex'")
        seen_ids.add(p["id"])
        c.patterns.append((p["id"], _rx(p["regex"], p.get("flags"), "citation pattern"), p.get("key")))
    rl = ci.get("record_links")
    if not isinstance(rl, dict) or not (rl.get("prefixes") or rl.get("hosts") or rl.get("fragments")):
        raise al.Refusal("config: 'citations.record_links' must name what counts as a link to a record (prefixes, hosts, fragments)")
    c.rl_prefixes = [al.norm_url(x) if x.startswith("/") else x for x in (rl.get("prefixes") or [])]
    c.rl_hosts = [h.lower() for h in (rl.get("hosts") or [])]
    c.rl_contains = list(rl.get("url_contains") or [])
    c.rl_fragments = list(rl.get("fragments") or [])
    # scans -------------------------------------------------------------------------------------------------------
    sc = raw.get("scans")
    c.scans = None
    c.link_only = set()
    c.aliases = {}
    c.image_patterns = []
    c.held_keys_file = None
    if not isinstance(sc, dict) or not sc:
        raise al.Refusal("config: 'scans' is missing: give image_patterns, or {\"none\": \"why this archive holds no scan to show\"}")
    if "none" in sc:
        if not isinstance(sc["none"], str) or len(sc["none"].strip()) < 8:
            raise al.Refusal("config: scans.none needs a reason of at least 8 characters")
    else:
        if not sc.get("image_patterns"):
            raise al.Refusal("config: scans.image_patterns is empty")
        c.scans = True
        c.aliases = {loose(k): loose(v) for k, v in (sc.get("aliases") or {}).items()}
        c.link_only = set(sc.get("link_only") or [])
        for p in sc["image_patterns"]:
            if not isinstance(p, dict) or not isinstance(p.get("regex"), str) or not isinstance(p.get("key"), str):
                raise al.Refusal("config: each scans.image_patterns entry needs a 'regex' and a 'key' template")
            c.image_patterns.append((_rx(p["regex"], p.get("flags"), "image pattern"), p["key"]))
        c.held_keys_file = sc.get("held_keys_file")
        if not any(k for (_i, _r, k) in c.patterns):
            raise al.Refusal("config: scans are configured but no citation pattern has a 'key' to match them with")
    return c


def url_match(url, pats):
    return any(fnmatch.fnmatchcase(url, p) for p in pats)


# ----------------------------------------------------------------------------------------------------------- one page
class Block:
    __slots__ = ("tag", "section", "text", "links", "exempt", "start", "end", "cites", "passage")

    def __init__(self, tag, section, exempt, start, passage):
        self.tag, self.section, self.exempt, self.start, self.passage = tag, section, exempt, start, passage
        self.text, self.links, self.end, self.cites = [], [], None, []


class Frame:
    __slots__ = ("tag", "attrs", "skip", "bold", "read", "heading", "a", "exempt", "name_exempt", "table", "block")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs = tag, attrs
        p = parent
        self.skip = p.skip if p else False
        self.bold = (p.bold if p else False) or tag in BOLD
        self.read = p.read if p else False
        self.heading = (p.heading if p else False) or (len(tag) == 2 and tag[0] == "h" and tag[1] in "123456")
        self.a = (p.a if p else False) or tag == "a"
        self.exempt = p.exempt if p else None
        self.name_exempt = p.name_exempt if p else False
        self.table = (p.table if p else False) or tag == "table"
        self.block = None


class Walker(HTMLParser):
    """One pass over one page: sections, passages, links, images, and the name-like phrases of the places L2 and L5 read."""

    def __init__(self, cfg, known, vocab, scope):
        super().__init__(convert_charrefs=True)
        self.cfg, self.known, self.vocab, self.scope = cfg, known, vocab, scope
        self.stack, self.blocks, self.open_blocks = [], [], []
        self.n_scope = 0
        self.section = 0
        self.tick = 0
        self.ids = set()
        self.images = {}                      # section -> [src]
        self.scope_seen = False
        self.bad_exempt = 0
        # names
        self.l2 = set()                       # distinct loose phrases
        self.l5 = set()                       # (section, form)
        self.full_seen = {}                   # section -> set of loose words written in a full name
        self.ex_names = 0
        self.names_seen = 0

    # -- structure
    def _implied(self, tag):
        """Close what HTML closes implicitly, so an unclosed <p> or <li> does not swallow the page."""
        closers = {"p": {"p"}, "li": {"li"}, "dd": {"dd", "dt"}, "dt": {"dd", "dt"}, "td": {"td", "th"}, "th": {"td", "th"},
                   "tr": {"td", "th", "tr"}}
        blockish = {"div", "ul", "ol", "table", "section", "blockquote", "figure", "h1", "h2", "h3", "h4", "h5", "h6", "pre",
                    "hr", "dl", "form", "header", "footer", "article", "aside", "nav", "main"}
        if tag in closers:
            for k in range(len(self.stack) - 1, -1, -1):
                if self.stack[k].tag in closers[tag]:
                    self._pop_to(k)
                    break
                if self.stack[k].tag in ("ul", "ol", "table", "dl", "div", "section"):
                    break
        if tag in blockish:
            for k in range(len(self.stack) - 1, -1, -1):
                if self.stack[k].tag == "p":
                    self._pop_to(k)
                    break
                if self.stack[k].tag in ("div", "section", "li", "td", "th", "blockquote", "figure"):
                    break

    def _pop_to(self, k):
        while len(self.stack) > k:
            f = self.stack.pop()
            if f.block is not None:
                self.tick += 1
                f.block.end = self.tick
                if self.open_blocks and self.open_blocks[-1] is f.block:
                    self.open_blocks.pop()
            if f.tag == "section" and self.n_scope:
                self.section += 1
            if f.tag == self.scope:
                self.n_scope -= 1

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        self._implied(tag)
        selfclose = tag in VOID
        parent = self.stack[-1] if self.stack else None
        if tag == self.scope and self.n_scope == 0:
            self.section += 1
            self.scope_seen = True
        if self.n_scope and tag in al.SECTION_TAGS:
            self.section += 1
        if "id" in a:
            self.ids.add(a["id"])
        if self.n_scope == 0 and tag != self.scope:
            if not selfclose:
                self.stack.append(Frame(tag, a, parent))
            return
        f = Frame(tag, a, parent)
        c = self.cfg
        if tag in al.SKIP_TAGS or "data-no-autolink" in a or any(s.match(tag, a) for s in c.name_skip) \
                or (tag == "table" and not c.include_tables):
            f.skip = True
        if "data-name-exempt" in a:
            if not a["data-name-exempt"].strip():
                self.bad_exempt += 1
            f.name_exempt = True
        if any(s.match(tag, a) for s in c.read_blocks):
            f.read = True
        if "data-cite-exempt" in a:
            if not a["data-cite-exempt"].strip():
                self.bad_exempt += 1
            f.exempt = a["data-cite-exempt"].strip() or "(none)"
        is_passage = any(s.match(tag, a) for s in c.blocks)
        if is_passage or tag in AUX_BLOCKS:
            self.tick += 1
            b = Block(tag, self.section, f.exempt, self.tick, is_passage)
            self.blocks.append(b)
            if not selfclose:
                self.open_blocks.append(b)
            f.block = b
        if tag == "a" and "href" in a:
            for b in self.open_blocks:
                b.links.append((a["href"], "data-cite" in a))
        if tag == "img":
            src = a.get("src") or a.get("data-src") or ""
            if src:
                self.images.setdefault(self.section, []).append(src)
        if tag == "br" and self.open_blocks:
            self.open_blocks[-1].text.append(" ")
        if not selfclose:
            self.stack.append(f)
            if tag == self.scope:
                self.n_scope += 1
        elif f.block is not None:
            self.tick += 1
            f.block.end = self.tick
            if self.open_blocks and self.open_blocks[-1] is f.block:
                self.open_blocks.pop()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1].tag == tag:
            self._pop_to(len(self.stack) - 1)

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k].tag == tag:
                self._pop_to(k)
                return

    # -- text
    def handle_data(self, data):
        if not self.n_scope or not self.stack:
            return
        f = self.stack[-1]
        if f.tag in al.RAW_TEXT:
            return
        if self.open_blocks:
            self.open_blocks[-1].text.append(data)
        if f.skip and not f.a:
            return
        F = al.fold(data)[0]
        if not F.strip():
            return
        self._names(F, f)

    def _runs(self, F):
        """Capitalised runs of words in one text node: [(words, start_index_of_first_token, n_tokens_before_trim)]."""
        toks = [(m.start(), m.end(), m.group(0)) for m in WORD_RE.finditer(F)]
        out, cur = [], []                 # cur: list of (s, e, word, kind)

        def flush():
            nonlocal cur
            while cur and cur[-1][3] == "p":
                cur.pop()
            ws = [w for (_s, _e, w, _k) in cur]
            # leading and trailing function words are not part of a name
            lo, hi = 0, len(cur)
            while lo < hi and loose(cur[lo][2]) in self.cfg.stop:
                lo += 1
            while hi > lo and loose(cur[hi - 1][2]) in self.cfg.stop:
                hi -= 1
            if hi > lo:
                out.append([w.replace("’", "'") for (_s, _e, w, _k) in cur[lo:hi]])
            cur = []

        for (s, e, w) in toks:
            if w[-2:].lower() in ("'s", "’s"):
                w = w[:-2]
            cap = w[:1].isupper() and len(w) >= 2
            sep_ok = bool(cur) and F[cur[-1][1]:s] == " "
            if cap and (not cur or sep_ok):
                cur.append((s, e, w, "c"))
            elif cap:
                flush()
                cur.append((s, e, w, "c"))
            elif cur and sep_ok and loose(w) in self.cfg.particles:
                cur.append((s, e, w, "p"))
            else:
                flush()
        flush()
        return out

    def _is_namelike(self, words):
        return any(loose(w) in self.vocab for w in words)

    def _names(self, F, f):
        c = self.cfg
        sec = self.section
        runs = self._runs(F)
        if f.a:
            # text inside a link: a full name written here counts as written in full for this section
            for ws in runs:
                self.full_seen.setdefault(sec, set()).update(loose(w) for w in ws)
            return
        if f.heading or f.skip:
            return
        in_l2 = f.bold or f.read
        for ws in runs:
            phrase = " ".join(ws)
            key = loose(phrase)
            words = [loose(w) for w in ws if loose(w) not in c.particles]
            if len(ws) == 1:
                w = words[0] if words else ""
                if w in self.vocab:
                    self.names_seen += 1
                    if w not in self.full_seen.get(sec, ()):
                        if f.name_exempt:
                            self.ex_names += 1
                        else:
                            self.l5.add((sec, "bare:" + w))
                        self.full_seen.setdefault(sec, set()).add(w)
                continue
            if len(ws) > c.max_words:
                continue
            if key in self.known:
                self.full_seen.setdefault(sec, set()).update(words)
                continue
            if not self._is_namelike(ws):
                continue
            if any(r.search(phrase) for r in c.not_names):
                continue
            self.names_seen += 1
            if key in c.allow or f.name_exempt:
                self.ex_names += 1
                continue
            if in_l2:
                self.l2.add(key)
            else:
                self.l5.add((sec, "run:" + key))


# ----------------------------------------------------------------------------------------------------------- analysis
def is_record_link(href, cite_marked, cfg, ids):
    href = (href or "").strip()
    if not href:
        return False
    if cite_marked and href not in ("#", ""):
        return True
    if href.startswith("#"):
        return any(href.startswith(fr) for fr in cfg.rl_fragments) and href[1:] in ids
    if href.startswith("/") and not href.startswith("//"):
        p = al.norm_url(href)
        return any(p.startswith(x) for x in cfg.rl_prefixes)
    m = re.match(r"^(?:https?:)?//([^/:?#]+)(.*)$", href, re.I)
    if m:
        host = m.group(1).lower()
        if any(host == h or host.endswith("." + h) for h in cfg.rl_hosts):
            return (not cfg.rl_contains) or any(x in href for x in cfg.rl_contains)
    return False


def analyse_page(html, cfg, idx_scan_inputs, known, vocab):
    """Returns (counts dict, info dict) for one in-scope page. idx_scan_inputs = (idx,) for L1."""
    (idx,) = idx_scan_inputs
    w = Walker(cfg, known, vocab, cfg.scope)
    w.feed(html)
    w.close()
    while w.stack:
        w._pop_to(len(w.stack) - 1)
    sc1 = al.scan_html(html, idx, cfg.scope)
    return w, sc1


def citations_of(block, cfg):
    text = squash("".join(block.text))
    hits = []
    for (pid, rx, tmpl) in cfg.patterns:
        for m in rx.finditer(text):
            hits.append((pid, tmpl, m.groupdict()))
    return text, hits


def page_counts(w, sc1, cfg, held, info):
    """L1..L5 and EX for one walked page. `held` = set of scan keys the archive holds."""
    counts = {k: 0 for k in KEYS}
    counts["L1"] = len(sc1.inserts)
    counts["L2"] = len(w.l2)
    counts["L5"] = len(w.l5)
    counts["EX"] = w.ex_names
    sec_keys = {}
    if cfg.scans:
        for sec, srcs in w.images.items():
            for s in srcs:
                for (rx, tmpl) in cfg.image_patterns:
                    m = rx.search(s)
                    if m:
                        k = key_of(tmpl, m.groupdict(), cfg.aliases)
                        if k:
                            sec_keys.setdefault(sec, set()).add(k)
    bl = [b for b in w.blocks]
    texts = {}
    for i, b in enumerate(bl):
        if not b.passage:
            continue
        text, hits = citations_of(b, cfg)
        b.cites = hits
        texts[id(b)] = text
        if not hits:
            continue
        info["citing"] += 1
        if b.exempt is not None:
            counts["EX"] += 1
            info["exempt"] += 1
            continue
        linked = any(is_record_link(h, cm, cfg, w.ids) for (h, cm) in b.links)
        if not linked:
            # the next block (in order, after this one closes) in the same section, when it is a short apparatus line or a figure
            nxt = next((x for x in bl[i + 1:] if x.start > (b.end or 0)), None)
            if nxt is not None and nxt.section == b.section \
                    and any(is_record_link(h, cm, cfg, w.ids) for (h, cm) in nxt.links):
                nt = squash("".join(nxt.text))
                if nxt.tag in AUX_BLOCKS or len(nt) <= cfg.next_max:
                    linked = True
        if linked:
            info["linked"] += 1
        else:
            counts["L3"] += 1
        if cfg.scans:
            miss = False
            for (pid, tmpl, gd) in hits:
                if tmpl is None or pid in cfg.link_only:
                    continue
                k = key_of(tmpl, gd, cfg.aliases)
                if k and k in held:
                    info["held"] += 1
                    if k not in sec_keys.get(b.section, ()):
                        miss = True
            if miss:
                counts["L4"] += 1
    return counts


# ----------------------------------------------------------------------------------------------------------- the build
def index_vocab(path, cfg):
    """From the archive's index: every name and alias (what has an entry), the given-name words, and the entry addresses."""
    d = json.load(open(path, encoding="utf-8"))
    known, given, last, urls = set(), set(), {}, set()
    for field in ("people", "ambiguous"):
        for r in (d.get(field) or []):
            if not isinstance(r, dict) or not isinstance(r.get("name"), str):
                continue
            u = r.get("url")
            if isinstance(u, str) and u.startswith("/"):
                urls.add(al.norm_url(u))
            known.add(loose(r["name"]))
            ws = loose(r["name"]).split(" ")
            ws = [x for x in ws if x not in cfg.particles]
            for x in ws[:-1]:
                given.add(x)
            if ws:
                last.setdefault(ws[-1], set()).add(loose(r["name"]))
            for a in (r.get("aliases") or []):
                if isinstance(a, str):
                    known.add(loose(a))
    surn = {w for w, names in last.items() if len(names) >= cfg.auto_surname_min} | cfg.surname_words
    vocab = ({g for g in given if len(g) >= 3 and g not in surn} | cfg.given_extra) - cfg.surname_words - cfg.stop
    return known, vocab, urls


def held_keys(dist, pages, cfg):
    keys = set()
    if not cfg.scans:
        return keys
    for p in pages:
        h = al.read_page(p)
        for m in IMG_RE.finditer(h):
            src = m.group(1) or m.group(2) or ""
            for (rx, tmpl) in cfg.image_patterns:
                mm = rx.search(src)
                if mm:
                    k = key_of(tmpl, mm.groupdict(), cfg.aliases)
                    if k:
                        keys.add(k)
    if cfg.held_keys_file:
        try:
            for k in json.load(open(cfg.held_keys_file, encoding="utf-8")):
                keys.add(str(k).strip().casefold())
        except (OSError, ValueError, TypeError):
            raise al.Refusal("scans.held_keys_file cannot be read as a JSON list")
    return keys


def load_floor(path):
    if not path or not os.path.exists(path):
        return None
    try:
        d = json.load(open(path, encoding="utf-8"))
        pg = d["pages"]
        assert isinstance(pg, dict)
        for k, v in pg.items():
            assert isinstance(k, str) and isinstance(v, dict)
            for kk, vv in v.items():
                assert kk in KEYS and isinstance(vv, int) and vv >= 0
        return pg
    except (OSError, ValueError, KeyError, AssertionError, TypeError):
        raise al.Refusal("the floor file %s is not a valid {\"pages\": {url: {\"L1\": n, ...}}} file" % path)


def evaluate(results, floor, new_max):
    v = []
    s = {"rises": 0, "new_bad": 0, "below": 0}
    for url, c in sorted(results.items()):
        if floor is not None and url in floor:
            fl = floor[url]
            rose = [k for k in KEYS if c[k] > fl.get(k, new_max)]
            if rose:
                s["rises"] += 1
                v.append(("rise", url, "; ".join("%s %d, floor %d" % (k, c[k], fl.get(k, new_max)) for k in rose)))
            elif any(c[k] < fl.get(k, new_max) for k in KEYS):
                s["below"] += 1
        else:
            over = [k for k in KEYS if c[k] > new_max]
            if over:
                s["new_bad"] += 1
                v.append(("new", url, "a page not in the floor: %s (allowed %d each)" % ("; ".join("%s %d" % (k, c[k]) for k in over), new_max)))
    return v, s


def main(argv=None):
    ap = argparse.ArgumentParser(description="The gate behind the linking standard (see the docstring).")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--index", required=True)
    ap.add_argument("--config", default="standard.json")
    ap.add_argument("--living")
    ap.add_argument("--floor", default=".standardfloor.json")
    ap.add_argument("--write-floor", action="store_true")
    ap.add_argument("--new-page-max", type=int, default=None)
    ap.add_argument("--allow-prefix", action="append", default=[])
    ap.add_argument("--min-words", type=int, default=2)
    ap.add_argument("--table", action="store_true", help="print the counts of every page in scope")
    a = ap.parse_args(argv)
    dist = _outdir.resolve(a.dist)
    try:
        cfg = load_config(a.config)
        a.allow_prefix = a.allow_prefix or cfg.entry_prefixes
        idx, prefixes = al.prepare(a)
        ln, _lu = al.load_living(a.living)
        if any(p in ln for p in cfg.allow):
            raise al.Refusal("LIVING: %d allow entr%s in the config the living list also holds"
                             % (sum(1 for p in cfg.allow if p in ln), "y is one" if sum(1 for p in cfg.allow if p in ln) == 1 else "ies are ones"))
        known, vocab, entry_urls = index_vocab(a.index, cfg)
        if not os.path.isdir(dist) or not al.html_pages(dist):
            raise al.Refusal("no built page under %s: nothing was examined" % dist)
        floor = load_floor(a.floor)
    except al.Refusal as e:
        print("checkstandard: REFUSED. %s" % e)
        return 2
    new_max = a.new_page_max if a.new_page_max is not None else (cfg.new_page_max if cfg.new_page_max is not None else 3)
    before = _outdir.fingerprint(dist)
    pages = al.html_pages(dist)
    urls = {al.page_url(dist, p): p for p in pages}
    in_public = lambda u: any(u.startswith(x) for x in prefixes + cfg.entry_prefixes)  # noqa: E731
    scoped = {}
    unmatched = 0
    for pat in cfg.include:
        hit = [u for u in urls if fnmatch.fnmatchcase(u, pat) and not url_match(u, cfg.exclude) and not in_public(u)]
        if not hit:
            unmatched += 1
        for u in hit:
            scoped[u] = urls[u]
    if unmatched:
        print("checkstandard: REFUSED. %d include pattern%s of the config matched no built page (a mistyped page would escape the gate)"
              % (unmatched, "" if unmatched == 1 else "s"))
        return 2
    if not scoped:
        print("checkstandard: REFUSED. no page is in scope: nothing was examined")
        return 2
    try:
        held = held_keys(dist, pages, cfg)
    except al.Refusal as e:
        print("checkstandard: REFUSED. %s" % e)
        return 2
    results, info_all = {}, {"citing": 0, "linked": 0, "held": 0, "exempt": 0}
    bad_exempt = 0
    no_scope = 0
    links = []
    for u in sorted(scoped):
        html = al.read_page(scoped[u])
        w, sc1 = analyse_page(html, cfg, (idx,), known, vocab)
        if not w.scope_seen:
            no_scope += 1
            continue
        bad_exempt += w.bad_exempt
        info = {"citing": 0, "linked": 0, "held": 0, "exempt": 0}
        results[u] = page_counts(w, sc1, cfg, held, info)
        for l in sc1.autolinks:
            links.append((u, l["href"], l["text"]))
        for k in info_all:
            info_all[k] += info[k]
    if _outdir.settled(dist, before, "checkstandard"):
        return 2
    if not results:
        print("checkstandard: REFUSED. none of the %d in-scope pages has a <%s>: wrong scope, or nothing was built" % (len(scoped), cfg.scope))
        return 2
    if info_all["citing"] == 0:
        print("checkstandard: REFUSED. no passage on the %d in-scope pages matches a citation pattern: the patterns found nothing, so nothing was examined"
              % len(results))
        return 2
    note = _outdir.note(dist)
    if note:
        print(note)
    # structural failures
    viol = []
    built_paths = {al.norm_url(u).split("?")[0] for u in urls}
    dead = sum(1 for u in entry_urls if u.split("?")[0] not in built_paths)
    if dead:
        viol.append(("dead", None, "%d index address%s not a built page (a name linked to nowhere)" % (dead, " is" if dead == 1 else "es are")))
    if bad_exempt:
        viol.append(("exempt", None, "%d data-cite-exempt or data-name-exempt with no reason" % bad_exempt))
    # checklinks' own stale and living checks, over the in-scope pages
    lv, _s = cl.evaluate({}, links, idx, None, 3, idx.living_names, idx.living_urls)
    viol += lv
    rv, s = evaluate(results, floor, new_max)
    viol += rv
    tot = {k: sum(c[k] for c in results.values()) for k in KEYS}
    base = ("%d pages, %d in scope; L1 %d, L2 %d, L3 %d, L4 %d, L5 %d, EX %d; %d passages cite a record (%d linked, %d exempt), "
            "%d scan keys held; floor %s"
            % (len(pages), len(results), tot["L1"], tot["L2"], tot["L3"], tot["L4"], tot["L5"], tot["EX"],
               info_all["citing"], info_all["linked"], info_all["exempt"], len(held),
               ("%d pages" % len(floor)) if floor is not None else "absent"))
    if a.table:
        for u in sorted(results):
            lab = cl.label(u, prefixes) or u
            print("  %-34s %s" % (lab, "  ".join("%s %d" % (k, results[u][k]) for k in KEYS)))
    if a.write_floor:
        viol = [x for x in viol if x[0] != "new"]
        if viol:
            print("checkstandard: FLOOR NOT WRITTEN, %d problem(s) first:" % len(viol))
            print("\n".join(cl.render(viol, prefixes)))
            print("  " + base)
            return 1
        old = floor or {}
        new = {}
        for u, c in results.items():
            new[u] = {k: (min(old[u].get(k, c[k]), c[k]) if u in old else c[k]) for k in KEYS}
        dropped = len([u for u in old if u not in results])
        with open(a.floor, "w", encoding="utf-8") as fh:
            fh.write('{\n "version": %d,\n "note": "Per page, per rule: violations of the linking standard. A number may only go down. '
                     'Written by checkstandard.py --write-floor; raise one only by hand, in a commit that says why. Counts only: no name.",\n "pages": {\n'
                     % FLOOR_VERSION)
            fh.write(",\n".join('  %s: {%s}' % (json.dumps(k, ensure_ascii=False), ", ".join('"%s": %d' % (kk, new[k][kk]) for kk in KEYS))
                                for k in sorted(new)))
            fh.write("\n }\n}\n")
        print("checkstandard: floor written to %s: %d pages (%d new, %d dropped). %s"
              % (a.floor, len(new), len([u for u in new if u not in old]), dropped, base))
        return 0
    if viol:
        print("checkstandard: FAIL (%d)" % len(viol))
        print("\n".join(cl.render(viol, prefixes)))
        print("  " + base)
        return 1
    extra = ""
    if floor is not None and s["below"]:
        extra = "; %d page(s) are below their floor: run with --write-floor to lock the gain in" % s["below"]
    if floor is None:
        extra = "; no floor file, so every page was held to a new-page maximum of %d per rule" % new_max
    print("checkstandard: ok. " + base + extra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
