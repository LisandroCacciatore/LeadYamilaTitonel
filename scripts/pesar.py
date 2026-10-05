#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pesar.py · mide lo que de verdad baja el visitante: HTML + CSS + JS + imágenes.

El peso del HTML solo engaña: una página de 26 KB puede obligar a bajar 1 MB
de bibliotecas. Este script resuelve los recursos que el HTML referencia y suma
lo que el navegador tiene que traer para mostrar la página.

Uso:
    python scripts/pesar.py https://www.liclisandrolagos.com/
    python scripts/pesar.py http://127.0.0.1:8931/
"""

import re
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medir  # noqa: E402


def recursos(html: str, base: str):
    urls = set()
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
        urls.add(m.group(1))
    for m in re.finditer(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\']', html, re.I):
        urls.add(m.group(1))
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I):
        urls.add(m.group(1))
    for m in re.finditer(r'<source[^>]+srcset=["\']([^"\']+)["\']', html, re.I):
        urls.add(m.group(1).split()[0])
    salida = []
    for u in urls:
        if u.startswith("data:") or u.startswith("#"):
            continue
        salida.append(urljoin(base, u))
    return sorted(set(salida))


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/pesar.py <url> [url2 ...]")
        return 1

    for url in sys.argv[1:]:
        status, html, final, _ = medir.fetch(url)
        if status != 200:
            print(f"{url} -> {status}: no se pudo medir")
            continue

        base = re.match(r"^(https?://[^/]+)", final or url).group(1)
        html_kb = len(html.encode("utf-8", errors="replace")) / 1024
        total = html_kb
        detalle = []

        for r in recursos(html, base):
            st, body, _, headers = medir.fetch(r, timeout=25)
            kb = len(body.encode("utf-8", errors="replace")) / 1024 if st == 200 else 0
            if kb == 0 and headers.get("Content-Length"):
                kb = int(headers["Content-Length"]) / 1024
            if kb == 0:
                continue
            total += kb
            tipo = ("JS" if r.endswith(".js") or ".js?" in r else
                    "CSS" if ".css" in r else "IMG")
            detalle.append((tipo, kb, r))

        detalle.sort(key=lambda x: -x[1])
        print(f"\n{url}")
        print(f"  HTML servido          : {html_kb:6.1f} KB")
        for tipo, kb, r in detalle[:8]:
            nombre = r.split("/")[-1][:44]
            print(f"  {tipo:<5} {kb:6.1f} KB  {nombre}")
        if len(detalle) > 8:
            resto = sum(k for _, k, _ in detalle[8:])
            print(f"  {'...':<5} {resto:6.1f} KB  ({len(detalle) - 8} recursos más)")
        print(f"  {'TOTAL':<5} {total:6.1f} KB  ({len(detalle) + 1} archivos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
