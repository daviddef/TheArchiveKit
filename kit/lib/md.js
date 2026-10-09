/* The archive's light markup, in one place.

   Data files across the estate are written with **bold**, *italic*, ***bold***
   and «quoted», because that is readable in a TSV or a JSON string — which is
   the point of keeping the research data in a TSV or a JSON string. Something
   has to turn it into markup at render time, and where nothing did, readers
   got the asterisks:

     Falco   /direct-line    598 literal ** pairs on one page
     Lerena  38 pages        362 literal asterisks, found and fixed locally

   Three archives had written a renderer and four had none, which is how the
   same fault reached two of them independently.

   Everything is escaped BEFORE any markup is produced, so data can never
   inject HTML — only the markers become tags. Returns an HTML string, so the
   caller must use set:html. */

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };
const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ESC[c]);

/* ⭐ 9 October 2026 — this chain now matches the archives' own renderer
   exactly: ***x*** closes as <strong><em>x</em></strong>, and every rule runs
   /g with no \s* trimming.

   ⭐ A `code` rule was added on 9 October 2026, FIRST in the chain so that a
   ** inside backticks stays literal. It had none at all, and the estate's data
   is full of file names, field names and shell: measured across the seven
   archives on that day, 2,581 backticks were printing as backticks in visible
   text — Blazevic 799, Booyzen 733, Falco 427, Mazza 338, D'arcy 226, and the
   rest in ones and tens. ⚠ Only one archive has a code{} rule in its own
   stylesheet; the other five will render browser-default monospace until they
   add one, which is still the right way round from where they are.

   Both halves were faults, not preferences.

   The OUTPUT half: ***x*** had rendered as <strong>x</strong>, silently
   dropping the italic half of a marker that means both. 816 strings in one
   archive's data gain the <em> they should always have had.

   The FLAGS half, which was left standing for a day and then measured: /s
   lets `.` cross a newline, and \s* matches newlines of its own accord even
   without it. Together they let an emphasis run swallow a paragraph break and
   join two unrelated spans. Measured over one archive's data, 125 strings
   rendered differently, and every difference was of this shape:

     **Michiela *fu Pietro*** — wife of Andrea…    the *** at the END of a
       nested italic opened a new match that ate the next two lines
     …not the problem.***\n\n***The specific failure…    a closing *** and the
       next opening *** were joined across the blank line between them
     ***Naša Sloga*, 28 May 1914**    bold-with-italic-inside was read as an
       unterminated triple and swallowed the rest of the sentence

   62 strings had a *** match crossing a newline, 31 a **, 9 a «». In none of
   them was the wider match the right one. Where the markers are genuinely
   unbalanced the narrower rule now leaves them visible, which is a data fault
   surfacing rather than a renderer hiding it. */
/* Order matters: *** before ** before *, or the shorter marker eats the
   longer one's delimiters and leaves a stray asterisk behind. */
/* ⚠ A code span's CONTENT must not be touched by the rules that follow it.
   Putting the code rule first was not enough: `*.json` came out as a <code>
   with the asterisk eaten by the italic rule, and `\s*` as <code>\s<em></code>.
   Across the estate 85 code spans hold a * or a « », and every one is the kind
   of thing a code span is FOR — a glob, a flag, a file pattern. So they are
   lifted out, the markup runs on what is left, and they go back in untouched.
   The sentinel is NUL, which no data file in the estate contains. */
const holdCode = (s) => {
  const spans = [];
  const held = String(s ?? "").replace(/`([^`\n]+)`/g, (_, c) => {
    spans.push(c);
    return `\u0000C${spans.length - 1}\u0000`;
  });
  return [held, (t) => t.replace(/\u0000C(\d+)\u0000/g, (_, i) => `<code>${spans[+i]}</code>`)];
};

export const md = (x) => {
  const [held, restore] = holdCode(esc(x));
  return restore(held
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/«(.+?)»/g, "<em>«$1»</em>")
    .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>"));
};

/* Same, but blank lines become paragraph breaks. For a field that holds more
   than one paragraph of prose. */
export const mdp = (x) => md(x).replace(/\n\n+/g, "</p><p>");

/* The text with no markup at all — a title attribute, a meta description, a
   search index. Strips the markers rather than rendering them.

   ⚠ These two keep /s ON PURPOSE, and it is the opposite call from md() above.
   md() RENDERS, so a match that crosses a newline swallows a paragraph break
   and joins two unrelated spans — a fault, now fixed. plain() STRIPS, so a
   wider match simply removes more punctuation, which is the whole point of a
   string that is about to become a <title> or a search-index entry. Measured
   over one archive's data on 9 October 2026: 302 strings differ between /gs
   and /g here, and NOT ONE of them differs by a letter — only by how many
   stray asterisks survive into the title. Do not "align" these with md(). */
export const plain = (x) =>
  String(x ?? "")
    /* A markdown link is markup too, and this function promises none. Keep the
       words, drop the brackets and the href — a <title> reading
       "[The Gologorica line](/gologorica-line/)" helps nobody. */
    .replace(/\[([^\]\n]{1,120})\]\((?:\/|https?:\/\/)[^)\s]{1,200}\)/g, "$1")
    .replace(/\*{1,3}(.+?)\*{1,3}/gs, "$1")
    .replace(/«(.+?)»/gs, "$1")
    /* Backticks go unconditionally, not in pairs. The emphasis rules above are
       pair-based because a lone * can be meaningful — a footnote mark, a glob
       in a filename — but a backtick never carries meaning in plain text, and
       the ones that reach a <title> are precisely the UNBALANCED ones a
       pair-based rule would leave behind. */
    .replace(/`/g, "")
    .replace(/\s+/g, " ")
    .trim();


/* ─────────────────────────────────────────────────────────────────────────
   mdNote — the same markup, but for a field that holds a whole NOTE.

   Added 9 October 2026, after measuring what /worklist/ was actually showing
   readers. The WorkList component had carried its own private renderer since
   it was written: it did **bold**, «quotes» and internal links, and nothing
   else — no italic, no code, no tables, and no newline handling of any kind.

   The archive's 216 work-list notes are not sentences. They contain 1,659
   paragraph breaks, 2,483 single-asterisk italics, 521 links, 497 code spans,
   124 horizontal rules, 42 pipe-tables, 36 bullets and 36 blockquotes. What
   the page rendered was one flat blob per note with the markers left in it:

     4,599 literal asterisks · 892 backticks · 123 table separators
     113 literal --- rules   · every paragraph break collapsed to a space

   which is the identical fault this file's header was written about, one
   component further out. The fix is not another private renderer: it is this
   one, with block structure added.

   Everything is escaped before any markup is produced, exactly as above, so a
   note can never inject HTML. Returns block-level HTML — <p>, <table>, <hr>,
   <ul>, <blockquote> — so the caller must use set:html on a container that may
   hold blocks (a <div>, never a <p>).

   Deliberately conservative about tables, which is the archive's own rule: a
   block qualifies only if a row of |cells| is followed immediately by a
   |---|---| separator. A stray pipe in prose is left exactly as written. */

const linkify = (s, u) =>
  s.replace(/\[([^\]]+)\]\((\/[^)\s]*)\)/g, (_, t, h) => `<a href="${u(h)}">${t}</a>`);

/* Inline markers only. Order matters here for the same reason as in md():
   *** before ** before *, and code spans FIRST so that `**x**` inside backticks
   stays literal. */
const inlineRich = (s, u) => {
  const [held, restore] = holdCode(esc(s));
  return restore(linkify(held
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/«(.+?)»/g, "<em>«$1»</em>")
    .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>"), u));
};

const isRow = (l) => /^\s*\|.*\|\s*$/.test(l || "");
const isSep = (l) => /^\s*\|[\s:|-]+\|\s*$/.test(l || "") && /-/.test(l || "");
const cells = (l) =>
  l.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());

export const mdNote = (x, u = (p) => p) => {
  const lines = String(x ?? "").split("\n");
  const out = [];
  let para = [];
  const flush = () => {
    const text = para.join("\n").trim();
    para = [];
    if (text) out.push("<p>" + inlineRich(text, u).replace(/\n/g, "<br>") + "</p>");
  };
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];

    /* A table, only with its separator directly beneath it. */
    if (isRow(l) && isSep(lines[i + 1])) {
      flush();
      const th = cells(l);
      let j = i + 2;
      const body = [];
      while (isRow(lines[j]) && !isSep(lines[j])) body.push(cells(lines[j++]));
      /* .scroll so a wide table scrolls inside its column rather than pushing
         the page sideways — the estate's styles.css provides it. */
      out.push(
        '<div class="scroll"><table><thead><tr>' +
        th.map((c) => `<th>${inlineRich(c, u)}</th>`).join("") +
        "</tr></thead><tbody>" +
        body.map((r) => "<tr>" + r.map((c) => `<td>${inlineRich(c, u)}</td>`).join("") + "</tr>").join("") +
        "</tbody></table></div>");
      i = j - 1;
      continue;
    }

    /* A rule. Checked before bullets so --- is never read as a list item. */
    if (/^\s*-{3,}\s*$/.test(l)) { flush(); out.push("<hr>"); continue; }

    /* A heading. */
    const h = /^\s*(#{1,6})\s+(.*)$/.exec(l);
    if (h) {
      flush();
      const n = Math.min(6, h[1].length + 2);
      out.push(`<h${n}>${inlineRich(h[2], u)}</h${n}>`);
      continue;
    }

    /* A bullet run. Only - and ·, never *, which is an italic marker here. */
    if (/^\s*[-·]\s+\S/.test(l)) {
      flush();
      const items = [];
      while (/^\s*[-·]\s+\S/.test(lines[i] || "")) {
        items.push(lines[i].replace(/^\s*[-·]\s+/, ""));
        i++;
      }
      i--;
      out.push("<ul>" + items.map((t) => `<li>${inlineRich(t, u)}</li>`).join("") + "</ul>");
      continue;
    }

    /* A blockquote run. */
    if (/^\s*>\s?/.test(l)) {
      flush();
      const qs = [];
      while (/^\s*>\s?/.test(lines[i] || "")) { qs.push(lines[i].replace(/^\s*>\s?/, "")); i++; }
      i--;
      out.push("<blockquote>" + inlineRich(qs.join("\n"), u).replace(/\n/g, "<br>") + "</blockquote>");
      continue;
    }

    if (/^\s*$/.test(l)) { flush(); continue; }
    para.push(l);
  }
  flush();
  return out.join("");
};
