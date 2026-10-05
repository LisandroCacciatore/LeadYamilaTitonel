#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cotejar-promesas.py · §10 del spec v2.0: lo que la propuesta promete, el sitio nuevo
lo cumple visiblemente.

Regla dura del spec: *todo lo que la propuesta promete, el sitio nuevo lo cumple
visiblemente*. Si no lo cumple, la propuesta baja la promesa.

Cómo se verifica: se lee la promesa desde config.json (base + módulos) y se busca su
huella en el DOM **renderizado** del sitio publicado. Se renderiza y no se lee el HTML
crudo porque al menos uno de los sitios es una aplicación JavaScript: su HTML es un
molde vacío y daria falsos negativos.

Honestidad del reporte: lo que no se puede comprobar automáticamente NO se declara
cumplido; se imprime como «no verificable» con el motivo.

Uso:
    python scripts/cotejar-promesas.py [--json]
"""

import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _chrome():
    return next((c for c in CHROME if Path(c).exists()), None)


def dom_remoto(url: str) -> str:
    """El DOM ya ejecutado del sitio publicado (renderiza JavaScript)."""
    exe = _chrome()
    if not exe:
        return ""
    with tempfile.TemporaryDirectory() as td:
        try:
            out = subprocess.run(
                [exe, "--headless=new", "--disable-gpu", "--no-first-run",
                 f"--user-data-dir={td}", "--virtual-time-budget=15000",
                 "--dump-dom", url],
                capture_output=True, text=True, errors="replace", timeout=120)
            return out.stdout or ""
        except Exception:
            return ""


def trae(url: str):
    """GET simple: devuelve (código, texto). Para robots/sitemap."""
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def cuenta_nav(dom: str) -> int:
    m = re.search(r"<nav\b.*?</nav>", dom, re.S | re.I) or \
        re.search(r"<header\b.*?</header>", dom, re.S | re.I)
    return len(re.findall(r"<a\b", m.group(0), re.I)) if m else 0


def main() -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    modelo = cfg.get("modelo") or {}
    url = (modelo.get("url") or "").rstrip("/")
    if not url:
        print("no hay modelo.url en config.json")
        return 2

    # §10 protege al cliente de promesas que el sitio base no cumple: se revisan los
    # items de la base (bloqueantes). Los bullets de módulo describen lo que el módulo
    # hace SI se contrata, así que se informan aparte y no bloquean.
    base = cfg.get("base") or {}
    promesas = list(base.get("items") or cfg.get("baseItems") or [])
    promesas_modulo = []
    for m in cfg.get("modulos") or []:
        promesas_modulo += list(m.get("bullets") or [])

    print("=" * 70)
    print(f"  §10 · COTEJO DE PROMESAS · {cfg.get('meta', {}).get('nombre', '')}")
    print(f"  sitio nuevo: {url}")
    print("=" * 70)

    dom = dom_remoto(url)
    if not dom:
        print("  ✗ no pude renderizar el sitio nuevo: no cotejo nada")
        return 2
    print(f"  DOM renderizado: {len(dom)} bytes\n")

    cumplidas, incumplidas, no_verificables, informativas = [], [], [], []
    ya_chequeado = {}

    def evaluar(texto: str, dom: str):
        """Devuelve (estado, evidencia). estado: True cumple · False no cumple ·
        None no verificable automáticamente."""
        t = texto.lower()
        if "whatsapp" in t:
            n = len(re.findall(r"wa\.me", dom))
            return (n > 0 or "whatsapp" in t and "whatsapp" in dom.lower()), \
                f"{n} enlace(s) wa.me en el sitio publicado"
        if "mapa del sitio" in t or "sitemap" in t:
            cod, txt = trae(f"{url}/sitemap.xml")
            return cod == 200 and "<urlset" in txt, f"sitemap.xml responde {cod}"
        if "robots" in t:
            cod, _ = trae(f"{url}/robots.txt")
            return cod == 200, f"robots.txt responde {cod}"
        if "estructurad" in t or "schema" in t:
            n = len(re.findall(r"application/ld\+json", dom, re.I))
            return bool(n), f"{n} bloque(s) de datos estructurados"
        if "open graph" in t or "twitter card" in t:
            n = len(re.findall(r'property="og:', dom, re.I))
            return n >= 2, f"{n} etiqueta(s) Open Graph"
        # El alt de las imágenes va ANTES de la regla genérica de «descripción»: si no,
        # una promesa sobre imágenes se contesta con la meta description del documento
        # y queda marcada como cumplida sin haberla mirado.
        if "imágenes" in t or "imagen" in t or re.search(r"\bal\b|\balt\b", t):
            n = len(re.findall(r'<img[^>]+alt="[^"]{3,}"', dom, re.I))
            tot = len(re.findall(r"<img", dom, re.I))
            return (tot > 0 and n == tot), f"{n} de {tot} imágenes con texto alternativo"
        # «Cada artículo con su título, su descripción…» habla de los artículos del blog,
        # no de la meta del documento: contestarlo con la meta description lo marcaba
        # cumplido sin haber mirado ningún artículo.
        if re.search(r"art[íi]culo", t):
            return None, "la descripción por artículo se verifica en el blog, no en la home"
        if "descripción" in t or "descripcion" in t or "títulos" in t:
            m = re.search(r'name="description"[^>]+content="([^"]{10,})"', dom, re.I)
            return bool(m), (f"descripción de {len(m.group(1))} caracteres" if m
                             else "sin meta description con contenido")
        if "idioma" in t:
            m = re.search(r'<html[^>]*\blang="([^"]+)"', dom, re.I)
            return bool(m and m.group(1).lower().startswith("es")), \
                f'lang="{m.group(1) if m else "sin atributo"}"'
        # «etiquetas … asociadas a cada campo» es <label> de formulario; «etiquetas por
        # tema» son etiquetas de contenido. Confundirlas marcaba en falso.
        if "etiquetas" in t and ("campo" in t or "formulario" in t):
            n = len(re.findall(r"<label\b", dom, re.I))
            return bool(n), f"{n} etiqueta(s) <label> en el formulario del sitio"
        if "etiquetas" in t:
            n = len(re.findall(r'class="[^"]*\btag\b', dom, re.I))
            return bool(n), f"{n} elemento(s) de etiqueta de tema"
        m = re.search(r"\b(\d+)\s+secciones", t)
        if m:
            n = cuenta_nav(dom)
            return n >= int(m.group(1)), f"{n} enlaces en la navegación (promete {m.group(1)})"
        if "fotos reales" in t or "foto" in t:
            n = len(re.findall(r"<img", dom, re.I))
            return bool(n), f"{n} imágenes en el sitio publicado"
        if "habilitación" in t or "matrícula" in t:
            mat = (cfg.get("meta") or {}).get("matricula") or ""
            num = re.search(r"\d{3,}", mat)
            return (num and num.group(0) in dom), \
                (f"el número de matrícula {num.group(0)} aparece en el sitio" if num
                 else "no hay matrícula en la config para cotejar")
        if "contraste" in t or "4,5:1" in t:
            return None, ("el contraste se mide sobre los colores computados: se verifica "
                          "con scripts/verificar-sitio.py sobre el sitio local")
        if "dominio" in t:
            return None, "el preview vive en github.io: apuntar el dominio pasa al publicar"
        if "sin costo" in t or "sin licencia" in t or "sin plugins" in t:
            return None, "es una condición contractual, no una huella en el sitio"
        return None, "no hay regla automática para esta promesa"

    def registrar(texto, destino_fallo):
        if texto in ya_chequeado:
            estado, ev = ya_chequeado[texto]
        else:
            estado, ev = evaluar(texto, dom)
            ya_chequeado[texto] = (estado, ev)
        if estado is None:
            no_verificables.append((texto, ev))
        elif estado:
            cumplidas.append((texto, ev))
        else:
            destino_fallo.append((texto, ev))

    for p in promesas:
        registrar(p, incumplidas)
    for p in promesas_modulo:
        registrar(p, informativas)

    for titulo, items in (("CUMPLIDAS", cumplidas), ("INCUMPLIDAS", incumplidas),
                          ("NO VERIFICABLES AUTOMÁTICAMENTE", no_verificables),
                          ("PROMESAS DE MÓDULO (informativas: se cumplen si se contrata)",
                           informativas)):
        if not items:
            continue
        print(f"  {titulo} ({len(items)}):")
        for texto, ev in items:
            marca = {"CUMPLIDAS": "✓", "INCUMPLIDAS": "✗"}.get(titulo, "·")
            print(f"    {marca} {texto[:76]}")
            print(f"        {ev}")
        print()

    if incumplidas:
        print("  ✗ §10 NO SE CUMPLE: la propuesta baja estas promesas al nivel de lo "
              "que el sitio sí hace.")
        return 1
    print("  ✓ §10 sin promesas incumplidas (las no verificables quedan declaradas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
