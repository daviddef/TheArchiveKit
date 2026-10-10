/* Prove the markup renderer does what its file says, on fixtures.

   md.js had no test of any kind, and it is the one file in this kit that every
   archive's prose passes through. The cases below are not invented: the two
   that matter are real rows from the Booyzen searched register, and they are
   the pair that no ordering of the old *** / ** / * chain could read, because
   they need the same run of three asterisks split in opposite directions.

   The rest pin the three properties the renderer must not lose while fixing
   that — a span never crosses a newline, an unmatched marker stays visible,
   and a lone asterisk is a wildcard rather than emphasis. Each of those was
   paid for by a measurement recorded in md.js or emphasis.js, and a test is
   cheaper than making the measurement twice.

       node kit/tools/md_selftest.mjs
*/

import { md, mdNote, mdp, plain } from "../lib/md.js";

const fails = [];
const expect = (label, got, want) => {
  const ok = got === want;
  if (!ok) fails.push(label);
  console.log(`  ${ok ? "ok  " : "FAIL"}  ${label}`);
  if (!ok) {
    console.log(`          got  ${JSON.stringify(got)}`);
    console.log(`          want ${JSON.stringify(want)}`);
  }
};

console.log("\nthe two rows the ordered chain could not read");
expect("an italic with a bold inside, both closed by one run of three",
  md("*Agnes Kolbe, 1685, **Evangelisch, Wuerttemberg***"),
  "<em>Agnes Kolbe, 1685, <strong>Evangelisch, Wuerttemberg</strong></em>");
expect("a bold with an italic inside, both closed by one run of three",
  md("**54 records, either *Baptisms* or *Ireland Births***"),
  "<strong>54 records, either <em>Baptisms</em> or <em>Ireland Births</em></strong>");

console.log("\nthe ordinary markers still read as before");
expect("bold", md("**b**"), "<strong>b</strong>");
expect("italic", md("*i*"), "<em>i</em>");
expect("a symmetric run of three is bold and italic",
  md("***x***"), "<strong><em>x</em></strong>");
expect("a quoted phrase", md("«q»"), "<em>«q»</em>");
expect("a bold opened with no space after an italic opener",
  md("*“**The decision 1987** (at that date)*"),
  "<em>“<strong>The decision 1987</strong> (at that date)</em>");

console.log("\na span never crosses a newline");
expect("two unmatched openers on different lines stay literal",
  md("**one\n\n**two"), "**one\n\n**two");
expect("one span per line, closed on its own line",
  md("**a**\n**b**"), "<strong>a</strong>\n<strong>b</strong>");

console.log("\nan unmatched marker stays visible, rather than being closed for the author");
expect("an opener with no closer", md("unclosed **bold"), "unclosed **bold");
expect("three open, two closed", md("***x**"), "***x**");

console.log("\na lone asterisk is a wildcard, not emphasis");
expect("a NAAIRS wildcard", md("BOOY* in the depot"), "BOOY* in the depot");
expect("a trailing wildcard does not pair with the next one",
  md("q.surname=Booij* and q.surname=Booy*"),
  "q.surname=Booij* and q.surname=Booy*");
/* ⚠ A KNOWN LIMIT, ASSERTED SO THAT IT IS A DECISION RATHER THAN A SURPRISE.
   The flanking rule cannot save a wildcard INSIDE a word: the asterisk in
   `B*rry` has a letter on both sides, which is exactly what an emphasis
   opener looks like, and the next wildcard closes it. This is the old
   renderer's behaviour too, unchanged here — there is no rule that separates
   the two without knowing it is reading a query. The remedy is at the caller:
   a register column that holds search queries is escaped, not rendered. The
   Booyzen searched register does this and says why. */
expect("a wildcard inside a word still pairs — the caller must not render such a column",
  md("q.surname=B*rry and Kolb*"), "q.surname=B<em>rry and Kolb</em>");
expect("spaced asterisks are not emphasis", md("2 * 3 * 4"), "2 * 3 * 4");

console.log("\ncode spans are held out of everything else");
expect("a glob inside backticks keeps its asterisk",
  md("`*.json` and `*.yml`"), "<code>*.json</code> and <code>*.yml</code>");
expect("a bold marker inside backticks stays literal",
  md("`**x**`"), "<code>**x**</code>");
expect("a code span inside a bold span",
  md("**a `b` c**"), "<strong>a <code>b</code> c</strong>");

console.log("\nescaping happens before any markup is produced");
expect("a script tag in the data cannot become one",
  md("<script>x</script>"), "&lt;script&gt;x&lt;/script&gt;");
expect("an ampersand", md("a & b"), "a &amp; b");
expect("a tag inside a code span is still escaped",
  md("`<b>`"), "<code>&lt;b&gt;</code>");

console.log("\nthe other exports still behave");
expect("mdp turns a blank line into a paragraph break",
  mdp("a\n\nb"), "a</p><p>b");
expect("plain strips the markers rather than rendering them",
  plain("**a** and *b*"), "a and b");
expect("mdNote renders blocks", mdNote("**a**\n\n- one\n- two"),
  "<p><strong>a</strong></p><ul><li>one</li><li>two</li></ul>");
expect("mdNote reads the same run of three as md",
  mdNote("**54 records, either *Baptisms* or *Ireland Births***"),
  "<p><strong>54 records, either <em>Baptisms</em> or <em>Ireland Births</em></strong></p>");

/* A renderer that only ever produced well-formed output on the cases it was
   shown has not been seen working. This is the shape it used to emit. */
console.log("\nthe output is well formed on every case above");
const nests = (h) => {
  const st = [];
  for (const m of h.matchAll(/<(\/?)(strong|em|code)\b[^>]*>/g)) {
    if (m[1]) { if (st.pop() !== m[2]) return false; } else st.push(m[2]);
  }
  return st.length === 0;
};
expect("the misnesting this fix was written for is gone",
  nests(md("**54 records, either *Baptisms* or *Ireland Births***")), true);
expect("...and the check can fail, so passing means something",
  nests("<em>a</strong></em>"), false);

console.log();
console.log(fails.length ? `${fails.length} failed` : "all cases behave");
process.exit(fails.length ? 1 : 0);
