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

/* Order matters: *** before ** before *, or the shorter marker eats the
   longer one's delimiters and leaves a stray asterisk behind. */
export const md = (x) =>
  esc(x)
    .replace(/\*\*\*\s*(.+?)\s*\*\*\*/gs, "<strong>$1</strong>")
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
