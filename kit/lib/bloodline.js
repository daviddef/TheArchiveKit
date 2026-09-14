/* The blood graph, built from whatever shape an archive records kin in.

   Written for Defranceschi and generalised once five other archives turned out
   to hold the same facts under different names: parents/children/siblings as
   arrays of {slug,name,via}, or a `rel` object wrapping them, or father/mother
   as single objects. None of that is worth arguing about, so it is read rather
   than standardised.

   What is NOT negotiable is how a link is allowed to exist. Every edge here
   comes from a record that names a slug. Nothing is matched on a name — this
   estate has 94 Marijas and two consecutive generations both called Ivan
   Defranceski, and matching on names gave one Pietro five mothers before a
   count of parents-per-person caught it. */

const RANK = { read: 3, register: 3, line: 3, index: 2, tree: 1 };

function pick(rec, names) {
  for (const n of names) if (rec && rec[n] != null) return rec[n];
  return null;
}
function many(v) {
  if (!v) return [];
  return Array.isArray(v) ? v : [v];
}

/* records: { slug: personRecord }  or  [personRecord] with a slug field */
export function graph(records, opts = {}) {
  const O = {
    parents: ["parents"], children: ["children"], siblings: ["siblings"],
    spouses: ["spouses", "spouse"], father: ["father"], mother: ["mother"],
    rel: ["rel"], name: ["name"], dates: ["dt", "dates", "life"],
    ...opts,
  };
  const rows = Array.isArray(records)
    ? records.filter((r) => r && r.slug)
    : Object.entries(records).map(([slug, r]) => ({ slug, ...r }));

  const people = {};
  const put = (slug, name) => (people[slug] ||= {
    slug, name: name || slug, dt: "",
    parents: [], children: [], siblings: [], spouse: null,
  });

  const kin = (r, kind) => {
    const src = pick(r, O.rel) || r;
    let out = many(pick(src, O[kind]));
    if (kind === "parents") {
      out = out.concat(many(pick(src, O.father)), many(pick(src, O.mother)));
    }
    return out.filter((x) => x && x.slug);
  };

  for (const r of rows) {
    const me = put(r.slug, pick(r, O.name));
    const d = pick(r, O.dates);
    if (typeof d === "string") me.dt = d;
    const sp = many(pick(pick(r, O.rel) || r, O.spouses))[0];
    if (sp) me.spouse = typeof sp === "string" ? sp : sp.name;

    for (const p of kin(r, "parents")) {
      if (p.slug === r.slug) continue;
      const via = p.via || "tree";
      if (!me.parents.some((x) => x.slug === p.slug))
        me.parents.push({ slug: p.slug, name: p.name, dt: p.dates || "", via });
      const up = put(p.slug, p.name);
      if (!up.children.some((c) => c.slug === r.slug))
        up.children.push({ slug: r.slug, name: me.name, dt: me.dt, via });
    }
    for (const c of kin(r, "children")) {
      if (c.slug === r.slug) continue;
      const via = c.via || "tree";
      if (!me.children.some((x) => x.slug === c.slug))
        me.children.push({ slug: c.slug, name: c.name, dt: c.dates || "", via });
      const kid = put(c.slug, c.name);
      if (!kid.parents.some((x) => x.slug === r.slug))
        kid.parents.push({ slug: r.slug, name: me.name, dt: me.dt, via });
    }
    for (const s of kin(r, "siblings")) {
      if (s.slug === r.slug) continue;
      if (!me.siblings.some((x) => x.slug === s.slug))
        me.siblings.push({ slug: s.slug, name: s.name, dt: s.dates || "", via: s.via || "tree" });
    }
  }

  /* siblings are symmetric even where only one side records it */
  for (const [slug, me] of Object.entries(people))
    for (const s of me.siblings) {
      const o = people[s.slug];
      if (o && !o.siblings.some((x) => x.slug === slug))
        o.siblings.push({ slug, name: me.name, dt: me.dt, via: s.via });
    }

  /* A person recorded as somebody's parent in one place and their brother in
     another cannot be drawn as both. The parent link is directional and comes
     out of a record somebody argued over, so it wins. */
  for (const me of Object.values(people)) {
    const direct = new Set([...me.parents, ...me.children].map((k) => k.slug));
    me.siblings = me.siblings.filter((s) => !direct.has(s.slug));
  }
  for (const [slug, me] of Object.entries(people)) {
    me.parents = me.parents.filter((k) => k.slug !== slug);
    me.children = me.children.filter((k) => k.slug !== slug);
    me.siblings = me.siblings.filter((k) => k.slug !== slug);
  }
  return people;
}

export function components(people) {
  const seen = new Set(), out = [];
  for (const slug of Object.keys(people)) {
    if (seen.has(slug)) continue;
    const stack = [slug], comp = [];
    while (stack.length) {
      const x = stack.pop();
      if (seen.has(x) || !people[x]) continue;
      seen.add(x); comp.push(x);
      for (const k of [...people[x].parents, ...people[x].children, ...people[x].siblings])
        if (k.slug && !seen.has(k.slug)) stack.push(k.slug);
    }
    out.push(comp);
  }
  return out.sort((a, b) => b.length - a.length);
}

export const weakest = (a, b) => ((RANK[a] ?? 1) <= (RANK[b] ?? 1) ? a : b);


/* ---- two other shapes an archive may already hold ------------------------

   Neither needs a session to convert anything, and neither guesses.

   An AHNENTAFEL is the strongest source there is: person n's father is 2n and
   their mother 2n+1, so the parent links are arithmetic rather than matching.
   D'Arcy carries 243 ancestors numbered this way.

   A NESTED PEDIGREE carries the relationship in its structure — each node has
   an f and an m — so the links are the shape of the tree. Booyzen's runs from
   one woman back through both her parents' lines. Nodes are keyed by their
   path through the tree, because a pedigree asserts positions rather than
   identities: the same man appearing twice in two places is a claim about the
   tree, not something to merge on a name. */

export function fromAhnentafel(rows, opts = {}) {
  const key = opts.key || ((r) => String(r.id || r.ahn));
  const byAhn = new Map();
  for (const r of rows) if (r && r.ahn) byAhn.set(Number(r.ahn), r);
  const out = [];
  for (const [n, r] of byAhn) {
    const parents = [];
    for (const p of [2 * n, 2 * n + 1]) {
      const up = byAhn.get(p);
      if (up) parents.push({ slug: key(up), name: up.name, via: opts.via || "line" });
    }
    out.push({ slug: key(r), name: r.name, dt: r.life || "", parents,
               spouses: (r.spouses || []).map((x) => (typeof x === "string" ? { name: x } : x)) });

    /* An ahnentafel is ancestors only, so a chart built from one has no aunts
       or uncles in it at all — every person on it is somebody's direct
       forebear. Where the archive also records who a person's brothers and
       sisters were, they come in here as children of the same parents.
       
       They arrive as names without ids, so each gets a key built from its
       own position — the ancestor it sits beside, and the name. Nothing is
       matched: two sisters called Mary in different families stay two people,
       and the same woman recorded under two ancestors stays two nodes rather
       than being merged on a name she happens to share. */
    for (const sib of r.siblings || r.sib || []) {
      const nm = typeof sib === "string" ? sib : sib && (sib.name || sib.n);
      if (!nm) continue;
      out.push({ slug: "sib:" + n + ":" + nm.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
                 name: nm, dt: "", parents: parents.slice(),
                 via: opts.via || "line" });
    }
  }
  return out;
}

export function fromPedigree(root, opts = {}) {
  const out = [];
  const walk = (node, path) => {
    if (!node || !node.n) return null;
    /* Brothers and sisters hang off the same parents. A pedigree records them
       as names, so each is keyed by the node it stands beside — two sisters
       called Mary under different parents stay two people. */
    const slug = opts.prefix ? opts.prefix + path : "ped" + path;
    const rec = { slug, name: node.n, dt: [node.b, node.d].filter(Boolean).join(" – "),
                  parents: [], children: [], siblings: [] };
    out.push(rec);
    for (const sib of node.sib || []) {
      const nm = sib && (sib.n || sib.name);
      if (!nm) continue;
      out.push({ slug: slug + ":sib:" + nm.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
                 name: nm, dt: [sib.b, sib.d].filter(Boolean).join(" – "),
                 _sibOf: slug, _via: sib.via === "doc" ? "read" : (sib.via || "tree") });
    }
    for (const [side, k] of [["f", "-f"], ["m", "-m"]]) {
      const up = walk(node[side], path + k);
      if (up) {
        rec.parents.push({ slug: up.slug, name: up.name, via: node.s === "doc" ? "read" : "tree" });
        up.children.push({ slug, name: rec.name, via: node.s === "doc" ? "read" : "tree" });
      }
    }
    return rec;
  };
  walk(root, "");
  /* a sibling shares whatever parents the person it stands beside has */
  const byslug = Object.fromEntries(out.map((r) => [r.slug, r]));
  for (const r of out) {
    if (!r._sibOf) continue;
    const base = byslug[r._sibOf];
    if (!base) continue;
    r.parents = (base.parents || []).map((p) => ({ ...p, via: r._via }));
    for (const p of r.parents) {
      const up = byslug[p.slug];
      if (up && !up.children.some((c) => c.slug === r.slug))
        up.children.push({ slug: r.slug, name: r.name, via: r._via });
    }
  }
  return out;
}
