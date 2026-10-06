#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bajar-fuentes.py · baja Inter y JetBrains Mono a brand/assets/fonts/

Por que local y no CDN: el PDF se genera con Chrome headless y se manda por mail.
Si la tipografia sale de fonts.googleapis.com en el momento del render, el dia que
la red falle -o el cliente abra el PDF en una maquina sin esa fuente- el documento
cambia de tipografia. Con el .woff2 al lado del HTML, el PDF sale siempre igual.

Las dos son FUENTES VARIABLES: Google devuelve el mismo archivo para cada peso
(mismo hash). Por eso se guarda UN archivo por familia y en el @font-face se
declara un rango (`font-weight: 100 900`), no un valor suelto. Declararlas por
peso con el mismo archivo hace que el navegador sintetice el peso y salga todo
igual de grueso.

Uso:  python scripts/bajar-fuentes.py
"""
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "brand" / "assets" / "fonts"

# Chrome moderno => Google devuelve woff2 (con UA viejo devuelve ttf).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

FAMILIAS = {
    "Inter":         "family=Inter:wght@400;500;600;700;800",
    "JetBrainsMono": "family=JetBrains+Mono:wght@400;500;700",
}


def traer(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def bajar_familia(nombre: str, query: str) -> int:
    css = traer(f"https://fonts.googleapis.com/css2?{query}&display=swap").decode("utf-8")

    # Cada @font-face viene precedido por un comentario con el subset:
    #   /* latin */ @font-face { src: url(...woff2); font-weight: 400; }
    urls = []
    for subset, cuerpo in re.findall(
        r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", css, re.DOTALL
    ):
        if subset != "latin":          # sólo el alfabeto base
            continue
        m = re.search(r"url\((https://[^)]+\.woff2)\)", cuerpo)
        if m:
            urls.append(m.group(1))

    if not urls:
        print(f"  !! {nombre}: Google no devolvio ningun woff2 latin")
        return 0

    # Variable: todos los pesos son el mismo archivo. Verificado por hash.
    archivos = {}
    for u in dict.fromkeys(urls):      # sin repetir
        datos = traer(u)
        archivos.setdefault(hashlib.sha256(datos).hexdigest(), datos)

    if len(archivos) != 1:
        print(f"  !! {nombre}: se esperaba 1 archivo variable, llegaron {len(archivos)}")
        return 0

    datos = next(iter(archivos.values()))
    archivo = DEST / f"{nombre}.woff2"
    archivo.write_bytes(datos)
    print(f"  ok  {archivo.name}  ({archivo.stat().st_size // 1024} KB, variable 100-900)")
    return 1


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    # Limpia los archivos por peso de una corrida anterior.
    for viejo in DEST.glob("*-[0-9]*.woff2"):
        viejo.unlink()
        print(f"  --  borrado {viejo.name} (los pesos viven en un solo archivo variable)")
    total = 0
    for nombre, query in FAMILIAS.items():
        print(f"{nombre}:")
        total += bajar_familia(nombre, query)
    print(f"\n{total} archivo(s) en {DEST.relative_to(ROOT)}")
    return 0 if total == len(FAMILIAS) else 1


if __name__ == "__main__":
    sys.exit(main())
