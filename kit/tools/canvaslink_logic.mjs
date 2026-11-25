// The address that opens an archive (and one person) on the Tree Canvas (lib/canvaslink.js), and that the component and the chart ship it.
//   node kit/tools/canvaslink_logic.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const kit = path.join(here, "..");
const { canvasHref: f, SLUG } = await import(pathToFileURL(path.join(kit, "lib", "canvaslink.js")).href);
const keys = JSON.parse(fs.readFileSync(path.join(kit, "data", "archives.json"), "utf8")).archives.map((a) => a.key);
let n = 0, bad = 0;
const eq = (label, got, want) => { n++; if (got !== want) { bad++; console.log(`  FAIL  ${label}: got ${got}, want ${want}`); } };
const T = "https://recordatlas.org/tree-canvas/";

for (const k of keys) eq(`${k} opens its archive`, f(k, null, keys), `${T}?archive=${k}`);
eq("a person is carried as p", f("mazza", "frank-mazza", keys), `${T}?archive=mazza&p=frank-mazza`);
eq("a slug with a digit and a hyphen", f("falco", "raffaele-falco-2", keys), `${T}?archive=falco&p=raffaele-falco-2`);
eq("an accented or upper-case slug is left off, the archive still opens", f("mazza", "Alfia-Cannavò", keys), `${T}?archive=mazza`);
eq("a slug with a slash or a space is left off", f("mazza", "a/b c", keys), `${T}?archive=mazza`);
eq("an empty slug is left off", f("mazza", "", keys), `${T}?archive=mazza`);
eq("a slug over 120 characters is left off", f("mazza", "a".repeat(121), keys), `${T}?archive=mazza`);
eq("a slug of 120 is kept", f("mazza", "a".repeat(120), keys), `${T}?archive=mazza&p=${"a".repeat(120)}`);
eq("an unknown archive is no link", f("nobody", null, keys), null);
eq("no archive is no link", f(undefined, null, keys), null);
eq("an empty archive is no link", f("", null, keys), null);
eq("a key with a query in it is no link", f("mazza&x=1", null), null);
eq("without a key list only the shape is checked", f("mazza", null), `${T}?archive=mazza`);
eq("the slug rule is the canvas's own", String(SLUG), String(/^[a-z0-9-]{1,120}$/));

/* the canvas (Record Atlas) must know every key the kit lists: its ARCH map is the other half of this contract */
eq("eight archives", keys.length, 8);

const comp = fs.readFileSync(path.join(kit, "components", "CanvasLink.astro"), "utf8");
eq("the component builds its address with canvasHref", /canvasHref\(archive, person, keys\)/.test(comp), true);
eq("the component stops the build on an unknown key", /throw new Error\(`CanvasLink:/.test(comp), true);
eq("the component opens in a new tab safely", /target="_blank" rel="noopener"/.test(comp), true);
const anc = fs.readFileSync(path.join(kit, "components", "AncChart.astro"), "utf8");
eq("AncChart draws by default", /draw = true/.test(anc), true);
eq("AncChart can leave the picture out", /\{draw && \(\s*<div class="ac-scroll">/.test(anc), true);

console.log(bad ? `${bad} of ${n} FAILED` : `canvaslink: ${n} checks ok`);
process.exit(bad ? 1 : 0);
