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


def preparar_captura(path: Path, ancho: int = 1000) -> str:
    """Deja la captura del sitio dentro de dist/ y devuelve su ruta relativa.

    Usa Pillow si está disponible (redimensiona y comprime); si no —por ejemplo en el
    runner de GitHub Actions, que no lo trae— copia el archivo tal cual. Y si aun así
    falla, devuelve "" para que la portada caiga al iframe: la publicación nunca se
    cae por una captura."""
    destino_dir = DIST / "assets"
    try:
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / ("captura" + (path.suffix or ".jpg"))
        try:
            from PIL import Image
            im = Image.open(path).convert("RGB")
            if im.width > ancho:
                im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
            destino = destino_dir / "captura.jpg"
            im.save(destino, "JPEG", quality=74, optimize=True, progressive=True)
        except Exception:
            shutil.copyfile(path, destino)
        return f"assets/{destino.name}"
    except Exception:
        return ""


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
    """Home del lead, spec §2: el resultado primero.
    Orden exacto: H1 · subtítulo · preview del sitio nuevo + botón · números del
    diagnóstico · CTAs · nota técnica colapsable · pie con el «no gracias»."""
    meta = cfg.get("meta") or {}
    modelo = cfg.get("modelo") or {}
    preview_cfg = cfg.get("preview") or {}
    nombre = meta.get("nombre", "Lead")
    url = (modelo.get("url") or "").strip()

    # 3 · preview del sitio nuevo: captura si existe, iframe si no.
    captura = modelo.get("captura")
    p = (ROOT / captura) if captura else None
    rel = preparar_captura(p) if (p and p.exists()) else ""
    if rel:
        media = (f'<img class="shot-img" src="{rel}" '
                 f'alt="Vista del sitio nuevo de {html.escape(nombre)}">')
    elif url:
        media = (f'<iframe class="shot-frame" src="{html.escape(url)}" loading="lazy" '
                 f'title="Sitio nuevo de {html.escape(nombre)}"></iframe>')
    else:
        media = '<p class="nota">[falta configurar modelo.url en config.json]</p>'

    # 4 · los números del diagnóstico (4-5), en grande
    kpis = ((cfg.get("comparativo") or {}).get("kpis") or [])[:5]
    kpi_html = "".join(
        f'<div class="kpi"><span class="kpi__value">{html.escape(str(k.get("valor", "")))}</span>'
        f'<span class="kpi__label">{html.escape(str(k.get("label", "")))}</span></div>'
        for k in kpis
    )

    # 2 · subtítulo: el gancho del caso, si la config lo trae
    gancho = preview_cfg.get("gancho") or modelo.get("bajada") or ""
    boton_sitio = (f'<a class="btn btn-brand" href="{html.escape(url)}">Abrir el sitio nuevo &rarr;</a>'
                   if url else "")

    return f"""<!DOCTYPE html>
<html lang="es-AR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(nombre)} — Cómo se vería tu sitio</title>
{NOINDEX}
<style>
{css}
body {{ background: var(--surface-alt); }}
.portada {{ max-width: 62rem; margin: 0 auto; padding: var(--space-10) var(--space-6); }}
.portada h1 {{ font-size: var(--fs-3xl); margin-bottom: var(--space-3); }}
.portada .lead {{ font-size: var(--fs-lg); color: var(--ink-body); max-width: 46rem; }}
.shot {{ border:1px solid var(--line-default); border-radius:var(--radius-lg); overflow:hidden;
  margin: var(--space-6) 0 var(--space-4); background: var(--surface-default); box-shadow: var(--shadow-md); }}
.shot-img {{ display:block; width:100%; height:auto; }}
.shot-frame {{ display:block; width:100%; height:70vh; min-height:420px; border:0; background:#fff; }}
.nota {{ font-size: var(--fs-sm); color: var(--ink-muted); }}
footer.pie {{ margin-top: var(--space-12); padding-top: var(--space-4);
  border-top: 1px solid var(--line-default); font-size: var(--fs-sm); color: var(--ink-muted); }}
details.tecnica {{ margin-top: var(--space-6); font-size: var(--fs-sm); color: var(--ink-muted); }}
details.tecnica summary {{ cursor: pointer; }}
</style>
</head>
<body>
<main class="portada">
  <h1>{html.escape(nombre)} — Cómo se vería tu sitio</h1>
  <p class="lead">{html.escape(gancho)}</p>

  <div class="shot">{media}</div>
  <div class="cta-row">{boton_sitio}</div>

  <div class="kpi-row">{kpi_html}</div>

  <div class="cta-row">
    <a class="btn btn-ink" href="propuesta/">Ver la propuesta &rarr;</a>
    <a class="btn btn-light" href="informe/">Ver el informe &rarr;</a>
  </div>

  <details class="tecnica">
    <summary>Nota técnica: por qué esto no aparece en Google</summary>
    <p>
      Estas páginas están marcadas con <code>noindex</code> y el sitio las excluye por
      <code>robots.txt</code>. Mientras sea un preview, no compite en Google con el sitio real
      del profesional: el indexado se abre recién cuando el sitio se publique en su dominio.
    </p>
  </details>

  <footer class="pie">
    <p>Si preferís que no te escriba más, respondé «no gracias» y no vuelvo a contactarte.</p>
  </footer>
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
