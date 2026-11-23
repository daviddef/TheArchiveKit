# cleantree.py: a build must leave the git working tree clean

`kit/tools/cleantree.py` (proved by `cleantree_selftest.py`, 16 cases) is run AFTER `npm run build` in an archive. It
asks git what the build changed and exits 1, listing the files, if the build rewrote any file git tracks. A tracked
file a build rewrites means the committed copy and the built copy have drifted; the site is right, the build is green,
and the next person's diff is full of changes they did not make. It is read only: it never commits, resets, cleans,
stashes or adds, and it asks git not to refresh the index.

| | |
|---|---|
| tracked file changed (modified, deleted, renamed, staged, conflicted) | **fails** (exit 1), listed with its git status code |
| new untracked file that is not ignored | listed under its own heading; fails only with `--fail-untracked` |
| ignored file (`site/dist`, `node_modules`, the GEDCOM) | never listed |
| `--allow GLOB` (repeatable; none by default) | the documented escape for a file a build must rewrite; `fnmatch` against the path from the repository root, `*` crosses `/`; an `--allow` that matches nothing is noted so it can be dropped |
| `--root DIR` | the repository, or a directory inside it (only paths below it are checked) |
| exit 2 | not a git repository, or git would not answer |

It cannot tell a file the build rewrote from one you edited by hand first, so it belongs in CI (a clean checkout); locally,
commit or stash before running it. The usual cure for a finding is to commit the regenerated file or to stop tracking
it and ignore it; `--allow` is for the file that genuinely must be rewritten, and each one needs a reason beside it.

## Wiring it into an archive (one PR each, after a kit pin bump)

    "check:cleantree": "python3 node_modules/@daviddef/archive-kit/kit/tools/cleantree.py --root .."

(the path from `site/`, where the archive's `package.json` lives; use `--root .` from the repository root), and in
`.github/workflows/deploy.yml`, after the last build step (the one that rebuilds with the search index, where there is
one) and before upload:

    - name: The build must leave git clean
      run: npm run check:cleantree
      working-directory: site

Push one archive and watch it deploy before wiring the rest (see traps.md, "Passed locally, failed on the runner").
