#!/usr/bin/env python3
"""Refuse an atlas whose pins sit outside the country their own text names.

WHY THIS EXISTS, AND IT IS NOT HYPOTHETICAL. The Defranceschi archive geocoded
each place on the substring before the first comma, so «Pag, Zara, Dalmatien,
Oesterreich» was looked up as "pag" and matched the largest homonym on earth.
Three places were in the wrong countries on a published map:

    shown as                  actually                    out by
    Pagadian, Philippines     Pag, Dalmatia               ~9,000 km
    Basel, Switzerland        Bale-Valle, Istria            ~700 km
    San Lorenzo, Paraguay     San Lorenzo, Santa Fe, AR     ~900 km

Every one of them carried the answer in its own record. Pag had a string
saying Dalmatia and a pin in Mindanao. Nothing read the two together, and
nothing was going to, because the map looked perfectly reasonable: a dot in
the Philippines is only wrong if you know it should be in Croatia.

That session asked for the check to live here rather than in its builder,
which is right - every archive with a diaspora has this, and the ones that do
not have it yet will get it the first time somebody adds a place called
Springfield, Cambridge, Richmond or Valencia.

HOW IT DECIDES. Every country named in a place's own strings is looked up in
kit/data/country-boxes.json, which is bounded from the Record Atlas's 9,472
placed settlements. Those boxes are EMPIRICAL and therefore tight, so the
check allows a wide margin and reports the distance: the point has to be well
outside every country its text names before this refuses. A place naming two
countries - «Trieste, Italy, formerly Austria» - passes if it is near either.

  python3 checkplaces.py --data site/public/atlas-data.json
  python3 checkplaces.py --data site/public/atlas-data.json --km 200
"""
import io, os, re, sys, json, math, argparse, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
BOXES = os.path.join(os.path.dirname(HERE), "data", "country-boxes.json")

# The words these archives actually write, including the ones an empire left
# behind. A country is only tested when its name is IN the place's own text.
NAMES = {
    "HR": ["croatia", "hrvatska", "kroatien", "croazia", "dalmatia", "dalmatien",
           "dalmazia", "istria", "istrien", "istra"],
    "IT": ["italy", "italia", "italien"], "AT": ["austria", "osterreich", "austriaco"],
    "SI": ["slovenia", "slovenija"], "HU": ["hungary", "magyarorszag", "ungarn"],
    "DE": ["germany", "deutschland", "prussia", "preussen"],
    "PL": ["poland", "polska", "polen"], "CZ": ["czechia", "czech republic", "bohemia"],
    "SK": ["slovakia"], "RS": ["serbia"], "BA": ["bosnia", "herzegovina"],
    "ME": ["montenegro"], "GR": ["greece"], "TR": ["turkey"],
    "GB": ["england", "scotland", "wales", "united kingdom", "great britain"],
    "IE": ["ireland", "eire"], "FR": ["france"], "ES": ["spain", "espana"],
    "PT": ["portugal"], "CH": ["switzerland", "schweiz", "svizzera"],
    "NL": ["netherlands", "holland"], "BE": ["belgium"],
    "ZA": ["south africa", "suid-afrika", "cape colony", "transvaal", "natal",
           "orange free state"],
    "MZ": ["mozambique", "mocambique"], "ZW": ["rhodesia", "zimbabwe"],
    "AU": ["australia"], "NZ": ["new zealand"],
    "US": ["united states", "usa", "u.s.a."], "CA": ["canada"],
    "AR": ["argentina"], "BR": ["brazil", "brasil"], "UY": ["uruguay"],
    "PY": ["paraguay"], "CL": ["chile"], "PE": ["peru"], "VE": ["venezuela"],
    "MX": ["mexico"], "CU": ["cuba"], "PR": ["puerto rico"], "PH": ["philippines"],
    "IN": ["india"], "IL": ["israel"], "RO": ["romania"], "UA": ["ukraine"],
    "RU": ["russia"], "SE": ["sweden"], "NO": ["norway"], "DK": ["denmark"],
    "FI": ["finland"],
}


"""Matched on WORD BOUNDARIES, never as substrings. The first run of this
   tool reported four failures that were nothing of the kind: «istra» matched
   inside ADMINISTRATION, so a Cape farm was accused of being in Croatia, and
   «eire» matched inside FIGUEIREDO, so a woman born at Lourenco Marques was
   accused of being in Ireland. This is the same mistake as folding JAN into
   JOHANNES and matching every January - a short token inside a long word - and
   it has now been made twice in this estate. The country a place names is a
   word in its text, not a run of letters somewhere in it."""


def fold(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def km_outside(lat, lon, b):
    """0 when the point is in the box, otherwise roughly how far outside."""
    dlat = max(b[0] - lat, lat - b[2], 0.0)
    dlon = max(b[1] - lon, lon - b[3], 0.0)
    return math.hypot(dlat * 111.0, dlon * 111.0 * math.cos(math.radians(lat)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--km", type=float, default=300.0,
                    help="how far outside every named country before it refuses")
    a = ap.parse_args()

    boxes = json.load(io.open(BOXES, encoding="utf-8"))["countries"]
    d = json.load(io.open(a.data, encoding="utf-8"))
    places = d["places"] if isinstance(d, dict) else d

    bad, checked = [], 0
    for p in places:
        if p.get("lat") is None:
            continue
        # NAMING STRINGS ONLY - the name and its `also` forms - and not the
        # prose. A diaspora archive's description of a place names the country
        # people CAME FROM as often as the one the place is in, and reading it
        # accused Kabwe of being in Britain because a Briton died there. The
        # qualifier that disambiguates a homonym lives in the name: «Pag,
        # Zara, Dalmatien, Oesterreich», «Athens, Clarke County, Georgia,
        # USA». That is the string to read, and it is the one that was not
        # read. 
        hay = fold(" ".join([str(p.get("name") or "")] +
                            [str(x) for x in (p.get("also") or [])]))
        named = [cc for cc, words in NAMES.items()
                 if cc in boxes and any(re.search(r"\b" + re.escape(w) + r"\b", hay)
                                        for w in words)]
        if not named:
            continue
        checked += 1
        # nearest of the countries its own text claims
        outs = [(km_outside(p["lat"], p["lon"], boxes[cc]["box"]), cc) for cc in named]
        outs.sort()
        if outs[0][0] > a.km:
            bad.append((p["name"], p["lat"], p["lon"], outs[0][1], outs[0][0],
                        ", ".join(cc for _, cc in outs)))

    print("  %d place(s) name a country this kit can bound; %d checked"
          % (checked, checked))
    if bad:
        for nm, la, lo, cc, km, all_cc in sorted(bad, key=lambda x: -x[4])[:20]:
            print("  FAIL  %-34s at %.3f, %.3f is %,.0f km outside %s, and its own "
                  "text names %s".replace(",.0f", ".0f") % (nm[:34], la, lo, km, cc, all_cc))
        print("\n  FAIL  places   %d pin(s) sit outside every country their own text "
              "names" % len(bad))
        return 1
    print("  ok    places   every pin sits in a country its own text names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
