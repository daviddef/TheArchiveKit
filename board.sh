#!/bin/sh
# The estate board, from anywhere.
#
#   ./board.sh            build it and open it
#   ./board.sh -o out.html   build it somewhere specific
#
# Written because the command it wraps needs two absolute paths and was handed
# over with neither, so it failed the first time it was run from a home
# directory. A command that only works from one folder is a command with an
# undocumented argument.
set -e
KIT="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$KIT")"
OUT="${HOME}/board.html"
[ "$1" = "-o" ] && OUT="$2"
python3 "$KIT/kit/tools/worklist_rollup.py" --root "$ROOT" --out "$OUT"
if [ "$1" != "-o" ] && command -v open >/dev/null 2>&1; then open "$OUT"; fi
exit 0
