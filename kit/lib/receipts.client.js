/* THE VIEW-TIME REFRESH of the Atlas lines on /whats-new/ (inlined by WhatsNew.astro, like bloodline.client.js, so there is one copy).
   The page is built with the Atlas states as they were at build time ("as of <date>"). When it is opened, this asks the Atlas's DEPLOYED receipts again
   (the one address in data-live, on recordatlas.org) and works out each row's state with the SAME logic as lib/receipts.js stateOf(key, live, null)
   (a copy, because this runs in the reader's browser; kit/tools/receipts_logic.mjs holds the two to identical answers). It can say two things only:
   "in the Atlas" (the key is in the deployed file with marks) and "nothing to send" (the key is there with an empty list), and it only ever paints those.
   A row it cannot place (the key is not in the deployed file) keeps the pill the page was built with: "Sent, going live" and "Not sent yet" cannot be told
   apart from here, so they are never redrawn, never downgraded and never invented. (Until 23 November 2026 it also read a second address, the Atlas's source
   repository, to tell "going live" from "not sent"; that address is gone from the page.) THIS FILE IS INLINED INTO EVERY PAGE AS WRITTEN: no address but
   the Atlas's own may be written in it, not even in a comment (receipts_logic.mjs and checkpages_nogithub.py check the built page).
   It then updates the day tallies and the status line. If anything fails (offline, no CORS header, a file missing, bad JSON) it does nothing: the build-time states stay.
   Plain ES5 on purpose: it is inlined as written. Reads data-* of #wn-asof: data-archive, data-live (the deployed receipts' address), data-asof (the build day, as the page prints it). */
var wnReceipts = (function () {
  var ORIGIN = "https://recordatlas.org";
  var LABEL = { "in-atlas": "In the Atlas", "going-live": "Sent, going live", "not-sent": "Not sent yet", "nothing-to-send": "Nothing to send" };
  var NOTE = {
    "in-atlas": "The Record Atlas has this search, live now",
    "going-live": "Sent to the Record Atlas; it goes live with the Atlas's next deploy (13 to 65 minutes)",
    "not-sent": "Not yet sent to the Record Atlas; sends run every few hours, then 13 to 65 minutes to go live",
    "nothing-to-send": "Checked: this note makes no mark on the Record Atlas (no source or volume to put on it)"
  };
  var GLYPH = { "in-atlas": "✓", "going-live": "↻", "not-sent": "○", "nothing-to-send": "–" };

  function atlasHref(h) {
    if (typeof h !== "string") return "";
    var t = h.replace(/^\s+|\s+$/g, "");
    if (/^\/(?!\/)[^\s]*$/.test(t)) return ORIGIN + t;
    if (t.indexOf(ORIGIN + "/") === 0 && !/\s/.test(t)) return t;
    return "";
  }
  function hasRows(x) { return !!x && typeof x === "object" && !!x.rows && typeof x.rows === "object" && !Array.isArray(x.rows); }
  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function marksOf(list) {
    var out = [];
    if (!Array.isArray(list)) return out;
    for (var i = 0; i < list.length; i++) { var m = list[i]; if (Array.isArray(m) && typeof m[0] === "string" && atlasHref(m[1])) out.push([m[0], atlasHref(m[1])]); }
    return out;
  }
  /* the same as stateOf(key, live, null) in lib/receipts.js: only what the deployed file can say */
  function stateOf(key, live) {
    var L = hasRows(live) ? live.rows : null;
    function done(state, list) { var marks = state === "nothing-to-send" ? [] : marksOf(list); return { state: state, href: marks.length ? marks[0][1] : "", marks: marks }; }
    if (L && has(L, key)) { return marksOf(L[key]).length ? done("in-atlas", L[key]) : done("nothing-to-send"); }
    return null;
  }

  function getJSON(url, ms) {
    return new Promise(function (resolve) {
      try {
        var ctl = typeof AbortController === "function" ? new AbortController() : null;
        var timer = ctl ? setTimeout(function () { ctl.abort(); }, ms) : null;
        fetch(url, ctl ? { signal: ctl.signal, cache: "no-cache" } : { cache: "no-cache" })
          .then(function (r) { if (!r.ok) throw 0; return r.json(); })
          .then(function (j) { if (timer) clearTimeout(timer); resolve(hasRows(j) && (j.v === undefined || j.v === 1) ? j : null); })
          .catch(function () { if (timer) clearTimeout(timer); resolve(null); });
      } catch (e) { resolve(null); }
    });
  }

  function label(markKey) { return String(markKey).replace(/:/, " "); }
  function paint(box, s) {
    /* box = .wn-ax, holding a .wn-at pill, an optional link and an optional list of the other marks; rebuilt from DOM nodes, never from markup strings */
    while (box.firstChild) box.removeChild(box.firstChild);
    var pill = document.createElement("span");
    pill.className = "wn-at " + s.state;
    pill.title = NOTE[s.state];
    var g = document.createElement("i"); g.setAttribute("aria-hidden", "true"); g.textContent = GLYPH[s.state];
    pill.appendChild(g); pill.appendChild(document.createTextNode(" " + LABEL[s.state]));
    box.appendChild(pill);
    if (s.state === "in-atlas" && s.href) {
      var see = document.createElement("a"); see.className = "wn-seeit"; see.href = s.href; see.rel = "noopener";
      see.title = "Opens the Record Atlas page that carries this search; the page, not the volume's own row";
      see.textContent = "see it in the Atlas ↗";
      box.appendChild(see);
      /* the other pages, one link per page (several marks can sit on one page) */
      var seen = {}; seen[s.href] = 1; var others = [];
      for (var i = 1; i < s.marks.length; i++) { if (!seen[s.marks[i][1]]) { seen[s.marks[i][1]] = 1; others.push(s.marks[i]); } }
      if (others.length) {
        var d = document.createElement("details"); d.className = "wn-am";
        var sm = document.createElement("summary"); sm.textContent = "and " + others.length + " more " + (others.length === 1 ? "page" : "pages");
        d.appendChild(sm);
        for (var j = 0; j < others.length; j++) {
          var a = document.createElement("a"); a.href = others[j][1]; a.rel = "noopener"; a.textContent = label(others[j][0]) + " ↗";
          d.appendChild(a);
        }
        box.appendChild(d);
      }
    }
    box.setAttribute("data-state", s.state);
    box.hidden = false;
  }
  function tally(dayEl) {
    var n = { "in-atlas": 0, "going-live": 0, "not-sent": 0 };
    var boxes = dayEl.querySelectorAll(".wn-ax[data-state]");
    for (var i = 0; i < boxes.length; i++) { var st = boxes[i].getAttribute("data-state"); if (n[st] !== undefined) n[st]++; }
    var makes = n["in-atlas"] + n["going-live"] + n["not-sent"];
    var t = dayEl.querySelector(".wn-atl");
    if (t) t.textContent = makes ? " · " + n["in-atlas"] + " of " + makes + " in the Atlas" : "";
  }

  function run() {
    try {
      var bar = document.getElementById("wn-asof");
      if (!bar) return;
      var live = bar.getAttribute("data-live");
      if (!live) return;
      getJSON(live, 8000).then(function (got) {
        try {
          if (!got) return;
          var boxes = document.querySelectorAll(".wn-ax[data-key]");
          for (var i = 0; i < boxes.length; i++) {
            var s = stateOf(boxes[i].getAttribute("data-key"), got);
            if (s) paint(boxes[i], s);
          }
          var days = document.querySelectorAll(".wn-day");
          for (var j = 0; j < days.length; j++) tally(days[j]);
          var txt = bar.querySelector(".wn-asof-t");
          var asof = bar.getAttribute("data-asof");
          if (txt) txt.textContent = "Record Atlas status: what is live in the Atlas, checked just now" + (asof ? "; rows not yet live are as of " + asof + ", when this page was built." : ".");
          bar.hidden = false;
          bar.setAttribute("data-fresh", "1");
        } catch (e) { /* the build-time states stay */ }
      });
    } catch (e) { /* the build-time states stay */ }
  }
  return { stateOf: stateOf, atlasHref: atlasHref, run: run };
})();
if (typeof document !== "undefined") wnReceipts.run();
