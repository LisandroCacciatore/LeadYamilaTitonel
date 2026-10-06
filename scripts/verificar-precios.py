#!/usr/bin/env python3
"""
Verifica que los precios que salen en una propuesta generada coincidan con la
fuente unica (templates/catalogo.json) y que los totales declarados cierren.

Motivo: un data.json / config con precios mal puede pasar desapercibido si los
errores se cancelan entre si (los totales dan bien y los line items no).

Uso:
    python scripts/verificar-precios.py [ruta/al/propuesta.html]

Sin argumento usa 01-propuesta/propuesta.html.
Salida: exit 0 si todo cierra, exit 1 si hay discrepancias.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGO = ROOT / "templates" / "catalogo.json"
DEFAULT_HTML = ROOT / "01-propuesta" / "propuesta.html"

errores: list[str] = []
avisos: list[str] = []


def parsear_html(path: Path):
    """Extrae BASE y MODULES del <script> embebido en la propuesta."""
    h = path.read_text(encoding="utf-8")

    m_base = re.search(r"\bBASE\s*=\s*(\d+)", h)
    if not m_base:
        raise SystemExit(f"✗ No encontre 'BASE = <numero>' en {path}")
    base = int(m_base.group(1))

    m_mods = re.search(r"\bMODULES\s*=\s*(\[.*?\]);", h, re.DOTALL)
    if not m_mods:
        raise SystemExit(f"✗ No encontre 'MODULES = [...]' en {path}")
    modulos = json.loads(m_mods.group(1))

    # Los totales declarados en pantalla, para contrastar.
    usd = sorted({int(x.replace(".", "")) for x in re.findall(r"USD\s*([\d.]+)", h)})
    return base, modulos, usd


def main() -> int:
    html_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_HTML

    if not CATALOGO.exists():
        raise SystemExit(f"✗ No existe la fuente unica: {CATALOGO}")
    if not html_path.exists():
        raise SystemExit(f"✗ No existe la propuesta: {html_path}")

    catalogo = {
        a["id"]: a for a in json.loads(CATALOGO.read_text(encoding="utf-8"))["addons"]
    }
    base, modulos, usd_declarados = parsear_html(html_path)

    print(f"Fuente unica : {CATALOGO.relative_to(ROOT)}  ({len(catalogo)} add-ons)")
    print(f"Propuesta    : {html_path.relative_to(ROOT) if html_path.is_relative_to(ROOT) else html_path}")
    print(f"BASE         : USD {base}")
    print(f"MODULES      : {len(modulos)}")
    print(f"USD en pagina: {['USD ' + f'{u:,}'.replace(',', '.') for u in usd_declarados]}")
    print()

    # 1) Cada modulo del render debe existir en el catalogo con el mismo precio.
    print("  modulo                    render   catalogo   estado")
    print("  " + "-" * 56)
    suma_recomendados = 0
    suma_total = 0
    for m in modulos:
        mid = m.get("id")
        precio_render = m.get("price")
        precio_catalogo = catalogo.get(mid, {}).get("price")
        suma_total += precio_render

        es_rec = bool(m.get("recomendado"))
        if es_rec:
            suma_recomendados += precio_render

        if mid not in catalogo:
            estado = "FALTA EN CATALOGO"
            errores.append(f"{m.get('code')} ({mid}) no existe en catalogo.json")
        elif precio_render != precio_catalogo:
            estado = f"MISMATCH  Δ{precio_render - precio_catalogo:+d}"
            errores.append(
                f"{m.get('code')} ({mid}): render USD {precio_render} != "
                f"catalogo USD {precio_catalogo} (Δ{precio_render - precio_catalogo:+d})"
            )
        else:
            estado = "ok"

        marca = "REC" if es_rec else "   "
        print(f"  {m.get('code','?'):<4}{mid:<18}{marca} {precio_render:>6} {str(precio_catalogo):>10}   {estado}")

    # 2) Totales derivados.
    rec_esperado = base + suma_recomendados
    pack_esperado = base + suma_total

    print()
    print(f"  suma add-ons        : USD {suma_total}")
    print(f"  recomendado (deriv.) : USD {rec_esperado}   (base + recomendados)")
    print(f"  pack completo        : USD {pack_esperado}   (base + todos)")
    print()

    # 3) Los totales tienen que estar declarados en la pagina.
    for etiqueta, valor in (("recomendado", rec_esperado), ("pack completo", pack_esperado)):
        if valor in usd_declarados:
            print(f"  ✓ {etiqueta} USD {valor} aparece en la pagina")
        else:
            errores.append(
                f"El total {etiqueta} derivado (USD {valor}) NO aparece en la pagina "
                f"(aparecen: {usd_declarados})"
            )

    # 4) El pack con descuento se retiro del generador (no hay descuento por
    #    volumen). Este chequeo queda como guarda de regresion: si alguien lo
    #    reintroduce escrito a mano en la plantilla, salta.
    exacto = round(pack_esperado * 0.85)
    redondeado = round(pack_esperado * 0.85 / 5) * 5
    if redondeado in usd_declarados or exacto in usd_declarados:
        avisos.append(
            f"La pagina declara un pack con descuento (USD {redondeado}) que el "
            f"generador ya no emite. Sacar el escenario o volver a derivarlo."
        )

    # 5) La trampa: precios distintos con totales iguales.
    if errores and not any("NO aparece" in e for e in errores):
        print()
        print("  ⚠  Los precios de linea NO coinciden con el catalogo,")
        print("     pero los totales declarados SI cierran. Es exactamente la")
        print("     trampa: los errores se cancelan y el total esconde el error.")

    print()
    for a in avisos:
        print(f"  ⚠  {a}")
    for e in errores:
        print(f"  ✗  {e}")

    print()
    if errores:
        print(f"  {len(errores)} discrepancia(s) -> NO PUBLICAR")
        return 1
    print("  ✓ precios coherentes con la fuente unica")
    return 0


if __name__ == "__main__":
    sys.exit(main())
