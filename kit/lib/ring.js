// Which entry of archives.json is the archive being built?
//
// It used to be answered by `base` alone: the entry whose base equals
// BASE_URL with its trailing slash stripped. That was unambiguous while every
// archive was a GitHub Pages project site (/TheMazza, /TheDArcy, ...). Each
// archive that moves to its own domain gets base "" — the defranceski, darcy,
// falco, lerena and blazevic moves all did — so after the second move "the one
// whose base is ''" is several archives and find() quietly returned the first
// (the Defranceschi one): every page of the others took its name, its
// theme colour and, worst, a CANONICAL pointing at archive.defranceski.com.
// SiblingArchives had the opposite fault, filtering out every archive whose
// base matched, which dropped all of the base-"" archives from every list.
//
// The origin settles it. astro.config.mjs carries `site`, which Astro exposes as
// import.meta.env.SITE, and archives.json carries each archive's url; they are
// the same origin for the archive being built. With no usable SITE the answer
// is what it always was — the first entry on that base — so nothing that worked
// before changes.
import ring from "../data/archives.json";

const originOf = (u) => { try { return new URL(u).origin; } catch { return ""; } };

export function whoami(base) {
  const site = originOf(import.meta.env.SITE || "");
  const onBase = ring.archives.filter((a) => a.base === base);
  return (site && onBase.find((a) => originOf(a.url) === site)) || onBase[0];
}
