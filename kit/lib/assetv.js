/* Fingerprint a public asset, so its URL changes exactly when it changes.

   Astro hashes the assets it bundles itself. It does not touch anything in
   public/ — styles.css, wholink.js, count.js, bloodline.js — and GitHub Pages
   serves those with max-age=600. Ten minutes does not sound like much until
   somebody is reading a fix back to you as still broken while their browser
   quietly serves the old file, which is exactly how an evening went.

   Six of the seven archives were shipping an unversioned stylesheet and all
   seven an unversioned script. One archive had solved it for CSS alone, in its
   own layout, which is the usual shape of this estate's problems.

   Usage, in a layout's frontmatter:
     const v = versioner(new URL("../../public/", import.meta.url));
     <link rel="stylesheet" href={u("/styles.css") + v("styles.css")} />

   A missing file returns "" rather than throwing: a fingerprint is a cache
   hint, and it should never be the reason a build fails. */
import fs from "node:fs";
import crypto from "node:crypto";

export function versioner(publicDir) {
  const cache = new Map();
  return function v(rel) {
    if (cache.has(rel)) return cache.get(rel);
    let out = "";
    try {
      out = "?v=" + crypto.createHash("sha1")
        .update(fs.readFileSync(new URL(rel, publicDir)))
        .digest("hex").slice(0, 8);
    } catch (e) { out = ""; }   /* named: esbuild rejects a bare catch here */
    cache.set(rel, out);
    return out;
  };
}
