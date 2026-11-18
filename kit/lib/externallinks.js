/* Which links open in a new tab: the ones that leave this site.
 *
 * David: links to FamilySearch, other sites and references opened in the same tab, so the reader lost their place. A link to another host now
 * opens in a new tab (with rel="noopener"); a link within the same host (people, places, pages, the archive's own menus) is left alone, so back and
 * forward still work. A link that already says where it opens (target), a download, a mailto:/tel:/javascript: link, and a link with no
 * address are never touched.
 *
 * This is one function with no outside names, because components/ExternalLinks.astro writes its source into the page (Function.toString()):
 * the code that ships is the code kit/tools/externallinks_logic.mjs tests. */
export function opensElsewhere(href, here, target, download) {
  if (!href || download) return false;
  if (target && target !== "_self") return false;
  var u, h;
  try { u = new URL(href, here); h = new URL(here); } catch (e) { return false; }
  if (u.protocol !== "http:" && u.protocol !== "https:") return false;
  return u.host !== h.host;
}
