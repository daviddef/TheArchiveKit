#!/usr/bin/env node
/* The ribbon flags must not make a card taller or wider, nor cover its words (kit/docs/ribbon-flags.md, "Real estate"). This opens
   built pages in a real browser, measures every ribbon card (li.st-rb, li.fr-c) as drawn, then hides every flag strip (.flag-strip)
   and measures again: a card whose height or width changes by more than 0px fails; so does a strip whose box meets the card's glyph,
   its "Gen. n", its name or its years. It checks at each width given (default 1440, 1100 and 390).

     node checkflagfit.mjs --url http://localhost:4321/story/ [--url ...] [--widths 1440,1100,390]
     node checkflagfit.mjs --selftest        a fixture ribbon from the kit's own css, script and flags: clean, then planted faults

   Needs playwright-core and an installed Google Chrome (channel "chrome"); neither is a kit dependency, so this is not in `npm test`:
   run it where an archive builds its pages (npx -y -p playwright-core node ...). Exit 0 clean, 1 a card changed size, 2 it could not
   run or found no flag to check. */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const KIT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const arg = (k) => process.argv.flatMap((a, i) => (a === k ? [process.argv[i + 1]] : []));

async function browser() {
  let pw;
  try { pw = await import("playwright-core"); } catch { console.error("checkflagfit: playwright-core is not installed"); process.exit(2); }
  return (pw.chromium || pw.default.chromium).launch({ channel: "chrome" });
}

const MEASURE = () => [...document.querySelectorAll("li.st-rb, li.fr-c")].map((li) => {
  const r = li.getBoundingClientRect();
  return { w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100, name: (li.querySelector(".st-rb-n, .fr-n") || li).textContent.trim().slice(0, 40) };
});

/* -> {flags, cards, bad: [{card, dw, dh}]} for one page already loaded */
async function measure(page) {
  await page.evaluate(() => (document.fonts ? document.fonts.ready : null));
  const flags = await page.evaluate(() => [...document.querySelectorAll(".flag-strip img")].filter((p) => p.getClientRects().length).length);
  const overlaps = await page.evaluate(() => [...document.querySelectorAll(".flag-strip")].flatMap((st) => {
    const a = st.getBoundingClientRect(), li = st.closest("li");
    return [...li.querySelectorAll(".st-rb-top svg, .st-rb-g, .st-rb-n, .st-rb-y, .fr-g, .fr-n, .fr-y")].filter((e) => {
      const b = e.getBoundingClientRect();
      /* the words' own box, not the block's: a centred name's text */
      const r = document.createRange(); r.selectNodeContents(e); const t = e.tagName === "svg" ? b : r.getBoundingClientRect();
      return t.width > 0 && a.left < t.right && t.left < a.right && a.top < t.bottom && t.top < a.bottom;
    }).map((e) => ({ card: (li.querySelector(".st-rb-n, .fr-n") || li).textContent.trim().slice(0, 40), dw: 0, dh: 0, overlap: e.tagName.toLowerCase() + "." + (e.getAttribute("class") || "") }));
  }));
  const withFlags = await page.evaluate(MEASURE);
  await page.addStyleTag({ content: ".flag-strip{display:none!important}" });
  const without = await page.evaluate(MEASURE);
  const bad = [...overlaps];
  withFlags.forEach((a, i) => {
    const b = without[i];
    const dw = Math.abs(a.w - b.w), dh = Math.abs(a.h - b.h);
    if (dw > 0 || dh > 0) bad.push({ card: a.name, dw, dh });
  });
  return { flags, cards: withFlags.length, bad };
}

async function check(urls, widths) {
  const b = await browser();
  let fails = 0, flagsSeen = 0;
  for (const url of urls) for (const w of widths) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: "networkidle" });
    const r = await measure(page);
    flagsSeen += r.flags;
    console.log(`${r.bad.length ? "FAIL" : "ok  "} ${url} at ${w}px: ${r.cards} cards, ${r.flags} flags shown, max delta `
      + `${Math.max(0, ...r.bad.map((x) => Math.max(x.dw, x.dh)))}px`);
    for (const x of r.bad) console.log(`       ${x.card}: ${x.overlap ? "the flags cover " + x.overlap : `width ${x.dw}px, height ${x.dh}px`}`);
    fails += r.bad.length;
    await ctx.close();
  }
  await b.close();
  return { fails, flagsSeen };
}

async function selftest() {
  const css = fs.readFileSync(path.join(KIT, "styles", "story.css"), "utf8");
  const svg = (f) => "data:image/svg+xml," + encodeURIComponent(fs.readFileSync(path.join(KIT, "data", "flags", f), "utf8"));
  const strip = `<span class="flag-strip flag-strip-4"><img class="flag-mini flag-mini-doc" src="${svg("spain-flags--era-1716.svg")}" alt="a" title="a" width="18" height="12">`
    + `<img class="flag-mini flag-mini-doc flag-mini-today" src="${svg("uruguay-flags--era-1830.svg")}" alt="b" title="b" width="18" height="12"></span>`
    + `<span class="flag-strip flag-strip-4 flag-strip-left"><img class="flag-mini flag-mini-doc" src="${svg("argentina-flags--era-1861.svg")}" alt="c" title="c" width="18" height="12"></span>`;
  const cardHtml = (name) => `<li class="st-rb st-rb-doc" data-living="0"><a class="st-rb-top" href="#x"><svg viewBox="-2 -2 28 22" width="26" height="20"><path d="M0 16L7 4L11 10L14 7L21 16Z"/></svg>`
    + `<span class="st-rb-g">Gen. 1</span></a>${strip}<span class="st-rb-n">${name}</span><span class="st-rb-y">1791–1815</span>`
    + `<span class="st-rb-f">from Canelones</span><span class="st-rb-at">at Montevideo, 1812</span><span class="st-rb-s">m. X, of Y</span></li>`;
  const page = (extraCss = "") => `<!doctype html><html><head><meta charset="utf-8"><style>${css}${extraCss}</style></head><body>`
    + `<nav class="st-rib"><ol>${["Félix Llerena", "Sancho Llerena", "Pablo Armando Lerena", "Nuno Fernando Lerena", "Cheryl Anne Lerena", "Juan Carlos Lerena", "Sancho's children"].map(cardHtml).join("")}</ol></nav></body></html>`;
  const cases = [
    ["clean: the strip in the header row", page(), false],
    ["planted: the strip drawn in the flow (not absolutely placed)", page(".flag-strip{position:static}"), true],
    ["planted: the strip moved down onto the name", page(".flag-strip{top:44px}"), true],
    ["planted: flags 30px high in the flow", page(".flag-strip{position:static}.flag-mini{height:30px;width:45px}"), true],
  ];
  const b = await browser();
  let fails = 0;
  for (const [name, html, shouldFail] of cases) for (const w of [1440, 390]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const p = await ctx.newPage();
    await p.setContent(html);
    const r = await measure(p);
    const failed = r.bad.length > 0;
    if (failed !== shouldFail) fails++;
    console.log(`${failed === shouldFail ? "ok  " : "FAIL"} ${name} at ${w}px: ${failed ? "caught (" + r.bad.length + ")" : "clean"}`);
    await ctx.close();
  }
  await b.close();
  console.log(`checkflagfit selftest: ${fails ? fails + " FAILED" : "all ok"}`);
  return fails ? 1 : 0;
}

if (process.argv.includes("--selftest")) process.exit(await selftest());
const urls = arg("--url");
if (!urls.length) { console.error("checkflagfit: --url ... (or --selftest)"); process.exit(2); }
const widths = (arg("--widths")[0] || "1440,1100,390").split(",").map(Number);
const { fails, flagsSeen } = await check(urls, widths);
if (!flagsSeen) { console.error("checkflagfit: no flag was shown on any page: nothing was checked"); process.exit(2); }
console.log(`checkflagfit: ${fails ? fails + " cards changed size" : "every card the same size with and without its flags"}`);
process.exit(fails ? 1 : 0);
