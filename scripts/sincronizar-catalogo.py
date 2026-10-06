#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sincronizar-catalogo.py · propaga el catálogo único de add-ons a los configs.

Problema que resuelve: un precio vivía escrito en el config de cada cliente, así que
el mismo add-on salía a USD 120 para uno y a USD 80 para otro (pasó de verdad:
WhatsApp contextual). Acá el precio vive UNA vez, en templates/catalogo.json.

Cómo funciona:
    El config declara sólo QUÉ add-on quiere el cliente y CUÁL le recomienda:

        "recomendados": ["whatsapp", "terminacion", "peso"]

    El menú completo que ve el cliente es TODO el catálogo. Los recomendados van
    primero y con la marca; el resto, después, sin marca. Los códigos M1..Mn se
    asignan en ese orden (por eso el recomendado siempre es M1..Mk), así el
    paginador y los escenarios siguen funcionando sin cambios.

    Este script escribe `modulos` en el config: los otros cinco scripts del motor
    (validar-editorial, cotejar-promesas, verify, verify-pdf, consolidar-evidencia)
    leen ese campo y siguen funcionando igual.

Uso:
    python scripts/sincronizar-catalogo.py                 # todos los leads hermanos
    python scripts/sincronizar-catalogo.py --config config.json
    python scripts/sincronizar-catalogo.py --check         # no escribe, falla si hay deriva
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGO = ROOT / "templates" / "catalogo.json"

# Los leads hermanos viven al lado del motor (~/lead-<cliente>).
HERMANOS = [
    "lead-campanaro",
    "lead-yamila-titonel",
    "lead-lagos-lisandro",
]


def leer(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def escribir(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def armar_modulos(catalogo: list, recomendados: list) -> list:
    """Recomendados primero (con la marca), después el resto del menú sin marca.

    Se valida que ningún id quede fuera del catálogo: un typo en el config no puede
    pasar en silencio y hacer desaparecer un add-on de la propuesta.
    """
    por_id = {a["id"]: a for a in catalogo}
    desconocidos = [r for r in recomendados if r not in por_id]
    if desconocidos:
        raise ValueError(f"ids que no están en el catálogo: {desconocidos}")

    orden = list(dict.fromkeys(recomendados))  # sin duplicados, respetando el orden
    orden += [a["id"] for a in catalogo if a["id"] not in orden]

    modulos = []
    for i, aid in enumerate(orden, 1):
        a = por_id[aid]
        modulos.append({
            "id": a["id"],
            "code": f"M{i}",
            "title": a["title"],
            "price": a["price"],
            "short": a["short"],
            "bullets": list(a["bullets"]),
            "recomendado": aid in recomendados,
        })
    return modulos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None, help="un solo config; si falta, recorre los leads hermanos")
    ap.add_argument("--check", action="store_true", help="no escribe: falla si el config está desincronizado")
    args = ap.parse_args()

    if not CATALOGO.exists():
        print(f"ERROR: falta {CATALOGO.relative_to(ROOT)}")
        return 1
    catalogo = leer(CATALOGO)["addons"]
    print(f"catálogo: {len(catalogo)} add-ons · {CATALOGO.relative_to(ROOT)}")

    if args.config:
        configs = [ROOT / args.config]
    else:
        configs = [ROOT.parent / h / "config.json" for h in HERMANOS]
        configs = [c for c in configs if c.exists()]

    fallos = 0
    for cfg_path in configs:
        cfg = leer(cfg_path)
        recomendados = cfg.get("recomendados")
        if recomendados is None:
            print(f"  [~] {cfg_path.parent.name}: sin «recomendados», no se toca")
            continue

        nuevos = armar_modulos(catalogo, recomendados)
        viejos = cfg.get("modulos") or []
        deriva = [m["code"] for m, v in zip(nuevos, viejos)
                  if m["title"] != v.get("title") or m["price"] != v.get("price")]
        if len(nuevos) != len(viejos):
            deriva.append(f"cantidad {len(viejos)}→{len(nuevos)}")

        base = int(cfg.get("base", {}).get("precio", 0))
        sum_antes = sum(int(m.get("price", 0)) for m in viejos)
        sum_ahora = sum(int(m["price"]) for m in nuevos)
        n_rec = sum(1 for m in nuevos if m["recomendado"])

        print(f"\n  {cfg_path.parent.name}")
        print(f"    recomendados : {n_rec} ({', '.join(recomendados)})")
        print(f"    menú         : {len(nuevos)} add-ons")
        print(f"    pack completo: USD {base} + {sum_antes} = {base + sum_antes}"
              f"  →  USD {base} + {sum_ahora} = {base + sum_ahora}")

        if args.check:
            if deriva:
                fallos += 1
                print(f"    ✗ DESINCRONIZADO: {deriva}")
            else:
                print("    ✓ sincronizado")
            continue

        cfg["modulos"] = nuevos
        escribir(cfg_path, cfg)
        print(f"    ✓ escrito ({len(deriva)} cambio(s) de precio/orden)")

    print()
    if args.check and fallos:
        print(f"{fallos} config(s) desincronizados: corré sin --check para arreglarlos")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
