"""Mide la condición mobile de §8.1 sin depender de un navegador instrumentado.

Inyecta un script que lee los estilos ya computados a 375 px y los escribe en el DOM;
después Chrome headless los devuelve con --dump-dom. Así la verificación es una
medición real (getComputedStyle sobre el layout de 375 px), no una inspección del CSS.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

SONDA = """
<script>
window.addEventListener('load', function () {
  var out = {};
  var t = document.querySelector('.compare-table');
  var b = document.querySelector('.comp-bullets');
  out.hayTabla = !!t;
  out.hayBullets = !!b;
  if (!t) { out.err = b ? null : 'ni tabla ni bullets (§6.2)'; }
  else {
    var th = t.querySelector('thead');
    var tr = t.querySelector('tbody tr');
    var td = t.querySelector('tbody td:not(:first-child)');
    out.displayTabla = getComputedStyle(t).display;
    out.displayThead = th ? getComputedStyle(th).display : null;
    out.displayFila = tr ? getComputedStyle(tr).display : null;
    out.etiquetaCelda = td ? getComputedStyle(td, '::before').content : null;
    out.dataCol = td ? td.getAttribute('data-col') : null;
    out.desbordePx = document.documentElement.scrollWidth - window.innerWidth;
  }
  out.vista = window.innerWidth;
  var d = document.createElement('div');
  d.id = 'sonda-mobile';
  d.textContent = 'SONDA ' + JSON.stringify(out);
  document.body.appendChild(d);
});
</script>
</body>
"""


def medir(propuesta: Path, ancho: int = 375, alto: int = 812) -> dict:
    html = propuesta.read_text(encoding="utf-8")
    if "</body>" not in html:
        return {"err": "sin </body>"}
    with tempfile.TemporaryDirectory() as td:
        copia = Path(td) / "sonda.html"
        copia.write_text(html.replace("</body>", SONDA, 1), encoding="utf-8")
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
               f"--user-data-dir={td}/perfil", f"--window-size={ancho},{alto}",
               "--virtual-time-budget=9000", "--dump-dom", copia.as_uri()]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 errors="replace", timeout=120).stdout
        except Exception as exc:
            return {"err": f"no pude renderizar: {exc}"}
    m = re.search(r"SONDA (\{.*?\})</div>", out, re.S)
    if not m:
        return {"err": "la sonda no escribió su resultado"}
    import json
    return json.loads(m.group(1))


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        p = Path(ruta)
        r = medir(p)
        print(f"── {p.parent.parent.name}")
        if not r.get("hayTabla"):
            if r.get("hayBullets"):
                print("   ✓ no hay tabla: el comparativo va en 3 bullets (§6.2), "
                      "así que la condición mobile no aplica")
            else:
                print("   ✗ no hay comparativo (ni tabla ni bullets)")
            continue
        ok = (r.get("displayTabla") == "block" and r.get("displayThead") == "none"
              and r.get("displayFila") == "block" and (r.get("desbordePx") or 0) <= 1
              and r.get("dataCol"))
        print(f"   vista {r.get('vista')} px · tabla={r.get('displayTabla')} · "
              f"thead={r.get('displayThead')} · fila={r.get('displayFila')} · "
              f"desborde={r.get('desbordePx')} px")
        print(f"   etiqueta de celda: {r.get('etiquetaCelda')} (data-col={r.get('dataCol')})")
        print("   " + ("✓ se convierte en bullets, sin desborde lateral (§8.1-4)"
                       if ok else "✗ NO cumple la condición mobile"))
