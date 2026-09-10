#!/usr/bin/env bash
# Wrapper: garantisce l'ambiente virtuale con openpyxl e lancia leggi_rosa.py.
# Uso: rosa.sh [percorso/rosa.xlsx]   oppure   rosa.sh --template [percorso]
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
if ! "$VENV/bin/python" -c "import openpyxl" 2>/dev/null; then
  "$VENV/bin/pip" install -q openpyxl
fi
exec "$VENV/bin/python" "$DIR/leggi_rosa.py" "$@"
