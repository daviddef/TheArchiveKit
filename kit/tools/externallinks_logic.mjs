// Which links open in a new tab (lib/externallinks.js), and that the component ships exactly that function.
//   node kit/tools/externallinks_logic.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const { opensElsewhere: f } = await import(pathToFileURL(path.join(here, "..", "lib", "externallinks.js")).href);
const HERE = "https://archive.defranceski.com/errands/";
let n = 0, bad = 0;
const eq = (label, got, want) => { n++; if (got !== want) { bad++; console.log(`  FAIL  ${label}: got ${got}, want ${want}`); } };

eq("another host opens in a new tab", f("https://www.familysearch.org/ark:/61903/3:1:ABC", HERE), true);
eq("the Atlas is another host", f("https://recordatlas.org/tree-canvas/", HERE), true);
eq("a sister archive is another host", f("https://booyzen.example.org/", HERE), true);
eq("a protocol-relative link to another host", f("//example.org/x", HERE), true);
eq("same host, absolute", f("https://archive.defranceski.com/people/", HERE), false);
eq("same host, relative path", f("/people/", HERE), false);
eq("same host, a fragment", f("#errand-3", HERE), false);
eq("same host, a relative file", f("page/", HERE), false);
eq("mailto is never a new tab", f("mailto:a@b.org", HERE), false);
eq("tel is never a new tab", f("tel:+61", HERE), false);
eq("javascript: is never a new tab", f("javascript:void(0)", HERE), false);
eq("no address", f("", HERE), false);
eq("a download is left alone", f("https://example.org/f.pdf", HERE, null, true), false);
eq("an existing target _blank is left alone", f("https://example.org/", HERE, "_blank"), false);
eq("an explicit target _self on another host still opens in a new tab", f("https://example.org/", HERE, "_self"), true);
eq("another origin on a different port is another host", f("https://archive.defranceski.com:8443/", HERE), true);
eq("an unparsable link is left alone", f("http://", HERE), false);

// the component writes this function's own source into the page
const comp = fs.readFileSync(path.join(here, "..", "components", "ExternalLinks.astro"), "utf8");
n++; if (!/opensElsewhere\.toString\(\)/.test(comp)) { bad++; console.log("  FAIL  ExternalLinks.astro no longer ships lib/externallinks.js's function"); }
const sib = fs.readFileSync(path.join(here, "..", "components", "SiblingArchives.astro"), "utf8");
n++; if (!/<ExternalLinks \/>/.test(sib)) { bad++; console.log("  FAIL  SiblingArchives.astro no longer renders ExternalLinks (no page would get the behaviour)"); }
// no outside names in the function: it must run from a string
n++; try { const src = f.toString(); new Function("return (" + src + ")")()("https://x.org/", "https://y.org/"); } catch (e) { bad++; console.log("  FAIL  the function does not stand alone: " + e.message); }

console.log(bad ? `externallinks: ${bad} of ${n} FAILED` : `  ok    ${n} checks, which links open in a new tab`);
process.exit(bad ? 1 : 0);
