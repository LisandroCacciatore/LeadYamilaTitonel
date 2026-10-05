#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar-assets.py · prepara las imágenes reales del cliente para el sitio nuevo.

Fuente: 00-auditoria/fuentes/*.jpg — las fotos y el certificado que el propio
profesional publica hoy en su sitio y en su perfil de Doctoralia.
No se genera, no se inventa y no se retoca ninguna imagen: sólo se redimensiona
y se optimiza, y nunca se agranda una imagen más allá de su tamaño original
(agrandar degrada y además falsea la evidencia).

Produce 02-sitio/assets/img/ con una variante por ancho útil y el Open Graph.

Uso:
    python scripts/preparar-assets.py
"""

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
FUENTES = ROOT / "00-auditoria" / "fuentes"
DESTINO = ROOT / "02-sitio" / "assets" / "img"

# (origen, nombre destino, anchos deseados en px)
TRABAJOS = [
    ("foto-a.jpg", "consultorio-principal", [1280]),
    ("a4-1.jpg", "consultorio-biblioteca", [640, 1200]),
    ("a4-2.jpg", "consultorio-lectura", [640, 1200]),
    ("perfil.jpg", "consultorio-detalle", [520]),
    ("a4-3.jpg", "habilitacion", [640, 1200]),
]


def main() -> int:
    if not FUENTES.exists():
        print(f"ERROR: no existe {FUENTES.relative_to(ROOT)}")
        return 1

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir(parents=True, exist_ok=True)

    total = 0
    print(f"{'archivo':<36}{'px':>12}{'KB':>7}")
    print("-" * 55)

    for origen, nombre, anchos in TRABAJOS:
        src = FUENTES / origen
        if not src.exists():
            print(f"  ✗ falta {origen}")
            continue

        base = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        # Sólo anchos que no obliguen a agrandar. El más chico nunca se descarta.
        utiles = sorted({min(w, base.width) for w in anchos})

        for i, w in enumerate(utiles):
            im = base
            if im.width > w:
                im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            sufijo = "" if i == 0 else f"@{w}w"
            out = DESTINO / f"{nombre}{sufijo}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            im.save(out, "JPEG", quality=76, optimize=True, progressive=True)
            total += 1
            print(f"{out.name:<36}{im.width:>5}x{im.height:<6}{out.stat().st_size // 1024:>4}")

    # Open Graph: 1200x630 recortado al centro de la foto principal.
    hero = FUENTES / "foto-a.jpg"
    if hero.exists():
        im = ImageOps.exif_transpose(Image.open(hero)).convert("RGB")
        im = ImageOps.fit(im, (1200, 630), Image.LANCZOS, centering=(0.5, 0.45))
        out = DESTINO / "og.jpg"
        im.save(out, "JPEG", quality=80, optimize=True, progressive=True)
        total += 1
        print(f"{out.name:<36}{im.width:>5}x{im.height:<6}{out.stat().st_size // 1024:>4}")

    print("-" * 55)
    print(f"  {total} archivos en {DESTINO.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
