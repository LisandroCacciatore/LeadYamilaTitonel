#!/usr/bin/env bash
# ==========================================================================
# scripts/generar.sh — CONSTRUYE las dos piezas del lead.
#
#   1. informe.html          (00-auditoria/)   documento A4 paginado
#   2. propuesta.html        (01-propuesta/)   propuesta comercial con selector
#   3. verificar-precios.py                    precios del render vs catalogo.json
#   4. verify.py                               render real en Chrome headless
#
# No exporta PDF y no reclama que el documento esté bien: eso es
# `scripts/verificar-todo.sh`, que es EL COMANDO ESTÁNDAR. Este script existe
# para iterar contenido sin pagar el costo de los seis gates.
#
# Si algo no cierra, corta con error.
#
# Uso:  bash scripts/generar.sh
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
echo "Construido:"
echo "  00-auditoria/informe.html"
echo "  01-propuesta/propuesta.html"
echo
echo "Para validar y exportar el entregable completo:"
echo "  bash scripts/verificar-todo.sh"
