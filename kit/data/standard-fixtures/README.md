Invented fixtures for kit/tools/checkstandard_selftest.py. Every name here is made up; none is a real person.

- standard.json   the archive's config (pages, citation patterns, what counts as a record link, how a scan is keyed)
- index.json      the archive's names index (the same file autolink.py reads); one entry is a /who/ entry for a person read from a register
- living.json     the living/held-out list
- site/           a tiny built site. /story/ and /notes/ are the narrative pages in scope and meet the standard exactly (every
                  count 0; EX 2 for two deliberate exemptions); /other/ breaks every rule but is not in scope; /plates/ holds the
                  scans; /people/ and /who/ are the entry pages the index points to. The self-test copies the site to a
                  temporary directory, plants one fault at a time at the <!--END1--> and <!--END2--> markers, and never changes it.
