// What the foot-of-page row is made of, kept out of the component so it can be tested without rendering Astro.
//
// `ring` is kit/data/archives.json; `mine` is the entry of the archive being built (lib/ring.js whoami(), which
// may be undefined for a site that is not in the file: it then gets every archive). Returns the archives to draw
// as cards, in the file's order and each exactly once, and the links drawn after them as a separate group: the
// children's site, then whatever archives.json lists under `links` (the Record Atlas, the home page).
// Nothing is counted here or in the component: the number of cards is whatever the file holds, less one.
export function ringCards(ring, mine) {
  const others = (ring.archives || []).filter((a) => a !== mine);
  const tail = [
    ring.children && { ...ring.children, why: "the children's site" },
    ...(ring.links || []),
  ].filter(Boolean);
  return { others, tail };
}

// The word on a card: the surname alone (`short`), else the full name.
export const cardLabel = (a) => a.short || a.name;
