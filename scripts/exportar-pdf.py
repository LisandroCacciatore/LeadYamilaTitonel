#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exportar-pdf.py · exporta la PROPUESTA a PDF con Chrome headless.

Por que existe: `generar.sh` regenera el HTML, pero hasta ahora nada exportaba
la propuesta a PDF — el informe lo hacia `verify-pdf.py`, la propuesta se
exportaba a mano. Resultado: el PDF quedaba viejo respecto al HTML sin que
nadie se enterara.

Uso:
    python scripts/exportar-pdf.py

Escribe  01-propuesta/propuesta-<slug>.pdf
"""
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROPUESTA = ROOT / "01-propuesta" / "propuesta.html"
CONFIG = ROOT / "config.json"

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def slug_de(cfg: dict) -> str:
    """Nombre del archivo PDF, sin tildes ni enies.

    Un PDF que se manda por mail con «adrián» en el nombre se rompe en el
    camino: clientes de correo, servidores y zips lo re-codifican distinto.
    ASCII siempre. Deriva de los dos primeros nombres del cliente.
    """
    meta = cfg.get("meta") or {}
    partes = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", meta.get("nombre") or "")
    partes = [p for p in partes if p.lower() not in ("lic", "dr", "dra", "sr", "sra")]
    base = "-".join(partes[:2]) or "propuesta"
    plano = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    return plano.lower() or "propuesta"


def main() -> int:
    if not PROPUESTA.exists():
        print("  ✗ falta 01-propuesta/propuesta.html — corré: python scripts/generate.py")
        return 1

    chrome = next((c for c in CHROME if Path(c).exists()), None)
    if not chrome:
        print("No encontré Chrome ni Edge.")
        return 1

    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    pdf = ROOT / "01-propuesta" / f"propuesta-{slug_de(cfg)}.pdf"

    pdf.unlink(missing_ok=True)
    perfil = ROOT / ".chrome-tmp-propuesta"
    subprocess.run([
        chrome, "--headless=new", "--disable-gpu", "--no-first-run",
        f"--user-data-dir={perfil}",
        # la propuesta ejecuta su JS (selector de modulos y total): hay que darle
        # tiempo a correr antes de imprimir.
        "--virtual-time-budget=14000",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf}",
        PROPUESTA.resolve().as_uri(),
    ], capture_output=True, text=True, errors="replace")
    shutil.rmtree(perfil, ignore_errors=True)

    if not pdf.exists():
        print("  ✗ Chrome no generó el PDF")
        return 1

    kb = pdf.stat().st_size // 1024
    print(f"  ✓ {pdf.relative_to(ROOT)}  ({kb} KB)")

    # El PDF tiene que reflejar el HTML actual: si quedó más viejo, algo se salteó.
    if pdf.stat().st_mtime < PROPUESTA.stat().st_mtime:
        print("  ✗ el PDF quedó más viejo que el HTML")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
