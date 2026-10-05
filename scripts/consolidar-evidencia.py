#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consolidar-evidencia.py · junta toda la evidencia de la auditoría en un solo JSON.

Entradas:
    00-auditoria/evidencia-web.json            señales medidas del cliente y de los pares
    00-auditoria/evidencia-doctoralia.json     perfiles de la categoría en Rosario
    00-auditoria/evidencia-antes-despues.json  sitio actual vs sitio nuevo
    config.json                                hallazgos, precios y alcance declarados

Salida:
    00-auditoria/evidencia.json                el artefacto legible por máquina

Uso:
    python scripts/consolidar-evidencia.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUD = ROOT / "00-auditoria"


def leer(path: Path, por_defecto=None):
    if not path.exists():
        return por_defecto
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    cfg = leer(ROOT / "config.json")
    if cfg is None:
        print("ERROR: falta config.json")
        return 1

    web = leer(AUD / "evidencia-web.json", {})
    doc = leer(AUD / "evidencia-doctoralia.json", {})
    ad = leer(AUD / "evidencia-antes-despues.json", {})

    base = int(cfg.get("base", {}).get("precio", 0))
    modulos = cfg.get("modulos", [])
    total = base + sum(int(m.get("price", 0)) for m in modulos)

    pares = {k: v for k, v in web.items() if k != "cliente"}
    vivos = [k for k, v in pares.items() if v.get("status") == 200]
    muertos = [k for k, v in pares.items() if v.get("error") and "getaddrinfo" in str(v.get("error"))]
    bloqueados = [k for k, v in pares.items() if v.get("status") not in (200, None) and k not in muertos]
    con_whatsapp = [k for k, v in pares.items() if (v.get("wa_botones") or 0) > 0]

    peso = cfg.get("peso", {})
    antes_peso = peso.get("antes", {})
    despues_peso = peso.get("despues", {})

    ev = {
        "que_es": "Evidencia de la auditoría de presencia digital del Lic. Lisandro Lagos (Rosario).",
        "cliente": cfg.get("meta", {}),
        "medidoEl": "2026-10-04",
        "autor": cfg.get("author", {}),
        "reproducible": [
            "python scripts/medir.py --pares 00-auditoria/pares.txt --out 00-auditoria/evidencia-web.json",
            "python scripts/pesar.py https://www.liclisandrolagos.com/",
            "python scripts/verificar-sitio.py",
            "python scripts/consolidar-evidencia.py",
        ],

        "sitio_actual": web.get("cliente", {}),
        "peso": {
            "antes_kb": antes_peso.get("total_kb"),
            "antes_archivos": antes_peso.get("archivos"),
            "despues_kb": despues_peso.get("total_kb"),
            "despues_archivos": despues_peso.get("archivos"),
            "reduccion": round(antes_peso.get("total_kb", 1) / despues_peso.get("total_kb", 1), 2)
            if antes_peso.get("total_kb") and despues_peso.get("total_kb") else None,
        },

        "comparativo_web": {
            "pares_medidos": len(pares),
            "vivos": vivos,
            "dominios_muertos": muertos,
            "bloquearon_la_medicion": bloqueados,
            "con_boton_de_whatsapp": con_whatsapp,
            "detalle": pares,
        },

        "comparativo_doctoralia": doc.get("totales", {}),
        "posicion_del_cliente": {
            "opiniones": doc.get("cliente", {}).get("opiniones"),
            "rating": doc.get("cliente", {}).get("rating"),
            "mediana_de_la_categoria": doc.get("totales", {}).get("mediana_opiniones_de_los_que_tienen"),
            "maximo_de_la_categoria": doc.get("totales", {}).get("maximo_opiniones"),
        },

        "hallazgos": [
            {
                "prioridad": h.get("prioridad"),
                "evidencia": h.get("tipo"),
                "titulo": h.get("titulo"),
                "impacto": h.get("impacto"),
            }
            for h in cfg.get("hallazgos", [])
        ],

        "propuesta": {
            "moneda": "USD",
            "base": base,
            "modulos": [{"code": m.get("code"), "title": m.get("title"), "price": m.get("price")} for m in modulos],
            "total_pack": total,
            "pack_con_descuento": round(total * 0.85 / 5) * 5,
            "referencia_cambio": cfg.get("conversion", {}),
        },

        "verificado": [a.lstrip("✓ ") for a in cfg.get("alcance", []) if a.startswith("✓")],
        "no_verificado": [a.lstrip("✗ ") for a in cfg.get("alcance", []) if a.startswith("✗")],
        "datos_por_confirmar": cfg.get("preguntasAbiertas", []),

        "antes_despues": {
            "antes": {k: ad.get("antes", {}).get(k) for k in (
                "status", "lang", "meta_description_len", "og_tags", "twitter_tags",
                "ldjson_bloques", "h1_count", "h2_count", "img_total", "img_sin_alt",
                "img_lazy", "srcset", "wa_botones", "sitemap_via_robots", "bytes_html")},
            "despues": {k: ad.get("despues", {}).get(k) for k in (
                "status", "lang", "meta_description_len", "og_tags", "twitter_tags",
                "ldjson_bloques", "h1_count", "h2_count", "img_total", "img_sin_alt",
                "img_lazy", "srcset", "wa_botones", "sitemap_via_robots", "bytes_html")},
        },
    }

    destino = AUD / "evidencia.json"
    destino.write_text(json.dumps(ev, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"-> {destino.relative_to(ROOT)}")
    print(f"   hallazgos           : {len(ev['hallazgos'])}")
    print(f"   pares medidos       : {ev['comparativo_web']['pares_medidos']} "
          f"({len(vivos)} vivos, {len(muertos)} con dominio muerto, {len(bloqueados)} bloquearon)")
    print(f"   con WhatsApp        : {len(con_whatsapp)} de {len(pares)}")
    print(f"   peso                : {ev['peso']['antes_kb']} KB -> {ev['peso']['despues_kb']} KB "
          f"(x{ev['peso']['reduccion']})")
    print(f"   propuesta           : USD {base} base + {len(modulos)} módulos = USD {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
