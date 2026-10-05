#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
movil.py · verifica y captura el sitio a ancho de celular real.

Chrome en Windows no acepta ventanas de menos de ~500px, así que --window-size
no sirve para probar 390px: la página se maqueta a 497 y la captura sale cortada.
La solución es un iframe del ancho pedido: el iframe SÍ impone un viewport de
390px y los @media responden a ese ancho.

Además de la captura, recorre el DOM del iframe y reporta qué elementos se
saldrían del ancho (desborde horizontal), que es el defecto más común en móvil.

Uso:
    python scripts/movil.py 02-sitio/index.html 390
    python scripts/movil.py 02-sitio/index.html 390 02-sitio/capturas/nuevo-mobile.png
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

ENVOLTORIO = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>esperando…</title>
<style>html,body{{margin:0;padding:0;background:#fff}}iframe{{display:block;border:0}}</style></head>
<body>
<iframe id="f" src="{src}" width="{ancho}" height="{alto}"></iframe>
<script>
var f = document.getElementById('f');
f.addEventListener('load', function () {{
  setTimeout(function () {{
    try {{
      var d = f.contentDocument, w = f.contentWindow;
      var anchoReal = d.documentElement.clientWidth;
      var out = [], nodos = d.querySelectorAll('body *');
      for (var i = 0; i < nodos.length; i++) {{
        var el = nodos[i], r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) continue;
        var cls = (typeof el.className === 'string' ? el.className : '');
        if (r.left < -100 || /(^|\\s)(skip|vh)(\\s|$)/.test(cls)) continue;
        if (r.right > anchoReal + 1) {{
          var corta = cls.split(' ').slice(0, 2).join('.');
          out.push(el.tagName + (corta ? '.' + corta : '') + '[' + Math.round(r.right) + ']');
        }}
      }}
      document.title = 'DBG ancho=' + anchoReal + ' scroll=' + d.documentElement.scrollWidth +
        ' desbordes=' + out.length + ' :: ' + out.slice(0, 20).join(' ; ');
    }} catch (e) {{
      document.title = 'DBG error=' + e.message;
    }}
  }}, 900);
}});
</script>
</body></html>
"""


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/movil.py <archivo.html> [ancho] [captura.png]")
        return 1

    archivo = Path(sys.argv[1]).resolve()
    ancho = int(sys.argv[2]) if len(sys.argv) > 2 else 390
    captura = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None
    if not archivo.exists():
        print(f"no existe {archivo}")
        return 1

    chrome = next((c for c in CHROME_CANDIDATES if Path(c).exists()), None)
    if not chrome:
        print("no encontré Chrome ni Edge")
        return 1

    alto = 3400
    pagina = archivo.as_uri()
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        envoltorio = tmpdir / "envoltorio.html"
        envoltorio.write_text(
            ENVOLTORIO.format(src=pagina, ancho=ancho, alto=alto), encoding="utf-8")

        perfil = tmpdir / "prof"
        comunes = [
            chrome, "--headless=new", "--disable-gpu", "--no-first-run",
            "--allow-file-access-from-files", "--hide-scrollbars",
            f"--user-data-dir={perfil}", "--virtual-time-budget=12000",
        ]
        res = subprocess.run(
            comunes + [f"--window-size={ancho + 40},{alto}", "--dump-dom", envoltorio.as_uri()],
            capture_output=True, text=True, errors="replace")
        titulo = re.findall(r"<title>(.*?)</title>", res.stdout, re.S)

        if captura:
            captura.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                comunes + [f"--window-size={ancho},{alto}", f"--screenshot={captura}",
                           envoltorio.as_uri()],
                capture_output=True, text=True, errors="replace")

    print(f"\n{archivo.name} emulado a {ancho}px")
    print("-" * 70)
    if not (titulo and "DBG" in titulo[0]):
        print("  no pude leer el diagnóstico")
        return 1
    for parte in titulo[0].split("::"):
        print("  " + parte.strip().replace(" ; ", "\n     "))
    if captura:
        print(f"\n  captura: {captura}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
