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

/* ⭐ 9 October 2026 — ***triple*** now closes as <strong><em>x</em></strong>.
   It had been <strong>x</strong>, which silently dropped the italic half of a
   marker that means both. The archives' own renderer was corrected the same
   day and this one was left disagreeing with it; measured over one archive's
   data, 816 strings render differently for the better.

   ⚠ The FLAGS here are deliberately NOT aligned with that renderer, which uses
   /g and no \s* trimming. Measured on the same data, /gs plus \s* changes
   where 95 strings' captures begin and end — a real behaviour change that
   needs its own evidence, not a tidy-up ridden in on this one. */
/* Order matters: *** before ** before *, or the shorter marker eats the
   longer one's delimiters and leaves a stray asterisk behind. */
export const md = (x) =>
  esc(x)
    .replace(/\*\*\*\s*(.+?)\s*\*\*\*/gs, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/gs, "<strong>$1</strong>")
    .replace(/«(.+?)»/gs, "<em>«$1»</em>")
    .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>");

/* Same, but blank lines become paragraph breaks. For a field that holds more
   than one paragraph of prose. */
export const mdp = (x) => md(x).replace(/\n\n+/g, "</p><p>");

/* The text with no markup at all — a title attribute, a meta description, a
   search index. Strips the markers rather than rendering them. */
export const plain = (x) =>
  String(x ?? "")
    .replace(/\*{1,3}(.+?)\*{1,3}/gs, "$1")
    .replace(/«(.+?)»/gs, "$1")
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
const inlineRich = (s, u) =>
  linkify(
    esc(s)
      .replace(/`([^`\n]+)`/g, "<code>$1</code>")
      .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/«(.+?)»/g, "<em>«$1»</em>")
      .replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>"),
    u);

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
