/* The address that opens one archive on the Tree Canvas (Record Atlas), and optionally one person in it.

   The canvas reads `?archive=<key>` (the same keys as kit/data/archives.json) and `?p=<slug>`: it draws the archive,
   puts that person on the canvas and selects them. It accepts only a plain slug for `p` (lower-case letters, digits and
   hyphens, 1 to 120 long) and ignores anything else, so this refuses the same things and says nothing is better than
   a link that opens the wrong thing: an unknown archive key returns null, and a slug the canvas would drop is left off
   (the link still opens the archive).

   Pure, so the kit's own test can run it without a build (kit/tools/canvaslink_logic.mjs). */
export const CANVAS = "https://recordatlas.org/tree-canvas/";
export const SLUG = /^[a-z0-9-]{1,120}$/;

export function canvasHref(archive, slug, keys) {
  if (typeof archive !== "string" || !archive) return null;
  if (Array.isArray(keys) && !keys.includes(archive)) return null;
  if (!/^[a-z]{2,20}$/.test(archive)) return null;
  const q = new URLSearchParams({ archive });
  if (typeof slug === "string" && SLUG.test(slug)) q.set("p", slug);
  return `${CANVAS}?${q.toString()}`;
}

/* The one sentence ahnen.js writes on a branch it cut for depth ("The chart stops here to stay readable.") is about a drawing.
   On a page that does not draw the chart (AncChart draw={false}) there is no chart to stop, and the sentence would say
   something false; say what is true of the page instead. Any other note is returned unchanged, and so is every note
   when the chart is drawn. */
export const CUT_FOR_DEPTH = "The chart stops here to stay readable.";
export const CUT_FOR_DEPTH_NO_CHART = "This page follows the line no further here.";
export function wallNote(note, draw = true) {
  if (draw || typeof note !== "string") return note;
  return note.startsWith(CUT_FOR_DEPTH) ? CUT_FOR_DEPTH_NO_CHART + note.slice(CUT_FOR_DEPTH.length) : note;
}
