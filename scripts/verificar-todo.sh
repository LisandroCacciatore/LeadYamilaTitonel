#!/usr/bin/env bash
# ==========================================================================
# scripts/verificar-todo.sh — EL ESTÁNDAR. Un comando, todos los gates.
#
# Es la checklist §12 del SPEC-workflow hecha script: si esto sale en verde, el
# entregable es publicable. Si algo falla, NO hay entregable.
#
# DOS FASES, a propósito:
#
#   Fase 1 — DIAGNÓSTICO. Corre todos los gates aunque uno falle: un rojo
#   temprano no tiene que esconder los demás.
#
#   Fase 2 — ARTEFACTOS. Sólo si la fase 1 quedó entera en verde. Un PDF
#   recién escrito con un precio mal es peor que no tener PDF: se manda.
#   Con gates en rojo los PDFs NO se tocan.
#
#   1/6  construir          generate + precios + render (scripts/generar.sh)
#   2/6  workflow v2.0      orden, promesas de base, fechas, solo USD
#   3/6  editorial v1.0     tono, patrones de hallazgo, mobile, tipografía
#   4/6  promesas           lo prometido contra el sitio publicado
#   ── corte: de acá para abajo sólo con la fase 1 en verde ──
#   5/6  PDF del informe    hojas, membrete repetido, sin precios (§4)
#   6/6  PDF de la propuesta
#
# Uso:  bash scripts/verificar-todo.sh
# ==========================================================================
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

PY="$(command -v python || command -v python3)"
if [[ -z "${PY}" ]]; then
  echo "No encontré un intérprete de Python." >&2
  exit 1
fi

fallos=0
RESUMEN=()

paso() {                      # paso "nombre" comando...
  local nombre="$1"; shift
  echo
  echo "──────────────────────────────────────────────────────────────────"
  echo "  $nombre"
  echo "──────────────────────────────────────────────────────────────────"
  if "$@"; then
    RESUMEN+=("OK    $nombre")
  else
    RESUMEN+=("FALLA $nombre")
    fallos=$((fallos + 1))
  fi
}

# validar-spec con --dist sólo si el dist está construido: agrega el chequeo de
# la home publicada, que sin dist no aplica.
SPEC_ARGS=()
[[ -d dist ]] && SPEC_ARGS=(--dist)

# ─────────── Fase 1 · diagnóstico ───────────
paso "1/6  construir el entregable"        bash scripts/generar.sh
paso "2/6  spec del workflow (v2.0)"       "$PY" scripts/validar-spec.py ${SPEC_ARGS[@]+"${SPEC_ARGS[@]}"}
paso "3/6  spec editorial (v1.0)"          "$PY" scripts/validar-editorial.py
paso "4/6  promesas vs sitio publicado"    "$PY" scripts/cotejar-promesas.py

# ─────────── Fase 2 · artefactos ───────────
if [[ "$fallos" -gt 0 ]]; then
  RESUMEN+=("SALTEA 5/6  PDF del informe  (fase 1 en rojo)")
  RESUMEN+=("SALTEA 6/6  PDF de la propuesta  (fase 1 en rojo)")
else
  paso "5/6  PDF del informe"              "$PY" scripts/verify-pdf.py
  paso "6/6  PDF de la propuesta"          "$PY" scripts/exportar-pdf.py
fi

echo
echo "══════════════════════════════════════════════════════════════════════"
for linea in "${RESUMEN[@]}"; do echo "  $linea"; done
echo "══════════════════════════════════════════════════════════════════════"

if [[ "$fallos" -gt 0 ]]; then
  echo "  ✗ $fallos gate(s) en rojo: NO PUBLICAR."
  echo "    Los PDFs quedaron como estaban: no se reescribió ningún entregable."
  exit 1
fi

echo "  ✓ Todo en verde. El entregable es publicable."
echo
echo "  Informe   : 00-auditoria/informe-*.pdf"
echo "  Propuesta : 01-propuesta/propuesta-*.pdf"
