#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
armar-dist.py · arma el sitio que se publica en GitHub Pages, para cualquier lead.

Junta las piezas disponibles en un solo sitio navegable:

    dist/
    ├── index.html        portada de entrega: las piezas enlazadas
    ├── propuesta/        la propuesta comercial
    ├── informe/          el informe de auditoría
    ├── sitio/            el sitio nuevo, si ya está construido (con sus assets)
    ├── robots.txt        Disallow: /  — el preview NO se indexa
    └── .nojekyll         para que Pages no procese nada con Jekyll

Regla de oro: **el preview va con noindex**. Mientras tenga datos provistos por el
cliente (teléfono, dirección, opiniones) y esté publicado en un dominio que no es el
suyo, no puede competir en Google con el sitio real. El indexado se abre recién cuando
el sitio se publica en el dominio del cliente.

Eso se aplica acá, no en los archivos fuente: en `02-sitio/index.html` la etiqueta
sigue diciendo `index, follow`, porque ése es el archivo que va al dominio del cliente.

Todo lo que cambia entre clientes sale de config.json. El sitio es opcional: hay leads
cuya propuesta todavía no incluye un sitio nuevo, y publicar sólo la propuesta y el
informe es un entregable válido.

Uso:
    python scripts/armar-dist.py
"""

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BRAND_CSS = ROOT / "brand" / "brand.css"
CONFIG = ROOT / "config.json"

NOINDEX = '<meta name="robots" content="noindex, nofollow">'
ARCHIVO = "index.html"


def brand_override(cfg: dict) -> str:
    """El color del cliente pisa el default del sistema, igual que en las piezas."""
    color = ((cfg.get("branding") or {}).get("colorPrimario") or "").strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", color):
        return ""

    def mezclar(hexc: str, hacia: str, t: float) -> str:
        a = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(hacia[i:i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{int(round(x + (y - x) * t)):02X}" for x, y in zip(a, b))

    return (
        "\n/* Identidad del cliente */\n:root {\n"
        f"  --brand-default: {color};\n"
        f"  --brand-hover:   {mezclar(color, '#000000', 0.16)};\n"
        f"  --brand-soft:    {mezclar(color, '#FFFFFF', 0.92)};\n"
        "}\n"
    )


def piezas(cfg: dict) -> list:
    """Las piezas que este lead realmente tiene. El orden es el de la portada."""
    n_hall = len(cfg.get("hallazgos", []))
    preview = cfg.get("preview") or {}
    lista = [
        {
            "slug": "propuesta",
            "titulo": preview.get("tituloPropuesta") or "Propuesta comercial",
            "bajada": preview.get("bajadaPropuesta") or
                      "Qué se midió, qué se encontró y qué se propone. Con selector de "
                      "bloques: el total se recalcula al tildar.",
            "origen": ROOT / "01-propuesta" / "propuesta.html",
        },
    ]
    sitio = ROOT / "02-sitio" / "index.html"
    if sitio.exists():
        lista.append({
            "slug": "sitio",
            "titulo": preview.get("tituloSitio") or "Sitio nuevo",
            "bajada": preview.get("bajadaSitio") or
                      "El sitio funcionando: datos reales, las fotos propias y el contacto "
                      "directo en todas las secciones.",
            "origen": sitio,
        })
    lista.append({
        "slug": "informe",
        "titulo": preview.get("tituloInforme") or "Informe de auditoría",
        "bajada": preview.get("bajadaInforme") or
                  f"Documento A4 con los {n_hall} hallazgos medidos, el comparativo y el "
                  "alcance de la revisión.",
        "origen": ROOT / "00-auditoria" / "informe.html",
    })
    return lista


def con_noindex(texto: str) -> str:
    """Fuerza noindex en el HTML que se publica, sin tocar el archivo fuente."""
    if re.search(r'<meta[^>]+name=["\']robots["\']', texto, re.I):
        return re.sub(r'<meta[^>]+name=["\']robots["\'][^>]*>', NOINDEX, texto, count=1, flags=re.I)
    return re.sub(r"(<head[^>]*>)", r"\1\n" + NOINDEX, texto, count=1, flags=re.I)


def portada(css: str, cfg: dict, lista: list) -> str:
    meta = cfg.get("meta") or {}
    modelo = cfg.get("modelo") or {}
    nombre = meta.get("nombre", "Lead")
    fecha = meta.get("fecha", "")
    tarjetas = "".join(
        f"""
        <a class="tarjeta" href="{p['slug']}/">
          <span class="tarjeta__n">{i:02d}</span>
          <h2>{html.escape(p['titulo'])}</h2>
          <p>{html.escape(p['bajada'])}</p>
          <span class="tarjeta__ir">Abrir &rarr;</span>
        </a>"""
        for i, p in enumerate(lista, start=1)
    )
    # La página modelo suele vivir en otro dominio (el sitio ya construido): se
    # enlaza directo y marcada como externa, para que no se confunda con el preview.
    if (modelo.get("url") or "").strip():
        n = len(lista) + 1
        tarjetas += f"""
        <a class="tarjeta tarjeta--modelo" href="{html.escape(modelo['url'])}" target="_blank" rel="noopener">
          <span class="tarjeta__n">{n:02d} · externo</span>
          <h2>{html.escape(modelo.get('titulo') or 'Página modelo')}</h2>
          <p>{html.escape(modelo.get('bajada') or '')}</p>
          <span class="tarjeta__ir">{html.escape(modelo.get('cta') or 'Abrir la página modelo')} &nearr;</span>
        </a>"""
    return f"""<!DOCTYPE html>
<html lang="es-AR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lead {html.escape(nombre)} — auditoría y propuesta</title>
{NOINDEX}
<style>
{css}
/* Portada de entrega: sólo disposición, los colores salen de la marca. */
body {{ background: var(--surface-alt); }}
.portada {{ max-width: 60rem; margin: 0 auto; padding: var(--space-12) var(--space-6); }}
.portada h1 {{ font-size: var(--fs-3xl); margin-bottom: var(--space-3); }}
.portada .lead {{ font-size: var(--fs-lg); color: var(--ink-body); max-width: 44rem; }}
.sello {{ display: inline-block; font-size: .72rem; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; background: rgba(220,53,69,.10); color: #A71D2A;
  border-radius: var(--radius-sm); padding: 4px 8px; margin-bottom: var(--space-4); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
  gap: var(--space-4); margin: var(--space-8) 0; }}
.tarjeta {{ display: block; background: var(--surface-default); border: 1px solid var(--line-default);
  border-radius: var(--radius-lg); padding: var(--space-5); text-decoration: none;
  transition: border-color .2s ease, box-shadow .2s ease; }}
.tarjeta:hover {{ border-color: var(--brand-default); box-shadow: var(--shadow-md); }}
.tarjeta__n {{ font-size: .72rem; font-weight: 700; letter-spacing: .1em; color: var(--brand-default); }}
.tarjeta h2 {{ font-size: var(--fs-xl); margin: var(--space-1) 0 var(--space-2); }}
.tarjeta p {{ font-size: var(--fs-sm); color: var(--ink-body); }}
.tarjeta__ir {{ font-size: var(--fs-sm); font-weight: 700; color: var(--brand-default); }}
.tarjeta--modelo {{ border-color: var(--brand-default); }}
.tarjeta--modelo .tarjeta__n {{ color: var(--ink-muted); }}
.nota {{ font-size: var(--fs-sm); color: var(--ink-muted); border-top: 1px solid var(--line-default);
  padding-top: var(--space-4); }}
</style>
</head>
<body>
<main class="portada">
  <span class="sello">Preview con indexado bloqueado</span>
  <h1>{html.escape(nombre)}</h1>
  <p class="lead">
    Auditoría medida y propuesta comercial. Todo lo que sigue está medido sobre el sitio y
    los perfiles públicos del profesional: cada número se puede reproducir con los comandos
    que figuran en el informe.
  </p>

  <div class="grid">{tarjetas}</div>

  <p class="nota">
    Estas páginas están marcadas con <code>noindex</code> y el sitio las excluye por
    <code>robots.txt</code>: mientras sea un preview, no compite en Google con el sitio real
    del profesional. El indexado se abre recién cuando el sitio se publique en su dominio.
    Medición del {html.escape(fecha)}.
  </p>
</main>
</body>
</html>
"""


def main() -> int:
    if not CONFIG.exists():
        print("ERROR: falta config.json")
        return 1
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    lista = piezas(cfg)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    if not BRAND_CSS.exists():
        print(f"ERROR: falta {BRAND_CSS.relative_to(ROOT)}")
        return 1

    print(f"{'pieza':<14}{'archivos':>10}{'KB':>8}")
    print("-" * 34)

    for pieza in lista:
        origen, slug = pieza["origen"], pieza["slug"]
        if not origen.exists():
            print(f"  ✗ falta {origen.relative_to(ROOT)} — generá las piezas primero")
            return 1

        destino_dir = DIST / slug
        destino_dir.mkdir(parents=True)

        texto = con_noindex(origen.read_text(encoding="utf-8"))
        (destino_dir / ARCHIVO).write_text(texto, encoding="utf-8")

        # El sitio arrastra su carpeta de assets; las otras piezas son autocontenidas.
        assets = origen.parent / "assets"
        if assets.is_dir():
            shutil.copytree(assets, destino_dir / "assets")

        archivos = sum(1 for _ in destino_dir.rglob("*") if _.is_file())
        kb = sum(f.stat().st_size for f in destino_dir.rglob("*") if f.is_file()) // 1024
        print(f"{slug:<14}{archivos:>10}{kb:>8}")

    css = BRAND_CSS.read_text(encoding="utf-8") + brand_override(cfg)
    (DIST / "index.html").write_text(portada(css, cfg, lista), encoding="utf-8")
    (DIST / "robots.txt").write_text(
        "# Preview: no se indexa mientras sea una maqueta con datos del cliente.\n"
        "User-agent: *\n"
        "Disallow: /\n",
        encoding="utf-8",
    )
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    # Verificación: ninguna página publicada puede quedar indexable.
    errores = []
    for f in DIST.rglob("*.html"):
        t = f.read_text(encoding="utf-8")
        if "noindex" not in t:
            errores.append(f"{f.relative_to(DIST)} no tiene noindex")
        if re.search(r'content=["\']index,\s*follow', t, re.I):
            errores.append(f"{f.relative_to(DIST)} todavía dice index, follow")
    if "Disallow: /" not in (DIST / "robots.txt").read_text(encoding="utf-8"):
        errores.append("dist/robots.txt no bloquea el indexado")
    for pieza in lista:
        if not (DIST / pieza["slug"] / ARCHIVO).exists():
            errores.append(f"falta {pieza['slug']}/{ARCHIVO}")
    if (DIST / "sitio").is_dir() and not (DIST / "sitio" / "assets" / "img").is_dir():
        errores.append("el sitio quedó sin sus assets")

    print("-" * 34)
    total = sum(1 for f in DIST.rglob("*") if f.is_file())
    kb = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file()) // 1024
    print(f"dist/: {total} archivos, {kb} KB  ({len(lista)} piezas)")
    if errores:
        print("  ✗ EL PREVIEW QUEDARÍA INDEXABLE O INCOMPLETO")
        for e in errores:
            print(f"      - {e}")
        return 2
    print(f"  ✓ Las {len(lista)} piezas están y todas quedan con noindex")
    print("  ✓ robots.txt del preview bloquea el indexado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
