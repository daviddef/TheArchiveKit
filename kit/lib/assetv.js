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
     const v = versioner();
     <link rel="stylesheet" href={u("/styles.css") + v("styles.css")} />

   It reads from public/ relative to the working directory, which is where
   Astro builds from. The first version took a URL built with import.meta.url,
   which is the idiomatic thing and which esbuild refused to parse in six of
   the seven layouts while accepting it in the seventh. Not worth chasing: a
   relative path has fewer moving parts and works everywhere.

   A missing file returns "" rather than throwing: a fingerprint is a cache
   hint, and it should never be the reason a build fails. */
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";

export function versioner(publicDir) {
  const dir = publicDir || "public";
  const cache = new Map();
  return function v(rel) {
    if (cache.has(rel)) return cache.get(rel);
    let out = "";
    try {
      out = "?v=" + crypto.createHash("sha1")
        .update(fs.readFileSync(path.join(dir, rel)))
        .digest("hex").slice(0, 8);
    } catch (e) { out = ""; }   /* named: esbuild rejects a bare catch here */
    cache.set(rel, out);
    return out;
  };
}
