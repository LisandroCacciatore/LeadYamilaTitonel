#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validar-editorial.py · gate de forma del spec `hermes-editorial` v1.0.

El spec v2.0 define QUÉ contiene el documento y en qué orden; éste define CÓMO se
escribe. Si hay conflicto manda el v2.0 (regla de precedencia del propio spec).

Acá se automatiza lo que es objetivamente verificable. Lo que no lo es se lista al
final como «revisión manual», con el ítem concreto — no se declara cumplido por
omisión.

Uso:
    python scripts/validar-editorial.py
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"
PROPUESTA = ROOT / "01-propuesta" / "propuesta.html"
INFORME = ROOT / "00-auditoria" / "informe.html"
SPEC = ROOT / "SPEC-editorial.md"

# §1.2 — frases gastadas, prohibidas en cualquier zona del documento.
MULETILLAS = [
    "la ventaja más barata",
    "sobre la mesa",
    "para que no haya sorpresas",
    "no hay una sola afirmación",
    "sin inventar métricas",
    "el cambio, en una mirada",
    "casa desordenada",
    "techo duro",
    "puerta de entrada",
    "cuello de botella",
    "en un mundo lleno",
    "no cambian por decretos",
]

# §1.3 — el documento habla en vos. Estas son las formas de tercera persona sobre el
# cliente que el spec manda corregir on sight.
TERCERA_PERSONA = [
    r"él mismo publica",
    r"a la tarifa que él publica",
    r"\bel profesional\b",
    r"\bsus pacientes\b",
]


def leer(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def texto_visible(markup: str) -> str:
    markup = re.sub(r"<(script|style).*?</\1>", " ", markup, flags=re.S | re.I)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", markup)))


def palabras(texto: str) -> int:
    """Cuenta palabras, no cifras: en «Tenés 5 opiniones. La mediana es 14» hay 7
    palabras. El propio spec propone ese titular como correcto, así que la regla de
    12 palabras no puede estar contando los números."""
    return len([w for w in re.findall(r"[\wáéíóúñüÁÉÍÓÚÑÜ]+", texto or "")
                if not re.fullmatch(r"[\d.,:/-]+", w)])


def main() -> int:
    if not CONFIG.exists():
        print("no encuentro config.json")
        return 2
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    prop_html = leer(PROPUESTA)
    prop = texto_visible(prop_html)
    inf = texto_visible(leer(INFORME))
    ambos = prop + " " + inf

    fallas, avisos, manual = [], [], []

    print("=" * 68)
    print("  VALIDACIÓN EDITORIAL · spec hermes-editorial v1.0")
    print("=" * 68)

    # §1.2 ------------------------------------------------------- muletillas
    dichas = sorted({m for m in MULETILLAS if m in ambos.lower()})
    if dichas:
        fallas.append("§1.2 muletillas prohibidas: " + "; ".join(f"«{m}»" for m in dichas))
    else:
        print("  ✓ §1.2 sin muletillas de la lista")

    # §1.3 ---------------------------------------------------- segunda persona
    dichas_ter = sorted({m for p in TERCERA_PERSONA for m in re.findall(p, ambos, re.I)})
    if dichas_ter:
        fallas.append("§1.3 tercera persona: " + "; ".join(f"«{m}»" for m in dichas_ter))
    else:
        print("  ✓ §1.3 el documento habla en vos")
    # «su sitio» puede referirse a un tercero (un colega del comparativo): se avisa.
    for m in re.finditer(r".{55}\bsu (?:sitio|dominio|perfil)\b.{35}", ambos, re.I):
        avisos.append("§1.3 revisar de quién habla: …" + m.group(0).strip() + "…")

    # §2 ------------------------------------------- titulares y largo de hallazgo
    # El largo del hallazgo se mide por pieza: la propuesta es la que resume (y la que
    # tiene el tope de 5 líneas); el informe es el que detalla, y ahí el detalle es el
    # punto. Mezclar los dos campos medía un documento que no existe.
    prop_hall = ((cfg.get("propuesta") or {}).get("saludo") and True)
    for i, h in enumerate(cfg.get("hallazgos", []), 1):
        for campo in ("titulo", "tituloCorto"):
            t = (h.get(campo) or "").strip()
            if t and palabras(t) > 12:
                fallas.append(f"§2 titular {i} ({campo}) tiene {palabras(t)} palabras (máx. 12): «{t}»")
        largo_prop = sum(palabras(h.get(c)) for c in ("resumen", "significa", "propongo"))
        if largo_prop > 80:
            manual.append(f"§2 hallazgo {i}: la propuesta le dedica ~{largo_prop} palabras "
                          f"(tope 5 líneas ≈ 80) — recortar")
    if not any("titular" in f for f in fallas):
        print("  ✓ §2 titulares dentro de 12 palabras")

    # §3 ------------------------------------------------- un dato, una aparición
    for k in ((cfg.get("comparativo") or {}).get("kpis") or []):
        v = str(k.get("valor", "")).strip()
        if len(v) < 2:
            continue
        n = len(re.findall(re.escape(v), prop))
        if n > 2:
            fallas.append(f"§3 el dato «{v}» aparece {n} veces en la propuesta (máx. 2)")
    if not any("§3" in f for f in fallas):
        print("  ✓ §3 ningún dato clave repetido más de dos veces")

    # §4 ------------------------------------------------------- cuadro de números
    kpis = ((cfg.get("comparativo") or {}).get("kpis") or [])
    if len(kpis) > 4:
        fallas.append(f"§4.1 el cuadro tiene {len(kpis)} números (máx. 4)")
    else:
        print(f"  ✓ §4.1 cuadro con {len(kpis)} números")
    for k in kpis:
        if palabras(str(k.get("label", ""))) > 8:
            fallas.append(f"§4.2 etiqueta de más de 8 palabras: «{k.get('label')}»")

    # §5.1 ------------------------------------------------------- largo de listas
    for nombre, lista in (("próximos pasos", cfg.get("nextSteps") or []),
                          ("qué no incluye", cfg.get("sinIncluir") or []),
                          ("preguntas al cliente", cfg.get("preguntasAbiertas") or [])):
        if len(lista) > 5:
            fallas.append(f"§5.1 la lista «{nombre}» tiene {len(lista)} ítems (máx. 5)")
    modulos = cfg.get("modulos") or []
    for m in modulos:
        if len(m.get("bullets") or []) > 4:
            fallas.append(f"§7.4 «{m.get('title')}» tiene {len(m.get('bullets'))} bullets (máx. 4)")
    if not any("§5.1" in f for f in fallas):
        print("  ✓ §5.1 listas dentro de 5 ítems")

    # §6.1 --------------------------------------------------- formato de números
    formatos = []
    for pat, nota in ((r"\d+K\b", "notación K (usar el número completo)"),
                      (r"USD\d", "falta el espacio después de USD"),
                      (r"AR\$\d", "falta el espacio después de AR$"),
                      (r"\d+%", "falta el espacio antes del %")):
        hits = re.findall(pat, ambos)
        if hits:
            formatos.append(f"{nota}: {', '.join(sorted(set(hits))[:3])}")
    if formatos:
        fallas.append("§6.1 formato de números — " + "; ".join(formatos))
    else:
        print("  ✓ §6.1 números, unidades y porcentajes bien formateados")

    # §7.2 ------------------------------------------- sección única de límites
    tiene_limites = "límites de este documento" in prop.lower()
    sueltas = [s for s in ("lo que no puedo medir", "qué no incluye")
               if prop.lower().count(s) > 1]
    if not tiene_limites:
        avisos.append("§7.2 falta consolidar las tres secciones de límites en una "
                      "«Límites de este documento»")
    if sueltas:
        avisos.append("§7.2 quedan secciones de límites sueltas: " + ", ".join(sueltas))
    if tiene_limites and not sueltas:
        print("  ✓ §7.2 límites consolidados en una sección")

    # §7.3 ------------------------------------------------------- CTA intermedio
    # El ancla no puede ser el texto «Base — …»: esa frase también vive dentro del
    # «Qué propongo» de un hallazgo, y hacía que el chequeo mirara el tramo equivocado.
    pos_hall = prop_html.lower().find("5 · lo que encontré")
    pos_precios = prop_html.lower().find("9-11 · base")
    if pos_precios < 0:
        pos_precios = prop_html.lower().find("escenarios, para no decidir")
    if pos_hall > 0 and pos_precios > pos_hall:
        medio = prop_html[pos_hall:pos_precios].lower()
        if "mailto:" in medio or "agendar" in medio:
            print("  ✓ §7.3 hay CTA entre los hallazgos y los precios")
        else:
            avisos.append("§7.3 falta el CTA intermedio («Si querés, hablamos…») "
                          "entre los hallazgos y los precios")

    # §10 ------------------------------------------------------------- escenarios
    if "recomendado" in prop.lower():
        print("  ✓ §10 el «Recomendado» está señalado")
    else:
        fallas.append("§10 no hay escenario «Recomendado» señalado")

    # §9.4 -------------------------------------------------- capturas con caption
    imgs = re.findall(r'<img[^>]+class="shot-img"', prop_html)
    caps = len(re.findall(r'class="shot-cap|class="caption', prop_html))
    if imgs and caps < len(imgs):
        manual.append("§9.4 hay capturas sin epígrafe (Hoy — … / Nuevo — …)")

    # §3 y §7.1 del spec para el informe: nada de esto se puede ver sin renderizar.
    manual += [
        "§2 «Medido» debe arrancar con el número, no con contexto (revisar el render)",
        "§7.1 ningún H3 sin H2 padre en la misma página (revisar el render)",
        "§7.4 ningún cuerpo de sección supera 200 palabras (revisar el render)",
        "§8.1 la tabla de colegas cumple las 4 condiciones, incluida la de mobile",
    ]

    # §11 ------------------------------ trabajo pendiente declarado en el propio spec
    apellido = (cfg.get("meta", {}).get("nombre", "").split()[-1] or "").lower()
    spec = leer(SPEC)
    pendientes = []
    bloque = re.search(rf"^### .*{re.escape(apellido)}.*$(.*?)(?=^###|\Z)",
                       spec, re.S | re.M | re.I)
    if bloque:
        pendientes = [l.strip("- ").strip() for l in bloque.group(1).splitlines()
                      if l.strip().startswith("-")]

    print("-" * 68)
    for a in avisos:
        print("  [~] " + a)
    if pendientes:
        print(f"  [§11] errores declarados para este lead ({len(pendientes)}), a corregir:")
        for p in pendientes:
            print("        · " + p)
    if manual:
        print("  [manual] no automatizable, revisar a ojo:")
        for m in manual:
            print("        · " + m)
    print("-" * 68)

    if fallas:
        print(f"  ✗ EDITORIAL EN ROJO · {len(fallas)} incumplimiento(s)")
        for f in fallas:
            print("      - " + f)
        return 1
    print("  ✓ CUMPLE EL SPEC EDITORIAL v1.0 (lo automatizable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
