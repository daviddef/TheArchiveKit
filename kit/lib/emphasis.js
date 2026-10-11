/* The emphasis scanner, written once and used by md() and inlineRich().

   ⭐ 11 October 2026 — THE ORDERED RULES COULD NOT READ A RUN OF THREE, and the
   two readings a run of three needs are opposite. Both of these are real rows
   in the Booyzen searched register:

     *Agnes Kolbe × Jerg Raisch, 1685, **Evangelisch … Wuerttemberg***
        an italic, with a bold inside it, both closed by the one run
     **54 records, every one either *Ireland … Baptisms* or *Ireland Births***
        a bold, with an italic inside it, both closed by the one run

   The chain read the first correctly and the second as

     <em>Ireland Births 1864-1958</strong></em>

   which is misnested, so the browser closes the <strong> at the <em> and the
   bold bleeds through the rest of the cell. No ordering of *** / ** / * fixes
   it, because the two rows need the asterisks split in opposite directions.

   So the run is scanned rather than matched, with a stack, closing the
   INNERMOST span first. That is the rule every markdown parser uses and it
   reads both rows.

   THREE PROPERTIES OF THE OLD CHAIN ARE KEPT ON PURPOSE.

   A SPAN NEVER CROSSES A NEWLINE. The old rules carried no /s flag and the
   italic rule excluded \n outright, after an archive measured 125 strings
   where a wider match swallowed a paragraph break and joined two unrelated
   spans. The scanner runs per line for the same reason — see this file's
   header, which is the record of that measurement.

   AN UNMATCHED MARKER STAYS VISIBLE. A delimiter that opens nothing, or opens
   a span that the line never closes, is written back out as asterisks rather
   than rendered and silently closed. The header's phrase for this is that an
   unbalanced marker is "a data fault surfacing rather than a renderer hiding
   it", and a stack makes it easy to do the opposite by accident.

   A LONE ASTERISK IS NOT ALWAYS EMPHASIS. `BOOY*` is a NAAIRS wildcard and
   `q.surname=B*rry` is a FamilySearch query; the estate's registers are full
   of them. So a run of ONE opens a span only when the character after it is
   not a space and closes one only when the character before it is not — the
   flanking rule — and a wildcard, having nothing to pair with, is printed as
   itself.

   ⚠ THE FLANKING RULE APPLIES TO A RUN OF ONE AND TO NOTHING ELSE, and the
   first draft of this file applied it to all three lengths. That draft was
   measured against the estate's data and passed, because the measurement
   counted misnestings and asterisks and not the thing it broke. This estate
   writes padded delimiters —

     *** OVERTURNS ROW 167. ***        a Booyzen work-list row

   — and the chain this replaced paired any two runs whatever sat beside them,
   so it rendered those and the draft did not. Caught in the Booyzen repin,
   which compares every built page: the row came out as four literal
   asterisks. Measured properly then: 3,174 strings across eight archives lost
   16,578 emphasis tags, Lerena 2,777 of them, Luwinski 189, Defranceski 88.

   A run of two or three is never a wildcard in this estate's data — every
   wildcard found in it is a single asterisk on the end or inside of a word —
   so lengths of two and three pair the way the old chain paired them, and
   only the lone asterisk has to earn it. */

const WS = (c) => c === undefined || /\s/.test(c);

/* How many open spans a run of n asterisks closes, innermost first — and 0
   unless it closes them EXACTLY, with nothing left over.

   The remainder is what makes this a function rather than a loop. In
   `*“**The decision … 1987**` an italic opens and a bold opens straight after
   it with no space between. Spending one asterisk of that run on closing the
   italic and opening a second italic with the other reads the line as nobody
   wrote it. Requiring the run to be spent in full leaves it to open the bold,
   which the bold's own ** closes later. */
const closes = (stack, n) => {
  let k = 0, rem = n;
  for (let j = stack.length - 1; j >= 0 && rem > 0; j--) {
    const need = stack[j].tag === "strong" ? 2 : 1;
    if (rem < need) break;
    rem -= need;
    k++;
  }
  return rem === 0 ? k : 0;
};

const line = (s) => {
  const out = [];          // strings, and open-tag tokens resolved at the end
  const stack = [];
  for (let i = 0; i < s.length; ) {
    if (s[i] !== "*") { out.push(s[i++]); continue; }
    let n = 1;
    while (s[i + n] === "*") n++;
    let rem = n;
    /* See the header: only a lone asterisk has to flank, because only a lone
       asterisk is ever a wildcard. */
    const lone = n === 1;
    const shut = (lone && WS(s[i - 1])) ? 0 : closes(stack, n);
    if (shut) {
      for (let k = 0; k < shut; k++) {
        const t = stack.pop();
        t.closed = true;
        rem -= t.tag === "strong" ? 2 : 1;
        out.push(`</${t.tag}>`);
      }
    } else if (!lone || !WS(s[i + n])) {
      while (rem >= 2) { const t = { tag: "strong", mark: "**" }; stack.push(t); out.push(t); rem -= 2; }
      if (rem === 1)   { const t = { tag: "em",     mark: "*"  }; stack.push(t); out.push(t); rem -= 1; }
    }
    if (rem) out.push("*".repeat(rem));
    i += n;
  }
  /* Anything still open never found its closer: put the markers back. */
  return out.map((o) => (typeof o === "string" ? o : o.closed ? `<${o.tag}>` : o.mark)).join("");
};

export const emphasis = (s) => String(s ?? "").split("\n").map(line).join("\n");
