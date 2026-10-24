// node kit/tools/ring_logic.mjs : the row at the foot of every page (components/SiblingArchives.astro,
// data/archives.json, lib/ringcards.js), held to what it promises.
//
//   data    every archive carries what a card needs; no new archive repeats a colour; the colours read on paper and night
//   cards   for each archive standing in the ring, the others appear exactly once, it never appears, and the
//           extra links (Our Family, Record Atlas, defranceski.com) come after, as their own group
//   layout  the component's own CSS keeps ONE line from 1100px (nowrap on the row and both lists, inside that
//           breakpoint) and lets it wrap below; the markup keeps the `ring` class and aria-label the gates read,
//           puts the full name in the link's aria-label and title, and loads nothing
//   proof   the layout check is shown to fail when the nowrap is taken out
import fs from "fs"; import path from "path"; import { fileURLToPath } from "url";
import { ringCards, cardLabel } from "../lib/ringcards.js";
const here = path.dirname(fileURLToPath(import.meta.url));
const kit = path.join(here, "..");
const ring = JSON.parse(fs.readFileSync(path.join(kit, "data", "archives.json"), "utf8"));
const SRC = fs.readFileSync(path.join(kit, "components", "SiblingArchives.astro"), "utf8");
let bad = 0;
const ok = (label, cond, detail) => { if (!cond) { bad++; console.log("  FAIL  " + label + (detail ? "\n         " + detail : "")); } else console.log("  ok    " + label); };

// ---- colours
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const lum = (h) => { const [r, g, b] = rgb(h).map(lin); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const hue = (h) => {
  const [r, g, b] = rgb(h), mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  if (!d) return 0;
  const k = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (k * 60 + 360) % 360;
};
const gap = (a, b) => { const d = Math.abs(hue(a) - hue(b)); return Math.min(d, 360 - d); };

// ---- data
console.log("data");
const A = ring.archives;
ok("eight archives are listed, the count read from the file", A.length === 8, "found " + A.length);
ok("Luwinski is one of them, at its own address", A.some((a) => a.key === "luwinski" && a.url === "https://luwinski.defranceski.com/"));
ok("keys, addresses, names and short names are each unique", ["key", "url", "name", "short"].every((k) => new Set(A.map((a) => a[k])).size === A.length));
ok("every archive has name, short, url, base, where, line, surnames, both accents and a counter",
  A.every((a) => ["key", "name", "short", "url", "where", "line", "accent", "accentDark"].every((k) => typeof a[k] === "string" && a[k].trim())
    && typeof a.base === "string" && Array.isArray(a.surnames) && a.surnames.length && typeof a.counter === "string"),
  A.filter((a) => !a.short).map((a) => a.key).join(","));
ok("a short name is the surname alone: it is in the full name and has no space", A.every((a) => a.name.includes(a.short) && !/\s/.test(a.short)));
ok("every address is https and ends in a slash", A.every((a) => /^https:\/\/[^/]+\/$/.test(a.url)));
ok("no two archives share an accent, light or dark", new Set(A.map((a) => a.accent.toLowerCase())).size === A.length && new Set(A.map((a) => a.accentDark.toLowerCase())).size === A.length);
// Two older pairs sit within 20 degrees (defranceski/darcy, falco/mazza: teal and blue, red and ochre) and are
// let stand; they differ in lightness and in the bar beside a name. A NEW archive must not make a third.
const OLD_CLOSE = new Set(["defranceski/darcy", "falco/mazza"]);
const near = [];
for (const [i, a] of A.entries()) for (const b of A.slice(i + 1)) if (gap(a.accent, b.accent) < 20 && !OLD_CLOSE.has(a.key + "/" + b.key)) near.push(a.key + "/" + b.key);
ok("no accent is within 20 degrees of hue of another, bar the two older pairs", !near.length, near.join(", "));
ok("every light accent is 3:1 or better against paper, every dark one against night",
  A.every((a) => contrast(a.accent, "#fffdf8") >= 3 && contrast(a.accentDark, "#1c1a16") >= 3),
  A.filter((a) => contrast(a.accent, "#fffdf8") < 3 || contrast(a.accentDark, "#1c1a16") < 3).map((a) => a.key).join(","));
ok("links are the Record Atlas and the home page, each with name, url and short",
  JSON.stringify((ring.links || []).map((l) => [l.name, l.url, l.short])) ===
  JSON.stringify([["Record Atlas", "https://recordatlas.org/", "Record Atlas"], ["defranceski.com", "https://defranceski.com/", "defranceski.com"]]));
ok("the children's site stays", ring.children && ring.children.name === "Our Family" && ring.children.url === "https://ourfamily.defranceski.com/");

// ---- cards
console.log("cards");
for (const me of A) {
  const { others, tail } = ringCards(ring, me);
  const keys = others.map((a) => a.key);
  ok(me.key + ": the other " + (A.length - 1) + " each once, itself never",
    keys.length === A.length - 1 && new Set(keys).size === keys.length && !keys.includes(me.key) && A.filter((a) => a !== me).every((a) => keys.includes(a.key)),
    keys.join(","));
  ok(me.key + ": then Our Family, Record Atlas and defranceski.com, as a group of their own",
    JSON.stringify(tail.map(cardLabel)) === JSON.stringify(["Our Family", "Record Atlas", "defranceski.com"]) &&
    JSON.stringify(tail.map((t) => t.url)) === JSON.stringify(["https://ourfamily.defranceski.com/", "https://recordatlas.org/", "https://defranceski.com/"]));
}
{
  const { others } = ringCards(ring, undefined);
  ok("a site not in the file is given every archive", others.length === A.length);
  const none = ringCards({ archives: A }, A[0]);
  ok("a file with no `links` and no `children` still draws the cards", none.others.length === A.length - 1 && none.tail.length === 0);
}
ok("the label of a card is the surname", cardLabel(A[0]) === "Defranceschi" && cardLabel({ name: "The X Archive" }) === "The X Archive");

// ---- layout
console.log("layout");
const style = (SRC.match(/<style>([\s\S]*?)<\/style>/) || [, ""])[1];
const markup = SRC.replace(/<style>[\s\S]*?<\/style>/, "").replace(/^---[\s\S]*?\n---/, "");
// the body of the @media block whose query is `q`, by brace matching, and the css with that block cut out
const media = (css, q) => {
  const at = css.indexOf("@media (" + q + ")");
  if (at < 0) return null;
  const i = css.indexOf("{", at); let depth = 0, j = i;
  for (; j < css.length; j++) { if (css[j] === "{") depth++; else if (css[j] === "}" && --depth === 0) break; }
  return { inner: css.slice(i + 1, j), outer: css.slice(0, at) + css.slice(j + 1) };
};
const rule = (css, sel) => { const m = css.match(new RegExp("(?:^|[}\\s,])" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*(?:,[^{]*)?\\{([^}]*)\\}")); return m ? m[1] : ""; };
function layoutFaults(css) {
  const out = [];
  const wide = media(css, "min-width: 1100px");
  if (!wide) return ["no @media (min-width: 1100px) block"];
  for (const sel of [".rr-row", ".rr-list", ".rr-links"]) {
    if (!/flex-wrap:\s*nowrap/.test(rule(wide.inner, sel))) out.push(sel + " is not nowrap from 1100px");
    if (/flex-wrap:\s*nowrap/.test(rule(wide.outer, sel))) out.push(sel + " is nowrap below 1100px, where it must wrap");
  }
  if (!/flex-wrap:\s*wrap/.test(rule(wide.outer, ".rr-row"))) out.push(".rr-row does not wrap below 1100px");
  if (!/flex-wrap:\s*wrap/.test(rule(wide.outer, ".rr-list"))) out.push(".rr-list does not wrap below 1100px");
  if (/display:\s*none/.test(rule(wide.inner, ".rr-w"))) out.push("the place is hidden on wide screens");
  if (!/display:\s*none/.test(rule(wide.outer, ".rr-w"))) out.push("the place is not hidden below 1100px");
  if (!/min-width:\s*0/.test(rule(wide.outer, ".rr-card"))) out.push("a card cannot shrink (min-width: 0)");
  return out;
}
const faults = layoutFaults(style);
ok("one line from 1100px, wrapping below, the place shown only on wide screens", !faults.length, faults.join("; "));
ok("the section keeps the class and aria-label the gates read", /<section class="ring" aria-label="The other family archives"/.test(markup));
ok("a card is a link with the full name in its title and aria-label",
  /<a href=\{a\.url\} title=\{`\$\{a\.name\} — \$\{a\.where\}`\} aria-label=\{`\$\{a\.name\}, \$\{a\.where\}`\}>/.test(markup));
ok("a link in the second group carries its full name too", /aria-label=\{l\.why \? `\$\{l\.name\}, \$\{l\.why\}` : l\.name\}/.test(markup) && /title=\{l\.line/.test(markup));
ok("keyboard focus is drawn", /a:focus-visible[\s\S]*?outline:\s*2px solid/.test(style));
ok("the stylesheet uses the archive's own tokens, each with a fallback",
  ["--ink", "--ink-3", "--rule", "--panel", "--accent", "--sans", "--serif"].every((t) => new RegExp("var\\(" + t + ",").test(style)));
ok("the accent bar takes --ring-l in light and --ring-d in dark", /var\(--ring-l\)/.test(style) && (style.match(/var\(--ring-d\)/g) || []).length >= 2 && /data-theme="dark"/.test(style));
ok("no images and no requests", !/<img|<script|<link/.test(markup) && !/url\(|@import|https?:\/\//.test(style));
ok("the count is not written into the prose", !/\b(seven|eight|nine)\b/i.test(markup) && !/WORDS/.test(SRC));
ok("the component draws its cards from ringCards", /ringCards\(ring, mine\)/.test(SRC));

// ---- proof that the layout check is a check
console.log("proof");
const sabotage = {
  "nowrap is taken off the row": style.replace(/(@media \(min-width: 1100px\)\s*\{\s*\.rr-row \{)[^}]*\}/, "$1 gap: 0 14px; }"),
  "nowrap is taken off the card list": style.replace(/\.rr-list \{ flex: 1 1 auto; flex-wrap: nowrap;/, ".rr-list { flex: 1 1 auto;"),
  "the 1100px breakpoint moves": style.replace("min-width: 1100px", "min-width: 700px"),
  "the row is forced nowrap below 1100px": style.replace(".rr-row { display: flex; flex-wrap: wrap;", ".rr-row { display: flex; flex-wrap: nowrap;"),
};
for (const [what, css] of Object.entries(sabotage)) {
  ok("the layout check fails when " + what, css !== style && layoutFaults(css).length > 0, css === style ? "(the edit did not apply)" : "");
}

console.log(bad ? "\n" + bad + " failed" : "\nring_logic: all hold");
process.exit(bad ? 1 : 0);
