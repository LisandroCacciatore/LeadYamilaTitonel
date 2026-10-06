#!/usr/bin/env bash
# ==========================================================================
# scripts/generar.sh — genera las dos piezas del lead y las verifica.
#
#   1. informe.html    (00-auditoria/)   documento A4 paginado
#   2. propuesta.html  (01-propuesta/)   propuesta comercial con selector
#   3. verify.py                         render real en Chrome headless
#
# Si algo no cierra, no hay entregable: el script corta con error.
#
# Uso:  ./scripts/generar.sh
# ==========================================================================
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

# En este host bash es MSYS: existe `python` (3.11), no `python3`.
PY="$(command -v python || command -v python3)"
if [[ -z "${PY}" ]]; then
  echo "No encontré un intérprete de Python." >&2
  exit 1
fi

echo "== Generando informe y propuesta desde config.json =="
"$PY" scripts/generate.py

echo
echo "== Verificando coherencia de precios contra la fuente unica =="
"$PY" scripts/verificar-precios.py

echo
echo "== Verificando el render (Chrome headless) =="
"$PY" scripts/verify.py

echo
echo "== Exportando la propuesta a PDF =="
"$PY" scripts/exportar-pdf.py

echo
echo "Listo:"
echo "  00-auditoria/informe.html"
echo "  01-propuesta/propuesta.html"
echo "  01-propuesta/propuesta-*.pdf"
echo
echo "Para el PDF del informe y la evidencia:"
echo "  python scripts/verify-pdf.py"
echo "  python scripts/consolidar-evidencia.py"
