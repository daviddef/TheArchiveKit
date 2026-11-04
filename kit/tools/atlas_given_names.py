#!/usr/bin/env python3
r"""Fetch the Atlas's given-name catalogue for this archive's "Say your name" page.

    python3 ../Archive\ Kit/kit/tools/atlas_given_names.py site/src/data/given-names.json \
        [--seen site/src/data/givennames.json] [--strict]
    python3 .../atlas_given_names.py OUT.json --from "../Record Atlas/site/public/given-names.json"

The forms of a given name (Ivan, Johann, Giovanni, Zuane, Joannes) are kept ONCE, in Record Atlas
(data/given-name-families.json, written only through scripts/given_name_variants.py) and published as
https://recordatlas.org/given-names.json in the shape SayYourName.astro reads: rows [{canon, langs:{lang:[{form, seen,
status, note, notNominative}]}, slips, notSame}], languages [{key,label,note}]. An archive does not keep its own table
of forms.

WHAT `seen` MEANS HERE. In the Atlas file `seen` is how many times ANY family archive has met the form. The page says
«attested in the records gathered here», and a form that only another archive met is not that: it is exactly the claim
the archives' own build gates were written to stop. So pass `--seen FILE` (this archive's own count of every form in its
records) and the output carries `seen` = THIS archive's count, `seenAll` = the Atlas's count across archives. Without
`--seen` every `seen` is left as the Atlas has it and the page must not call it «here».

`--seen FILE` takes {"observed": {canon: {form: n}}} (the shape tools/given_names.py writes), {canon: {form: n}} or a
flat {form: n}. Forms are matched without case, accents or a trailing «?» (an uncertain reading). A form in the records that the Atlas does not hold is
listed (these are what to add: `given_name_variants.py add`, then publish) and, with `--strict`, the exit status is 2,
so a build gate can refuse a form nobody has catalogued. Many of those are not names at all (a place written in the
name column); say so in the add, or fix the record.

Writes the file only when the fetch parses and has rows; keeps the old file otherwise (a build must not lose its data
because the network blinked).
"""
import json, sys, unicodedata, urllib.request

URL = "https://recordatlas.org/given-names.json"


def fold(s):
    """No case, no accents, and no trailing «?»: a reading marked uncertain («Maria?») is a reading of Maria."""
    t = "".join(c for c in unicodedata.normalize("NFD", str(s).lower()) if not unicodedata.combining(c))
    return t.strip().rstrip("?").strip()


def local_counts(path):
    d = json.load(open(path, encoding="utf-8"))
    d = d.get("observed", d) if isinstance(d, dict) else {}
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for form, n in v.items():
                out[fold(form)] = out.get(fold(form), 0) + int(n or 0)
        else:
            out[fold(k)] = out.get(fold(k), 0) + int(v or 0)
    return out


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    out, src = args[0], URL
    if "--from" in args:
        src = args[args.index("--from") + 1]
    try:
        if src.startswith("http"):
            req = urllib.request.Request(src, headers={"User-Agent": "ArchiveKit/1.0 (family archive build)"})
            data = json.load(urllib.request.urlopen(req, timeout=60))
        else:
            data = json.load(open(src, encoding="utf-8"))
        assert data.get("rows") and data.get("languages")
    except Exception as e:
        sys.exit(f"not updated ({e}); the existing {out} is kept")

    missing = []
    if "--seen" in args:
        seen_path = args[args.index("--seen") + 1]
        try:
            mine = local_counts(seen_path)
        except Exception as e:
            sys.exit(f"not updated (could not read --seen {seen_path}: {e}); the existing {out} is kept")
        held = set()
        for r in data["rows"]:
            for forms in (r.get("langs") or {}).values():
                for f in forms:
                    k = fold(f["form"])
                    held.add(k)
                    f["seenAll"] = f.get("seen", 0)
                    f["seen"] = mine.get(k, 0)
        missing = sorted(k for k, n in mine.items() if n and k not in held)
        data["seenIs"] = "this archive's own records"

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{out}: {len(data['rows'])} names, {data['totalForms']} forms, from {src}")
    if "--seen" in args:
        print(f"  {len(missing)} form(s) in the records are not in the Atlas catalogue"
              + (": " + ", ".join(missing[:40]) if missing else ""))
        if missing and "--strict" in args:
            sys.exit(2)


if __name__ == "__main__":
    main()
