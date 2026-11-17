/* when.js — the one reading of a work date, shared by lib/pulse.js (What's new) and lib/corrections.js (the corrections page), so the two cannot disagree
   about what day a row is. Pure. */
const MON = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };

/* "2026-11-11", "2026-11", "11 Nov 2026", "5 October 2026", "Sept 2026" (a month alone: day 1, exact false); anything else (a bare record
   year, a sentence) is not a date the work was done on, and returns null */
export function parseWhen(s) {
  const t = String(s == null ? "" : s).trim();
  let m = /^(\d{4})-(\d{2})(?:-(\d{2}))?(?:$|[T\s])/.exec(t);
  if (m) {
    const mo = +m[2];
    if (mo < 1 || mo > 12) return null;
    return { iso: `${m[1]}-${m[2]}-${m[3] || "01"}`, exact: !!m[3] };
  }
  m = /^(?:(\d{1,2})\s+)?([A-Za-z]{3,})\.?\s+(\d{4})$/.exec(t);
  if (!m) return null;
  const mo = MON[m[2].slice(0, 3).toLowerCase()];
  if (mo === undefined) return null;
  const day = m[1] ? +m[1] : 1;
  return { iso: `${m[3]}-${String(mo + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`, exact: !!m[1] };
}

