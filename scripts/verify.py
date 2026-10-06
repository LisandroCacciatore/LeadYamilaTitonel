#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py · verifica las dos piezas sobre el DOM renderizado, no sobre el HTML fuente.

Un informe paginado y un selector interactivo sólo se prueban ejecutando el JavaScript:
acá se renderiza con Chrome/Edge headless (--dump-dom) y se mira lo que se ve.

Uso:
    python scripts/verify.py
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INFORME = ROOT / "00-auditoria" / "informe.html"
PROPUESTA = ROOT / "01-propuesta" / "propuesta.html"
CONFIG = ROOT / "config.json"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def dump_dom(chrome, url: Path, profile: Path) -> str:
    res = subprocess.run([
        chrome, "--headless=new", "--disable-gpu", "--no-first-run",
        "--no-default-browser-check", f"--user-data-dir={profile}",
        "--virtual-time-budget=9000", "--dump-dom", url.resolve().as_uri(),
    ], capture_output=True, text=True, errors="replace")
    # El texto dentro de <script> repite los strings que también se renderizan.
    # Lo que se mide es lo que SE VE.
    return re.sub(r"<script\b.*?</script>", "", res.stdout, flags=re.S | re.I)


def main() -> int:
    for f in (INFORME, PROPUESTA, CONFIG):
        if not f.exists():
            print(f"  ✗ falta {f.relative_to(ROOT)} — corré primero: python scripts/generate.py")
            return 1

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    n_hallazgos = len(cfg.get("hallazgos", []))
    n_modulos = len(cfg.get("modulos", []))
    base = int(cfg.get("base", {}).get("precio", 0))

    chrome = find_chrome()
    if not chrome:
        print("No encontré Chrome ni Edge: no puedo verificar el render.")
        return 1

    print("=" * 68)
    print("  VERIFICANDO RENDER")
    print(f"  motor: {Path(chrome).name}")
    print("=" * 68)

    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        dom_inf = dump_dom(chrome, INFORME, profile)
        dom_prop = dump_dom(chrome, PROPUESTA, profile)

    errores = []
    doms = {"informe": dom_inf, "propuesta": dom_prop}

    # ---- Invariante 1: las dos piezas comparten marca, membrete y pie
    for name, dom in doms.items():
        if "--brand-default" not in dom.replace(" ", ""):
            errores.append(f"{name}: el token de marca no está en el DOM")
        if "brand-header" not in dom:
            errores.append(f"{name}: el DOM no tiene el membrete")
        if "brand-footer" not in dom:
            errores.append(f"{name}: el DOM no tiene el pie")

    # ---- Invariante 2: el informe paginó sin cortar contenido
    inf = dom_inf
    n_find = len(re.findall(r'class="finding"', inf))
    n_comp = len(re.findall(r'class="compare-table"', inf))
    hojas = re.search(r'data-hojas="(\d+)"', inf)
    desb = re.search(r'data-desbordes="(\d+)"', inf)
    n_hojas = int(hojas.group(1)) if hojas else 0
    n_desb = int(desb.group(1)) if desb else -1
    print(f"  informe   : {n_find} hallazgos · {n_comp} comparativo · "
          f"{n_hojas} hojas · desbordes={n_desb}")
    if n_find != n_hallazgos:
        errores.append(f"informe: esperaba {n_hallazgos} hallazgos, hay {n_find}")
    # El comparativo es opcional: hay configs cuyo comparativo es una tabla de mercado
    # orientativa, que sólo tiene sentido en la propuesta y no bajo el título «verificado».
    comp_cfg = cfg.get("comparativo", {})
    espera_comp = bool(comp_cfg.get("filas")) and comp_cfg.get("mostrarEnInforme") is not False
    if espera_comp and n_comp != 1:
        errores.append("informe: el comparativo verificado no se renderizó")
    if not (5 <= n_hojas <= 16):
        errores.append(f"informe: el paginador armó {n_hojas} hojas (esperado 5-16)")
    if n_desb != 0:
        errores.append(f"informe: el paginador reporta {n_desb} hoja(s) con desborde")
    # §4: el informe es sólo diagnóstico. Precios y módulos viven en la propuesta.
    if re.search(r'class="mod-row"|class="base-card"|class="total-row"', inf):
        errores.append("informe: tiene precios o módulos (§4: sólo diagnóstico)")
    if "ver la propuesta" not in inf.lower():
        errores.append("informe: falta el CTA de cierre «Ver la propuesta →»")
    if "Página 1 de" not in inf and "Página " not in inf:
        errores.append("informe: no encontré la numeración de páginas")
    if "banner" in inf and "Error al armar el documento" in inf:
        errores.append("informe: el paginador reportó un error interno")

    # ---- Invariante 3: la propuesta ejecutó su JS y calcula el total
    prop = dom_prop
    # Cuenta tarjetas, no una clase exacta: el recomendado va con clase extra
    # («module-card rec») y con el patrón cerrado el gate daba 9 de 14 en falso.
    n_cards = len(re.findall(r'class="module-card[ "]', prop))
    total = re.search(r'id="total"[^>]*>([^<]+)<', prop)
    total_txt = total.group(1).strip() if total else None
    n_kpi = len(re.findall(r'class="kpi"', prop))
    print(f"  propuesta : {n_cards} tarjetas de módulo · total = {total_txt} · {n_kpi} indicadores")
    if n_cards != n_modulos:
        errores.append(f"propuesta: el JS no renderizó las {n_modulos} tarjetas (hay {n_cards})")
    esperado = f"USD {base}"
    if total_txt != esperado:
        errores.append(f'propuesta: el total inicial debería ser "{esperado}", es {total_txt!r}')
    # §4.1 del spec editorial: máximo 4 números en el cuadro, y 3 cuando no hay una
    # unidad común entre ellos. Menos de 3 sí es un cuadro pobre.
    if n_kpi < 3 or n_kpi > 4:
        errores.append(f"propuesta: el cuadro tiene {n_kpi} indicadores (el spec pide 3 o 4)")
    # Guard de datos sin resolver: un bloque mal formado (items como objeto en vez de
    # par) hacía que el documento imprimiera las CLAVES — «título body» — y los tres
    # gates pasaban igual. Los placeholders {{...}} ya se chequean; esto es la otra
    # mitad: el dato llegó, pero se leyó mal.
    for artefacto in ("título body", "titulo body", ">None<", "&gt;None&lt;", "{}"):
        if artefacto in prop:
            errores.append(f"propuesta: quedó un dato sin resolver en el DOM: {artefacto!r}")
    # El comparativo puede ser tabla (colegas medidos, §6.2) o 3 bullets (cuando no hay
    # comparables medidos). Antes bastaba con que la clase apareciera en el CSS.
    if '<table class="compare-table"' not in prop and "comp-bullets" not in prop:
        errores.append("propuesta: no hay comparativo (ni tabla de colegas ni bullets §6.2)")
    for h in cfg.get("hallazgos", []):
        # §4: la propuesta titula corto y el informe titula largo. Alcanza con que
        # aparezca el título que le corresponde a esta pieza.
        t = h.get("tituloCorto") or h.get("titulo", "")
        if t[:30] not in prop:
            errores.append(f"propuesta: falta el hallazgo «{t[:40]}»")
            break

    # ---- Invariante 4: ningún placeholder quedó visible
    for name, dom in doms.items():
        left = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", dom)))
        if left:
            errores.append(f"{name}: placeholders sin resolver en el DOM -> {left}")

    print("-" * 68)
    if errores:
        print("  ✗ VERIFICACIÓN DE RENDER FALLÓ")
        for e in errores:
            print(f"      - {e}")
        return 2
    print("  ✓ Las dos piezas renderizadas comparten marca, membrete y pie")
    print(f"  ✓ El informe paginó: {n_hallazgos} hallazgos, {n_modulos} módulos, "
          f"{n_hojas} hojas, desbordes=0")
    print(f"  ✓ La propuesta ejecutó su JS: {n_modulos} tarjetas, total inicial {esperado}")
    print("  ✓ Ningún placeholder quedó visible en el DOM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
