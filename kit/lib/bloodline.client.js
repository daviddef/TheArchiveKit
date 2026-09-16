/* THE CHART. Inlined by Bloodline.astro rather than served from public/, so
   that every archive gets the same drawing without seven copies of this file
   drifting apart — which is exactly what happened to BranchRivers.

   Everyone one person is related to — not a card of their immediate family.
   Parents, children, brothers and sisters, and through them aunts, uncles,
   cousins and their children, as far as the archive's links reach.

   Generations are COLUMNS and people stack down them. They used to be rows,
   which reads beautifully for a small family and falls apart for a real one:
   one Zubrinic has 217 blood relatives, 105 of them in a single generation, and
   that row was 25,008px wide against 616px tall — a 41:1 ribbon nobody could
   follow, with every parent-child line flattened into a horizontal dash running
   the width of it.

   Turned on its side the width stops growing with the family: it is set by the
   NUMBER of generations, which is small, while the count of people in any one
   of them costs height, and height is what a page has to spare. The same chart
   is now about 2,200px wide. Lines became short local hops between neighbouring
   columns instead.

   Every line is still drawn in the colour of the record behind it. */
(function () {
  var P = window.__BLOOD || {}, START = window.__START;
  var svg = document.getElementById("bl-svg");
  var input = document.getElementById("who");
  var none = document.getElementById("bl-none");
  var stage = document.getElementById("bl-stage");
  var summary = document.getElementById("bl-summary");
  if (!svg || !P[START]) return;

  var NS = "http://www.w3.org/2000/svg";
  var BOX = 150, BH = 42, GAPX = 14, LANE = 96, PAD = 20;
  var COLGAP = 74, ROWH = BH + 12, HEADH = 30;
  var STROKE = { read: ["var(--accent-2,#5c8a5c)", "0"], line: ["var(--accent-2,#5c8a5c)", "0"],
                 index: ["var(--accent)", "0"], tree: ["var(--ochre,#8a7f5c)", "6 4"] };

  function fold(x) {
    return String(x == null ? "" : x).normalize("NFD")
      .replace(/[̀-ͯ]/g, "").toLowerCase();
  }
  function squash(x) { return fold(x).replace(/[^a-z0-9]+/g, ""); }
  var ALL = Object.keys(P).map(function (s) {
    return { slug: s, name: P[s].name, f: fold(P[s].name), q: squash(P[s].name),
             deg: P[s].parents.length + P[s].children.length + P[s].siblings.length };
  }).sort(function (a, b) { return a.name.localeCompare(b.name); });

  function search(v) {
    var f = fold(v.trim()), q = squash(v);
    if (!f) return [];
    return ALL.filter(function (p) { return p.f.indexOf(f) > -1 || (q && p.q.indexOf(q) > -1); })
      .sort(function (a, b) {
        var as = a.f.indexOf(f) === 0 ? 0 : 1, bs = b.f.indexOf(f) === 0 ? 0 : 1;
        return as - bs || b.deg - a.deg || a.name.localeCompare(b.name);
      });
  }

  /* An edge is only followed when the person at the other end is actually IN
     the graph. A record can name somebody the graph does not carry — the page
     hands over only people who have an edge of their own, and an archive whose
     data is not symmetric (A names B as a child, B names nobody) leaves an edge
     pointing at a node that was never drawn. Walking into one of those read
     .parents off undefined and killed the whole chart rather than dropping one
     line from it. */
  var link = function (s, k) {
    var p = P[s];
    return ((p && p[k]) || []).filter(function (c) { return c.slug && P[c.slug]; });
  };
  var kids = function (s) { return link(s, "children"); };
  var pars = function (s) { return link(s, "parents"); };
  var sibs = function (s) { return link(s, "siblings"); };

  /* everyone reachable by blood, with their generation relative to the root */
  function household(root) {
    var gen = {}, order = [];
    gen[root] = 0;
    var q = [root];
    while (q.length) {
      var x = q.shift();
      order.push(x);
      pars(x).forEach(function (p) { if (!(p.slug in gen)) { gen[p.slug] = gen[x] - 1; q.push(p.slug); } });
      kids(x).forEach(function (c) { if (!(c.slug in gen)) { gen[c.slug] = gen[x] + 1; q.push(c.slug); } });
      sibs(x).forEach(function (s) { if (!(s.slug in gen)) { gen[s.slug] = gen[x]; q.push(s.slug); } });
    }
    return { gen: gen, order: order };
  }

  /* how the archive would describe this person to the one in the middle */
  function ancestors(s) {
    var d = {}, q = [[s, 0]];
    while (q.length) {
      var it = q.shift(), x = it[0], n = it[1];
      if (x in d && d[x] <= n) continue;
      d[x] = n;
      if (n > 8) continue;
      pars(x).forEach(function (p) { q.push([p.slug, n + 1]); });
    }
    return d;
  }
  /* How many "greats" go in front. A grandparent has none, a great-grandparent
     one, and past two it is counted rather than repeated — "5× great-" reads
     where "great-great-great-great-great-" does not. The first version of this
     put the prefix in front of a word that already contained one and produced
     "3× great-great-aunt". */
  function greats(k) {
    return k <= 0 ? "" : k === 1 ? "great-" : k === 2 ? "great-great-" : k + "× great-";
  }

  function kin(root, x) {
    if (x === root) return "this person";
    var A = ancestors(root), B = ancestors(x), best = null;
    for (var k in B) if (k in A) {
      var tot = A[k] + B[k];
      if (!best || tot < best.t) best = { t: tot, a: A[k], b: B[k] };
    }
    /* a sibling link with no shared parent recorded still means a sibling */
    if (!best) {
      if (sibs(root).some(function (s) { return s.slug === x; })) return "brother or sister";
      /* No blood path — but they are usually on the chart because they married
         somebody who has one, and their children carry it. "Related" was true
         of them and told a reader nothing; a brother's wife should read as a
         brother's wife. Checked through the spouse's own ancestors, so it is
         the same test as every other line on this page. */
      var ms = P[x].mates || [];
      for (var mi = 0; mi < ms.length; mi++) {
        var sp = ms[mi];
        if (!P[sp]) continue;
        if (sp === root || sibs(root).some(function (s) { return s.slug === sp; }))
          return "married into the family";
        var S = ancestors(sp);
        for (var k3 in S) if (k3 in A) return "married into the family";
      }
      return "related";
    }
    var up = best.a, down = best.b;        // up: root→ancestor, down: x→ancestor
    if (down === 0) return up === 1 ? "parent"
      : up === 2 ? "grandparent" : greats(up - 2) + "grandparent";
    if (up === 0) return down === 1 ? "child"
      : down === 2 ? "grandchild" : greats(down - 2) + "grandchild";
    if (up === 1 && down === 1) return "brother or sister";
    if (down === 1) return greats(up - 2) + "aunt or uncle";
    if (up === 1) return greats(down - 2) + "niece or nephew";
    var deg = Math.min(up, down) - 1, rem = Math.abs(up - down);
    var name = deg === 1 ? "first cousin" : deg === 2 ? "second cousin"
      : deg === 3 ? "third cousin" : deg + "th cousin";
    return rem ? name + (rem === 1 ? ", once removed" : rem === 2 ? ", twice removed"
      : ", " + rem + "× removed") : name;
  }

  /* The direct line through whoever is selected: up the paternal chain, and
     down through their own descendants. Everyone else in the chart is kin, but
     this is the thread the archive is built along and it should be the thing
     the eye lands on.

     Going up, a person can have two parents and the paternal one is not
     recorded as such anywhere here. The surname is: preferring the parent who
     carries the same one picks the father's side wherever the names survive,
     and falls back to the first recorded parent where they do not, which is
     what the spine gives anyway since each of its generations has exactly one
     parent. */
  function surnameOf(slug) {
    var parts = String(P[slug].name || "").trim().split(/\s+/);
    return parts.length > 1 ? fold(parts[parts.length - 1]) : "";
  }
  function lineage(root) {
    var set = {}, x = root;
    set[root] = true;
    for (var i = 0; i < 40; i++) {                 // up
      var ps = pars(x);
      if (!ps.length) break;
      var mine = surnameOf(x);
      var pick = ps.find(function (p) { return P[p.slug] && surnameOf(p.slug) === mine && mine; })
                 || ps[0];
      if (!pick || set[pick.slug]) break;
      set[pick.slug] = true; x = pick.slug;
    }
    /* Down, follow the line rather than the whole cone of descendants. The
       archive already marks which child carried the line onward, so on the
       spine it is that child and then theirs. Highlighting every descendant
       lit up Josip's daughters as well, and they are his children but they are
       not his line — which is the distinction this page exists to draw. */
    var y = root;
    for (var j = 0; j < 40; j++) {
      var cs = kids(y);
      if (!cs.length) break;
      var next = null;
      if (P[y].spine != null) {
        next = cs.find(function (c) { return P[c.slug] && P[c.slug].spine === P[y].spine + 1; });
      }
      if (!next) next = cs.length === 1 ? cs[0] : null;   // no line marked: only follow an only child
      if (!next || set[next.slug]) break;
      set[next.slug] = true; y = next.slug;
    }
    return set;
  }

  function draw(root) {
    var me = P[root];
    if (!me) return;
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    var h = household(root), gen = h.gen;

    /* Both halves of a couple can be blood relatives of the person in the
       middle — every married pair of ancestors is — and where they were, this
       chart used to draw each of them TWICE: once in their own right, and
       again as the other one's "married in" chip beside them. Nuno Fernando
       Lerena's 13 relatives came out in 22 boxes, holding two Juan Carloses,
       two Marias and two Mary Septimas, which reads as a fault in the archive
       rather than in the drawing.

       So a husband or wife gets a chip only when they are not already on the
       chart. The test is the SLUG, never the name — two women called Maria
       Lerena in one family would be two people, and this file does not merge
       on names. An archive that records a spouse as a bare name still gets
       the chip it always got. */
    var chip = function (s) {
      var p = P[s];
      return !!(p && p.spouse && !(p.spouseSlug && p.spouseSlug in gen));
    };
    var LIN = lineage(root);
    var byGen = {};
    Object.keys(gen).forEach(function (s) { (byGen[gen[s]] = byGen[gen[s]] || []).push(s); });
    var gens = Object.keys(byGen).map(Number).sort(function (a, b) { return a - b; });

    /* Where both halves of a couple are on the chart, seat them together, so
       the tie between them is a short hop rather than a rule down the column.
       One pass, taking each person and then their partner, so the sort above
       still decides the order of the couples themselves. */
    function seat(list) {
      var out = [], taken = {};
      for (var i = 0; i < list.length; i++) {
        var a = list[i];
        if (taken[a]) continue;
        out.push(a); taken[a] = 1;
        (P[a].mates || []).forEach(function (sp) {
          if (!taken[sp] && list.indexOf(sp) > -1) { out.push(sp); taken[sp] = 1; }
        });
      }
      return out;
    }

    /* order each generation so that children sit near their parents */
    var pos = {};
    gens.forEach(function (gi, row) {
      var list = byGen[gi];
      if (row > 0) {
        list.sort(function (a, b) {
          var pa = pars(a).map(function (p) { return pos[p.slug]; }).filter(function (v) { return v != null; });
          var pb = pars(b).map(function (p) { return pos[p.slug]; }).filter(function (v) { return v != null; });
          var ma = pa.length ? pa.reduce(function (s, v) { return s + v; }, 0) / pa.length : 1e9;
          var mb = pb.length ? pb.reduce(function (s, v) { return s + v; }, 0) / pb.length : 1e9;
          return ma - mb || P[a].name.localeCompare(P[b].name);
        });
      } else {
        list.sort(function (a, b) { return P[a].name.localeCompare(P[b].name); });
      }
      list = byGen[gi] = seat(list);
      list.forEach(function (s, i) { pos[s] = i; });
    });

    /* A column only needs room for a husband or wife if somebody in it has a
       chip — measured rather than assumed, and measured on the same test that
       decides whether the chip is drawn at all. */
    var colW = function (gi) {
      return BOX + (byGen[gi].some(chip) ? GAPX + BOX : 0);
    };
    var colX = {}, cx = PAD;
    gens.forEach(function (gi) { colX[gi] = cx; cx += colW(gi) + COLGAP; });
    var tallest = Math.max.apply(null, gens.map(function (gi) { return byGen[gi].length; }));
    var W = Math.max(640, cx - COLGAP + PAD);
    var H = PAD * 2 + HEADH + tallest * ROWH;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("width", W);
    svg.setAttribute("height", H);
    /* THE ATTRIBUTES ARE THE FALLBACK; THE STYLES ARE THE BEHAVIOUR. An explicit
       pixel width beside a viewBox pins the drawing at its natural size, so a
       1,354px chart in a 1,022px box could only be dragged sideways - and the
       stage is overflow:auto, so that was a choice and not an accident. It is
       the wrong choice at that ratio: 1,354 into 1,022 is 75%, which still
       leaves a 113px name box and legible text, and no scrollbar.

       So it fills the box and scales down, with a floor. Below 70% the text
       stops being readable and dragging a full-size drawing beats squinting at
       a small one, so under that the stage scrolls as it always did. A phone is
       always under it. */
    svg.style.width = "100%";
    svg.style.height = "auto";
    svg.style.maxWidth = W + "px";
    svg.style.minWidth = Math.round(W * 0.7) + "px";

    /* short columns are centred against the tallest, so a family of four beside
       a family of a hundred sits opposite them rather than at the ceiling */
    var xy = {};
    gens.forEach(function (gi) {
      var list = byGen[gi];
      var top = PAD + HEADH + (tallest - list.length) * ROWH / 2;
      list.forEach(function (s, i) { xy[s] = { x: colX[gi], y: top + i * ROWH }; });
    });

    /* Say what each column is. A column holds everyone at that remove — aunts
       and cousins as well as ancestors — so it is named for the generation
       rather than for a relationship. */
    function genLabel(g) {
      var back = ["this generation", "parents' generation", "grandparents' generation",
                  "great-grandparents' generation"];
      var on = ["this generation", "children's generation", "grandchildren's generation",
                "great-grandchildren's generation"];
      var k = Math.abs(g);
      if (k < 4) return (g <= 0 ? back : on)[k];
      return k + " generations " + (g < 0 ? "back" : "on");
    }
    gens.forEach(function (gi) {
      svg.appendChild(el("text", { x: colX[gi], y: PAD + 14, class: "bl-lane" }, genLabel(gi)));
    });

    function edge(a, b, via) {
      var A = xy[a], B = xy[b];
      if (!A || !B) return;
      var s = STROKE[via] || STROKE.tree;
      var onLine = LIN[a] && LIN[b];
      /* an edge into a person with more than two claimed parents is one of
         several competing claims, and is drawn as a claim rather than a fact */
      var toContested = (P[b].parents || []).filter(function (p) { return p.slug; }).length > 2;
      /* the line leaves the COUPLE, not the blood parent, so it never crosses
         the husband or wife sitting beside them */
      var ax = A.x + (chip(a) ? BOX + GAPX + BOX : BOX), ay = A.y + BH / 2;
      var bx = B.x, by = B.y + BH / 2;
      var bend = Math.max(22, (bx - ax) * 0.45);
      svg.appendChild(el("path", {
        d: "M" + ax + "," + ay + " C" + (ax + bend) + "," + ay +
           " " + (bx - bend) + "," + by + " " + bx + "," + by,
        stroke: s[0], "stroke-width": onLine ? 3.4 : 1.6,
        "stroke-dasharray": s[1], fill: "none",
        "stroke-opacity": toContested ? ".38" : (onLine ? 1 : ".45"),
        class: onLine ? "bl-edge is-line" : "bl-edge"
      }));
    }
    function el(n, a, t) {
      var e = document.createElementNS(NS, n);
      for (var k in a) e.setAttribute(k, a[k]);
      if (t != null) e.appendChild(document.createTextNode(t));
      return e;
    }
    function clip(s, n) { return s && s.length > n ? s.slice(0, n - 1) + "…" : (s || ""); }

    Object.keys(gen).forEach(function (s) {
      kids(s).forEach(function (c) { if (c.slug in gen) edge(s, c.slug, c.via); });
    });

    /* A marriage between two people the chart already holds — drawn once, in
       the same dashed grey as a chip, down the left of the column where the
       parent-and-child lines are not. */
    var tied = {};
    Object.keys(gen).forEach(function (a) {
      (P[a].mates || []).forEach(function (b) {
        if (!(b in gen) || !xy[a] || !xy[b]) return;
        var k = a < b ? a + "|" + b : b + "|" + a;
        if (tied[k]) return;
        tied[k] = 1;
        var A = xy[a], B = xy[b], ay = A.y + BH / 2, by = B.y + BH / 2, d;
        if (A.x === B.x) {
          /* the ordinary case — a couple seated together, so the tie is a
             bracket down the gutter to the left of their column, where the
             parent-and-child lines never go */
          var lx = A.x - 9;
          d = "M" + A.x + "," + ay + " H" + lx + " V" + by + " H" + B.x;
        } else {
          /* Married across generations. Roseline Forbes married Frederick
             Chappell and then Roque Lerena, and her daughter by the first
             married Roque's brother — so Doreen Chappell stands a column to
             the right of the husband she is tied to. A bracket down the far
             gutter would be ruled straight through whatever sits between
             them, so this takes the route every other cross-column line on
             the chart takes: out of the right of one and into the left of the
             other. */
          var L = A.x < B.x ? a : b, R = A.x < B.x ? b : a;
          var lxy = xy[L], rxy = xy[R];
          var sx = lxy.x + (chip(L) ? BOX + GAPX + BOX : BOX), sy = lxy.y + BH / 2;
          var ex = rxy.x, ey = rxy.y + BH / 2, bend = Math.max(22, (ex - sx) * 0.45);
          d = "M" + sx + "," + sy + " C" + (sx + bend) + "," + sy + " " +
              (ex - bend) + "," + ey + " " + ex + "," + ey;
        }
        svg.appendChild(el("path", {
          d: d, stroke: "var(--ink-3)", "stroke-width": 1.5, "stroke-dasharray": "5 4",
          fill: "none", class: "bl-tie"
        }));
      });
    });

    Object.keys(gen).forEach(function (s) {
      var p = xy[s], isMe = s === root;
      var g = el("g", { class: "bl-node" + (isMe ? " is-self" : "")
                        + (LIN[s] && !isMe ? " is-line" : "")
                        + (!LIN[s] ? " is-kin" : "") });
      if (!isMe) {
        g.setAttribute("tabindex", "0");
        g.setAttribute("role", "button");
        g.addEventListener("click", function () { go(s); });
        g.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(s); } });
      }
      g.appendChild(el("rect", { x: p.x, y: p.y, width: BOX, height: BH, rx: 5 }));
      g.appendChild(el("text", { x: p.x + 10, y: p.y + 17 }, clip(P[s].name, 22)));
      g.appendChild(el("text", { x: p.x + 10, y: p.y + 31, class: "bl-dt" },
        clip(P[s].dt || kin(root, s), 26)));
      g.appendChild(el("title", {}, P[s].name + (P[s].dt ? ", " + P[s].dt : "") + " — " + kin(root, s)));
      svg.appendChild(g);

      /* The wife or husband, beside them, joined by a marriage line. Drawn
         differently on purpose: they are not blood, and this page is about
         blood — but leaving them out makes a family look like a list of
         single men. */
      if (chip(s)) {
        var sx = p.x + BOX + GAPX;
        svg.appendChild(el("path", {
          d: "M" + (p.x + BOX) + "," + (p.y + BH / 2) + " L" + sx + "," + (p.y + BH / 2),
          stroke: "var(--ink-3)", "stroke-width": 1.5, "stroke-dasharray": "5 4", fill: "none"
        }));
        var sg = el("g", { class: "bl-node is-spouse" });
        sg.appendChild(el("rect", { x: sx, y: p.y, width: BOX, height: BH, rx: 5 }));
        sg.appendChild(el("text", { x: sx + 10, y: p.y + 17 }, clip(P[s].spouse, 22)));
        sg.appendChild(el("text", { x: sx + 10, y: p.y + 31, class: "bl-dt" },
          clip(P[s].spouseDt ? "b. " + P[s].spouseDt : "married in", 26)));
        sg.appendChild(el("title", {}, P[s].spouse + " — married " + P[s].name));
        svg.appendChild(sg);
      }
    });

    /* Nobody has five parents. Where an archive records more than two it is
       holding competing claims from different sources — Falco has a register
       couple, a tree couple and a line assertion for one man — and drawing all
       five as equally true is the one thing these archives do not do. Say so
       instead of quietly picking. */
    var ps = me.parents.filter(function (p) { return p.slug; });
    var srcs = {};
    ps.forEach(function (p) { srcs[p.via] = (srcs[p.via] || 0) + 1; });
    var contested = ps.length > 2 ? Object.keys(srcs).length : 0;

    var n = Object.keys(gen).length;
    summary.textContent = n === 1
      ? "No relative of " + me.name + " is recorded here yet."
      : n + " people, across " + gens.length + " generations — everyone this archive can join to "
        + me.name + " by blood, and the husbands and wives who stand beside them."
        + (contested
            ? "  The records disagree about this person's parents: "
              + ps.length + " are claimed, from " + contested + " different kinds of source."
            : "");
    var box = xy[root];
    if (box) {
      stage.scrollLeft = Math.max(0, box.x + BOX / 2 - stage.clientWidth / 2);
      stage.scrollTop = Math.max(0, box.y + BH / 2 - stage.clientHeight / 2);
    }
  }

  function go(slug) {
    if (!P[slug]) return;
    draw(slug);
    input.value = P[slug].name;
    history.replaceState(null, "", "?p=" + encodeURIComponent(slug));
  }

  var results = document.createElement("div");
  results.className = "bl-hits";
  input.parentNode.insertBefore(results, none);

  function render(v) {
    var hits = search(v);
    results.textContent = "";
    none.hidden = !v.trim() || hits.length > 0;
    if (!v.trim()) return;
    hits.slice(0, 10).forEach(function (h) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "bl-hit";
      var nm = document.createElement("span"); nm.className = "bl-hit-n"; nm.textContent = h.name;
      var d = document.createElement("span"); d.className = "bl-hit-d";
      d.textContent = h.deg ? h.deg + (h.deg === 1 ? " relative" : " relatives") : "no relatives yet";
      b.appendChild(nm); b.appendChild(d);
      b.addEventListener("click", function () { go(h.slug); results.textContent = ""; });
      results.appendChild(b);
    });
    if (hits.length > 10) {
      var more = document.createElement("div");
      more.className = "bl-more";
      more.textContent = hits.length - 10 + " more — keep typing";
      results.appendChild(more);
    }
  }

  /* The box carries the name of whoever is on screen, so the next thing a
     reader wants to do is replace it, not append to it. Select it on focus and
     one keystroke starts a new search instead of a dozen backspaces. iOS puts
     the caret where it was tapped after the focus event, so it has to be done
     again on the next frame, and the click guard keeps a deliberate
     cursor-placement from being stolen back. */
  function selectAll() { try { input.select(); } catch (e) {} }
  input.addEventListener("focus", function () { selectAll(); setTimeout(selectAll, 0); });
  input.addEventListener("click", function () {
    if (input.selectionStart === input.selectionEnd) selectAll();
  });

  var t;
  input.addEventListener("input", function () {
    clearTimeout(t); var v = input.value;
    t = setTimeout(function () { render(v); }, 120);
  });
  input.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    var hits = search(input.value);
    if (hits.length) { go(hits[0].slug); results.textContent = ""; }
  });

  var q = new URLSearchParams(location.search).get("p");
  go(P[q] ? q : START);
})();
