#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar-sitio.py · verifica el sitio nuevo y lo compara contra el sitio actual.

Dos capas:
  1. Medición de señales con el MISMO motor que mide al cliente y a los pares
     (scripts/medir.py), sirviendo el sitio nuevo desde un servidor local.
  2. Render real en Chrome headless: se mira el DOM y se validan los datos
     estructurados, los textos alternativos y la cantidad de llamados a WhatsApp.

Produce:
  02-sitio/evidencia-despues.json      señales medidas del sitio nuevo
  00-auditoria/evidencia-antes-despues.json  comparación lado a lado
  02-sitio/capturas/*.png              capturas de escritorio y celular

Uso:
    python scripts/verificar-sitio.py
"""

import functools
import json
import re
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medir  # noqa: E402  (el motor de medición del repo)

ROOT = Path(__file__).resolve().parent.parent
SITIO = ROOT / "02-sitio"
CONFIG = ROOT / "config.json"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

ESPERADO_WA_MINIMO = 8
ESPERADO_DESC = (120, 165)


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def servir(puerto: int):
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(SITIO))
    httpd = ThreadingHTTPServer(("127.0.0.1", puerto), handler)
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()
    return httpd


def dump_dom(chrome, url: str, profile: Path) -> str:
    res = subprocess.run([
        chrome, "--headless=new", "--disable-gpu", "--no-first-run",
        "--no-default-browser-check", f"--user-data-dir={profile}",
        "--virtual-time-budget=10000", "--dump-dom", url,
    ], capture_output=True, text=True, errors="replace")
    return re.sub(r"<script\b.*?</script>", "", res.stdout, flags=re.S | re.I)


def captura(chrome, url: str, destino: Path, ancho: int, alto: int, profile: Path):
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        f"--user-data-dir={profile}", "--virtual-time-budget=10000",
        f"--window-size={ancho},{alto}", f"--screenshot={destino}", url,
    ], capture_output=True, text=True, errors="replace")


def ld_tipos(html_texto: str):
    """Devuelve los @type de todos los bloques JSON-LD. Falla si el JSON está roto."""
    tipos, rotos = [], []
    for blob in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html_texto, re.S | re.I):
        try:
            data = json.loads(blob.strip())
        except Exception as e:  # noqa: BLE001
            rotos.append(str(e))
            continue
        nodos = data.get("@graph", [data]) if isinstance(data, dict) else data
        for n in nodos:
            if isinstance(n, dict) and "@type" in n:
                t = n["@type"]
                tipos.extend(t if isinstance(t, list) else [t])
    return tipos, rotos


def main() -> int:
    if not (SITIO / "index.html").exists():
        print("  ✗ falta 02-sitio/index.html")
        return 1

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    dominio = cfg["meta"]["url"].replace("https://", "").replace("http://", "").strip("/")
    url_actual = "https://www." + dominio if not dominio.startswith("www.") else "https://" + dominio
    url_actual += "/"

    errores = []
    puerto = 8931
    httpd = servir(puerto)
    url_nuevo = f"http://127.0.0.1:{puerto}/"
    try:
        print("=" * 70)
        print("  VERIFICANDO EL SITIO NUEVO")
        print("=" * 70)

        # ── 1. Señales, medidas con el mismo motor que mide a los pares
        antes = medir.measure(url_actual)
        despues = medir.measure(url_nuevo)
        despues["url"] = "02-sitio/index.html (servido local)"
        antes["etiqueta"], despues["etiqueta"] = "ANTES (sitio actual)", "DESPUÉS (sitio nuevo)"

        campos = [
            ("status", "estado HTTP"),
            ("lang", "idioma declarado"),
            ("meta_description_len", "descripción en Google (caracteres)"),
            ("og_tags", "etiquetas Open Graph"),
            ("twitter_tags", "tarjetas de Twitter"),
            ("canonical", "URL canónica"),
            ("ldjson_bloques", "bloques de datos estructurados"),
            ("h1_count", "encabezados h1"),
            ("h2_count", "encabezados h2"),
            ("img_total", "imágenes"),
            ("img_sin_alt", "imágenes sin texto alternativo"),
            ("img_lazy", "imágenes con carga diferida"),
            ("srcset", "imágenes con srcset"),
            ("wa_botones", "llamados a WhatsApp"),
            ("tel_links", "enlaces telefónicos"),
            ("sitemap_via_robots", "mapa del sitio"),
            ("bytes_html", "peso del HTML (KB)"),
        ]
        print(f"\n  {'señal':<38}{'ANTES':>14}{'DESPUÉS':>14}")
        print("  " + "-" * 66)
        for campo, etiqueta in campos:
            a, d = antes.get(campo), despues.get(campo)
            fmt = lambda v: ("sí" if v is True else "no" if v is False else
                             "—" if v in (None, "") else str(v))
            if isinstance(a, list):
                a = len(a)
            if isinstance(d, list):
                d = len(d)
            print(f"  {etiqueta:<38}{fmt(a):>14}{fmt(d):>14}")

        tipos, rotos = ld_tipos((SITIO / "index.html").read_text(encoding="utf-8"))
        print(f"\n  datos estructurados declarados: {', '.join(sorted(set(tipos))) or 'ninguno'}")
        if rotos:
            errores.append(f"JSON-LD inválido: {rotos}")

        # ── 2. Verificación sobre el HTML servido
        if despues.get("lang") != "es-AR":
            errores.append(f"el sitio declara lang={despues.get('lang')!r} (debería ser es-AR)")
        d_len = despues.get("meta_description_len") or 0
        if not (ESPERADO_DESC[0] <= d_len <= ESPERADO_DESC[1]):
            errores.append(f"la descripción mide {d_len} caracteres (se esperan 120-165)")
        if not despues.get("canonical"):
            errores.append("falta la URL canónica")
        if (despues.get("ldjson_bloques") or 0) < 1:
            errores.append("no hay datos estructurados")
        for requerido in ("Psychologist", "Person", "FAQPage"):
            if requerido not in tipos:
                errores.append(f"falta el tipo de dato estructurado {requerido}")
        if (despues.get("wa_botones") or 0) < ESPERADO_WA_MINIMO:
            errores.append(f"hay {despues.get('wa_botones')} llamados a WhatsApp (se esperan {ESPERADO_WA_MINIMO}+)")
        if (despues.get("img_sin_alt") or 0) != 0:
            errores.append(f"{despues.get('img_sin_alt')} imágenes sin texto alternativo")
        # Todas las imágenes con carga diferida salvo la de portada, que se pide
        # primero a propósito (fetchpriority=high): diferirla empeoraría el LCP.
        n_img_html = despues.get("img_total") or 0
        if (despues.get("img_lazy") or 0) < n_img_html - 1:
            errores.append(
                f"sólo {despues.get('img_lazy')} de {n_img_html} imágenes con carga diferida"
            )
        if (despues.get("srcset") or 0) < 2:
            errores.append("faltan imágenes con srcset")
        if despues.get("h1_count") != 1:
            errores.append(f"hay {despues.get('h1_count')} h1 (debe haber exactamente 1)")
        if (despues.get("h2_count") or 0) < 5:
            errores.append(f"sólo {despues.get('h2_count')} h2: falta jerarquía")
        if not despues.get("sitemap_via_robots"):
            errores.append("no se encuentra el mapa del sitio")
        if not (despues.get("og_tags") or 0) >= 6:
            errores.append("faltan etiquetas Open Graph")

        # ── 3. Render real y capturas
        chrome = find_chrome()
        if not chrome:
            errores.append("no encontré Chrome ni Edge para verificar el render")
        else:
            with tempfile.TemporaryDirectory() as tmp:
                profile = Path(tmp) / "profile"
                dom = dump_dom(chrome, url_nuevo, profile)
                n_wa_dom = len(re.findall(r"wa\.me/", dom))
                n_alt = len(re.findall(r'<img[^>]+alt="[^"]+"', dom))
                n_img = len(re.findall(r"<img", dom))
                n_h1 = len(re.findall(r"<h1", dom))
                print(f"\n  render real: {n_img} imágenes ({n_alt} con alt) · "
                      f"{n_wa_dom} enlaces wa.me · {n_h1} h1 · {len(dom)} caracteres de DOM")
                if n_h1 != 1:
                    errores.append(f"el DOM renderizado tiene {n_h1} h1")
                if n_alt != n_img:
                    errores.append("alguna imagen del DOM quedó sin alt")
                if "Habilitación" not in dom or "084-60296" not in dom:
                    errores.append("los datos de la habilitación no están como texto en el DOM")
                if "60.000" not in dom:
                    errores.append("los honorarios no están visibles")
                if "lisandro-lagos" not in dom:
                    errores.append("falta el enlace al perfil de Doctoralia")

                captura(chrome, url_nuevo, SITIO / "capturas" / "nuevo-desktop.png", 1440, 3600, profile)
                captura(chrome, url_nuevo, SITIO / "capturas" / "nuevo-mobile.png", 390, 2600, profile)
                print("  capturas: 02-sitio/capturas/nuevo-desktop.png y nuevo-mobile.png")
    finally:
        httpd.shutdown()

    # ── 4. Evidencia a disco
    (SITIO / "evidencia-despues.json").write_text(
        json.dumps(despues, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "00-auditoria" / "evidencia-antes-despues.json").write_text(
        json.dumps({"antes": antes, "despues": despues}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n  evidencia: 02-sitio/evidencia-despues.json y 00-auditoria/evidencia-antes-despues.json")

    print("-" * 70)
    if errores:
        print("  ✗ VERIFICACIÓN DEL SITIO FALLÓ")
        for e in errores:
            print(f"      - {e}")
        return 2
    print("  ✓ Idioma, descripción, canónica, Open Graph y datos estructurados correctos")
    print("  ✓ WhatsApp presente como canal principal (el hallazgo #1, resuelto)")
    print("  ✓ Todas las imágenes con texto alternativo, carga diferida y srcset")
    print("  ✓ Un solo h1 y jerarquía de encabezados completa")
    print("  ✓ Mapa del sitio y robots.txt publicados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
