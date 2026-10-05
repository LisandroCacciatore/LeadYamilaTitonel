#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capturar.py · captura la evidencia visual: el sitio actual y el sitio nuevo.

Deja dos cosas:
  1. Capturas completas (evidencia): escritorio y celular, de los dos sitios.
  2. Recortes de portada para la propuesta: los primeros 1500px, en JPEG y 900px
     de ancho, que es lo que se embebe en 01-propuesta/propuesta.html.

El celular se captura con el truco del iframe (ver scripts/movil.py): Chrome en
Windows no acepta ventanas de menos de ~500px, así que --window-size no sirve.

Uso:
    python scripts/capturar.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from movil import CHROME_CANDIDATES, ENVOLTORIO  # noqa: E402

AUD = ROOT / "00-auditoria" / "capturas"
SIT = ROOT / "02-sitio" / "capturas"
URL_ACTUAL = "https://www.liclisandrolagos.com/"
ALTO_DESKTOP = 3400
ALTO_RECORTE = 1500
ANCHO_RECORTE = 900


def chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    raise SystemExit("No encontré Chrome ni Edge.")


def comunes(ch: str, perfil: Path):
    return [ch, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
            "--allow-file-access-from-files", f"--user-data-dir={perfil}",
            "--virtual-time-budget=13000"]


def capturar_escritorio(ch: str, url: str, destino: Path, perfil: Path, ancho=1440):
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(comunes(ch, perfil) + [f"--window-size={ancho},{ALTO_DESKTOP}",
                                          f"--screenshot={destino}", url],
                   capture_output=True, text=True, errors="replace")


def capturar_movil(ch: str, archivo: Path, destino: Path, tmp: Path, ancho=390):
    """Emula el ancho con un iframe, porque la ventana de Chrome no baja de ~500px."""
    envoltorio = tmp / f"envoltorio-{ancho}.html"
    envoltorio.write_text(
        ENVOLTORIO.format(src=archivo.as_uri(), ancho=ancho, alto=ALTO_DESKTOP),
        encoding="utf-8")
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(comunes(ch, tmp / f"prof-{ancho}") +
                   [f"--window-size={ancho},{ALTO_DESKTOP}", f"--screenshot={destino}",
                    envoltorio.as_uri()],
                   capture_output=True, text=True, errors="replace")


def recorte_portada(origen: Path, destino: Path, alto=ALTO_RECORTE, ancho=ANCHO_RECORTE):
    im = Image.open(origen).convert("RGB")
    im = im.crop((0, 0, im.width, min(alto, im.height)))
    if im.width > ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, "JPEG", quality=78, optimize=True, progressive=True)
    return im.size


def main() -> int:
    ch = chrome()
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        print("Capturando el sitio actual…")
        capturar_escritorio(ch, URL_ACTUAL, AUD / "actual-desktop.png", tmp / "p1")
        print("Capturando el sitio nuevo…")
        capturar_escritorio(ch, (ROOT / "02-sitio" / "index.html").as_uri(),
                            SIT / "nuevo-desktop.png", tmp / "p2")
        capturar_movil(ch, ROOT / "02-sitio" / "index.html",
                       SIT / "nuevo-mobile.png", tmp, 390)

    print("Recortando portadas para la propuesta…")
    a = recorte_portada(AUD / "actual-desktop.png", AUD / "antes-portada.jpg")
    d = recorte_portada(SIT / "nuevo-desktop.png", SIT / "despues-portada.jpg")
    print(f"  antes-portada.jpg    {a[0]}x{a[1]}  {(AUD / 'antes-portada.jpg').stat().st_size // 1024} KB")
    print(f"  despues-portada.jpg  {d[0]}x{d[1]}  {(SIT / 'despues-portada.jpg').stat().st_size // 1024} KB")

    for f in ("actual-desktop.png", "actual-mobile.png", "antes-portada.jpg"):
        p = AUD / f
        if p.exists():
            print(f"  {p.relative_to(ROOT)}  {p.stat().st_size // 1024} KB")
    for f in ("nuevo-desktop.png", "nuevo-mobile.png", "despues-portada.jpg"):
        p = SIT / f
        if p.exists():
            print(f"  {p.relative_to(ROOT)}  {p.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
