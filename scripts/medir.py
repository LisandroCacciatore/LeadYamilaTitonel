#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
medir.py · motor de medición de la auditoría.

Mide SEÑALES VERIFICABLES del HTML servido de una URL y de sus recursos
convencionales (robots.txt, sitemap.xml). No estima: cuenta.

Uso:
    python scripts/medir.py https://www.liclisandrolagos.com/            # una URL
    python scripts/medir.py --pares pares.txt --out evidencia.json       # lista + salida

Regla de la casa: cada número que entra al informe sale de acá.
Si algo no se pudo medir, queda en null y se declara [NO VERIFICADO].
"""

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=30):
    """Devuelve (status, body, final_url, headers). Nunca levanta: devuelve el error."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.5",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return r.status, raw.decode(enc, errors="replace"), r.geturl(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", url, {}
    except Exception as e:  # DNS, TLS, timeout
        return None, f"__ERR__ {type(e).__name__}: {e}", url, {}


def head_ok(url, timeout=20):
    st, _, _, _ = fetch(url, timeout)
    return st


def count(rx, s):
    return len(re.findall(rx, s, re.I))


def measure(url):
    """Mide una URL. Devuelve dict con cada señal y su valor crudo."""
    t0 = time.time()
    status, body, final, headers = fetch(url)
    ms = int((time.time() - t0) * 1000)
    out = {
        "url": url,
        "url_final": final,
        "status": status,
        "error": None,
        "ms_respuesta": ms,
        "bytes_html": None,
        "https": url.startswith("https"),
    }
    if status is None or body.startswith("__ERR__"):
        out["error"] = body or "sin respuesta"
        return out

    kb = round(len(body.encode("utf-8", errors="replace")) / 1024, 1)
    out["bytes_html"] = kb

    base = re.match(r"^(https?://[^/]+)", final or url)
    root = base.group(1) if base else url.rstrip("/")

    desc = re.findall(r'<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', body, re.I)
    if not desc:
        desc = re.findall(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', body, re.I)

    imgs = re.findall(r"<img\b[^>]*>", body, re.I)
    imgs_sin_alt = [t for t in imgs if not re.search(r'alt=["\'][^"\']+["\']', t, re.I)]

    ld = re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', body, re.S | re.I)
    ld_tipos = []
    for blob in ld:
        try:
            data = json.loads(blob.strip())
        except Exception:
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict):
                if "@graph" in node:
                    for sub in node["@graph"]:
                        if isinstance(sub, dict) and "@type" in sub:
                            ld_tipos.append(str(sub["@type"]))
                elif "@type" in node:
                    ld_tipos.append(str(node["@type"]))

    h1 = re.findall(r"<h1\b[^>]*>(.*?)</h1>", body, re.S | re.I)

    wa = sorted(set(re.findall(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=|whatsapp://send\?phone=)(\+?\d[\d\-\s]*)", body, re.I)))
    wa_btn = count(r"wa\.me/", body)
    tel = sorted(set(re.findall(r'href=["\']tel:([^"\']+)["\']', body, re.I)))
    mail = sorted(set(re.findall(r'mailto:([^"\'>\s]+)', body, re.I)))

    out.update({
        "lang": (re.findall(r'<html[^>]*\blang=["\']([^"\']*)["\']', body, re.I) or [None])[0],
        "title": (re.findall(r"<title[^>]*>(.*?)</title>", body, re.S | re.I) or [None])[0],
        "title_len": len(re.sub(r"\s+", " ", (re.findall(r"<title[^>]*>(.*?)</title>", body, re.S | re.I) or [""])[0]).strip()),
        "meta_description": (desc[0] if desc else None),
        "meta_description_len": len(desc[0].strip()) if desc else 0,
        "og_tags": count(r'property=["\']og:', body),
        "twitter_tags": count(r'name=["\']twitter:', body),
        "canonical": (re.findall(r'rel=["\']canonical["\'][^>]*href=["\']([^"\']*)["\']', body, re.I)
                      or re.findall(r'href=["\']([^"\']*)["\'][^>]*rel=["\']canonical["\']', body, re.I)
                      or [None])[0],
        "hreflang": count(r"hreflang", body),
        "robots_meta": (re.findall(r'name=["\']robots["\'][^>]*content=["\']([^"\']*)["\']', body, re.I) or [None])[0],
        "ldjson_bloques": len(ld),
        "ldjson_tipos": ld_tipos,
        "itemprop": count(r"itemprop=", body),
        "h1_count": len(h1),
        "h1_texto": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h1[0])).strip()[:120] if h1 else None,
        "h2_count": count(r"<h2\b", body),
        "img_total": len(imgs),
        "img_sin_alt": len(imgs_sin_alt),
        "img_lazy": count(r'loading=["\']lazy["\']', body),
        "srcset": count(r"srcset=", body),
        "wa_links": wa,
        "wa_botones": wa_btn,
        "whatsapp_menciones": count(r"whatsapp", body),
        "tel_links": tel,
        "mailto": mail,
        "forms": count(r"<form\b", body),
        "iframes": count(r"<iframe\b", body),
        "precios": sorted(set(re.findall(r"([\d]{2}\.?[\d]{3})\s*\$", body)))[:6],
        "viewport": bool(re.search(r'name=["\']viewport["\']', body, re.I)),
        "generator": (re.findall(r'name=["\']generator["\'][^>]*content=["\']([^"\']*)["\']', body, re.I) or [None])[0],
        "plataforma_docplanner": bool(re.search(r"docplanner|doctoralia", body, re.I)),
        "footer_copyright": (re.findall(r"©\s*(\d{4})", body) or [None])[0],
        "server": headers.get("Server"),
    })

    # Recursos convencionales: se prueban, no se suponen.
    out["robots_txt"] = head_ok(root + "/robots.txt")
    out["sitemap_xml"] = head_ok(root + "/sitemap.xml")
    out["sitemap_via_robots"] = (
        out["sitemap_xml"] == 200
        or (out["robots_txt"] == 200 and _robots_declara_sitemap(root))
    )
    return out


def _robots_declara_sitemap(root):
    st, body, _, _ = fetch(root + "/robots.txt")
    return st == 200 and bool(re.search(r"^\s*sitemap:", body, re.I | re.M))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*", help="URLs a medir")
    ap.add_argument("--pares", help="archivo con una URL por línea (se etiqueta por línea #comentario)")
    ap.add_argument("--out", help="ruta del JSON de salida")
    args = ap.parse_args()

    objetivos = []
    for u in args.urls:
        objetivos.append(("cliente", u))
    if args.pares:
        with open(args.pares, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    etiqueta, u = line.split("|", 1)
                    objetivos.append((etiqueta.strip(), u.strip()))
                else:
                    objetivos.append((line, line))

    if not objetivos:
        print("Nada que medir. Pasá URLs o --pares archivo.txt")
        return 1

    res = {}
    for etiqueta, url in objetivos:
        r = measure(url)
        r["etiqueta"] = etiqueta
        res[etiqueta if etiqueta not in res else url] = r
        print(f"{etiqueta:<34} {str(r.get('status')):>4}  "
              f"desc={r.get('meta_description_len')}  wa={r.get('wa_botones')}  "
              f"ld={r.get('ldjson_bloques')}  lang={r.get('lang')}  "
              f"sitemap={r.get('sitemap_via_robots')}")
        if r.get("error"):
            print(f"    ! {r['error']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
        print(f"\n-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
