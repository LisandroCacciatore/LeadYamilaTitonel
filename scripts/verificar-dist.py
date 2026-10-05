#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar-dist.py · verifica el sitio que se publica (dist/) antes de subirlo.

Sirve dist/ en local y comprueba, contra el servidor real:
  - las cuatro rutas responden 200 (portada, propuesta, sitio, informe);
  - los assets del sitio se sirven;
  - TODAS las páginas publicadas quedan con noindex;
  - robots.txt bloquea el indexado;
  - ninguna página quedó diciendo "index, follow".

Además renderiza la portada y el sitio nuevo con Chrome headless para descartar
errores de render, y deja una captura de la portada.

Uso:
    python scripts/armar-dist.py && python scripts/verificar-dist.py
"""

import functools
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PUERTO = 8940

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

def rutas_de(dist: Path) -> list:
    """Las rutas salen de lo que hay en dist/: no todos los leads publican las mismas
    piezas, así que no se puede fijar una lista."""
    rutas = ["/"]
    for d in sorted(dist.iterdir()):
        if d.is_dir() and (d / "index.html").exists():
            rutas.append(f"/{d.name}/")
    rutas.append("/robots.txt")
    return rutas


def assets_de(dist: Path) -> list:
    """Los assets del sitio tienen que servirse de verdad: tomo archivos reales de
    cada carpeta assets/ publicada, sin suponer nombres de cliente."""
    out = []
    for d in sorted(dist.glob("*/assets")):
        archivos = sorted(f for f in d.rglob("*") if f.is_file())[:2]
        out += [f"/{f.relative_to(dist).as_posix()}" for f in archivos]
    return out


def servir():
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(DIST))
    handler.log_message = lambda *a, **k: None
    httpd = ThreadingHTTPServer(("127.0.0.1", PUERTO), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def traer(ruta: str):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}{ruta}", timeout=15) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def main() -> int:
    if not (DIST / "index.html").exists():
        print("  ✗ falta dist/ — corré: python scripts/armar-dist.py")
        return 1

    httpd = servir()
    errores = []
    rutas = rutas_de(DIST)
    assets = assets_de(DIST)
    try:
        print("=" * 66)
        print("  VERIFICANDO EL SITIO PUBLICABLE (dist/)")
        print("=" * 66)

        for ruta in rutas + assets:
            status, cuerpo = traer(ruta)
            kb = len(cuerpo) // 1024
            print(f"  {status or 'ERR':>4}  {ruta:<46}{kb:>5} KB")
            if status != 200:
                errores.append(f"{ruta} no responde 200 ({cuerpo[:80]})")
                continue
            if ruta.endswith(("/", ".html")):
                if "noindex" not in cuerpo:
                    errores.append(f"{ruta} quedó indexable (sin noindex)")
                if re.search(r'content=["\']index,\s*follow', cuerpo, re.I):
                    errores.append(f"{ruta} todavía dice index, follow")

        _, robots = traer("/robots.txt")
        if "Disallow: /" not in robots:
            errores.append("robots.txt no bloquea el indexado")
        else:
            print("   ✓  robots.txt: Disallow: /")

        chrome = next((c for c in CHROME if Path(c).exists()), None)
        if chrome:
            with tempfile.TemporaryDirectory() as tmp:
                perfil = Path(tmp) / "p"
                aRenderizar = [("/", "portada")]
                if (DIST / "sitio" / "index.html").exists():
                    aRenderizar.append(("/sitio/", "sitio"))
                for ruta, nombre in aRenderizar:
                    dom = subprocess.run(
                        [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
                         f"--user-data-dir={perfil}", "--virtual-time-budget=9000",
                         "--dump-dom", f"http://127.0.0.1:{PUERTO}{ruta}"],
                        capture_output=True, text=True, errors="replace").stdout
                    if len(dom) < 2000:
                        errores.append(f"{ruta} renderizó un DOM sospechosamente corto")
                    print(f"   ✓  render {ruta:<8} {len(dom) // 1024} KB de DOM")
                destino = DIST / "capturas"
                destino.mkdir(exist_ok=True)
                subprocess.run(
                    [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
                     "--hide-scrollbars", f"--user-data-dir={perfil}", "--virtual-time-budget=9000",
                     "--window-size=1200,1000",
                     f"--screenshot={destino / 'portada.png'}",
                     f"http://127.0.0.1:{PUERTO}/"],
                    capture_output=True, text=True, errors="replace")
                print(f"   ✓  captura: {(destino / 'portada.png').relative_to(ROOT)}")
        else:
            print("   (sin Chrome: no verifico el render)")
    finally:
        httpd.shutdown()

    print("-" * 66)
    if errores:
        print("  ✗ EL PREVIEW TIENE PROBLEMAS")
        for e in errores:
            print(f"      - {e}")
        return 2
    print(f"  ✓ Las {len(rutas)} rutas" + (f" y {len(assets)} assets" if assets else "") +
          " responden 200")
    print("  ✓ Todas las páginas publicadas quedan con noindex")
    print("  ✓ robots.txt bloquea el indexado: el preview no compite con el sitio real")
    return 0


if __name__ == "__main__":
    sys.exit(main())
