#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico-desborde.py · encuentra QUÉ elemento desborda el ancho en un ancho dado.

Abre la página en Chrome headless, ejecuta un script que recorre todos los
elementos y reporta los que se salen del ancho visible, y lo escribe en el
<title> para poder leerlo con --dump-dom.

Uso:
    python scripts/diagnostico-desborde.py 02-sitio/index.html 390
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

SONDA = """
<script>
window.addEventListener('load', function () {
  setTimeout(function () {
    var w = document.documentElement.clientWidth;
    var out = [];
    var nodos = document.querySelectorAll('body *');
    for (var i = 0; i < nodos.length; i++) {
      var el = nodos[i];
      var r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      // Los elementos de accesibilidad (.skip/.vh) viven fuera de pantalla a propósito.
      var cls = (typeof el.className === 'string' ? el.className : '');
      if (r.left < -100 || /(^|\s)(skip|vh)(\s|$)/.test(cls)) continue;
      if (r.right > w + 1) {
        var corta = cls.split(' ').slice(0, 2).join('.');
        out.push(el.tagName + (corta ? '.' + corta : '') + '[' + Math.round(r.left) + '→' + Math.round(r.right) + ']');
      }
    }
    document.title = 'DBG ancho=' + w + ' scroll=' + document.documentElement.scrollWidth +
      ' culpables=' + out.length + ' :: ' + out.slice(0, 30).join(' ; ');
  }, 600);
});
</script>
"""


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/diagnostico-desborde.py <archivo.html> [ancho]")
        return 1

    archivo = Path(sys.argv[1]).resolve()
    ancho = int(sys.argv[2]) if len(sys.argv) > 2 else 390
    if not archivo.exists():
        print(f"no existe {archivo}")
        return 1

    chrome = next((c for c in CHROME_CANDIDATES if Path(c).exists()), None)
    if not chrome:
        print("no encontré Chrome ni Edge")
        return 1

    html = archivo.read_text(encoding="utf-8")
    # El <base> hace que los recursos relativos (css, imágenes) sigan resolviéndose.
    sonda = f'<base href="{archivo.parent.as_uri()}/">' + SONDA
    html = html.replace("</body>", sonda + "</body>")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        copia = tmpdir / "debug.html"
        # Copia con los assets al lado para que el render sea real.
        for item in archivo.parent.iterdir():
            if item.is_dir() and item.name == "assets":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(tmpdir / "assets"),
                                str(item)], capture_output=True, text=True)
        copia.write_text(html, encoding="utf-8")
        res = subprocess.run([
            chrome, "--headless=new", "--disable-gpu", "--no-first-run",
            f"--user-data-dir={tmpdir / 'prof'}", "--virtual-time-budget=9000",
            f"--window-size={ancho},900", "--dump-dom", copia.as_uri(),
        ], capture_output=True, text=True, errors="replace")

    titulo = re.findall(r"<title>(.*?)</title>", res.stdout, re.S)
    print(f"\n{archivo.name} @ {ancho}px")
    print("-" * 70)
    if titulo and "DBG" in titulo[0]:
        for parte in titulo[0].split("::"):
            print("  " + parte.strip().replace(" ; ", "\n  "))
    else:
        print("  no pude leer el diagnóstico (la página no terminó de cargar)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
