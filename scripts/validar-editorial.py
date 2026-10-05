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
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"
PROPUESTA = ROOT / "01-propuesta" / "propuesta.html"
INFORME = ROOT / "00-auditoria" / "informe.html"
SPEC = ROOT / "SPEC-editorial.md"

CHROME_CANDIDATOS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

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


def render_dom(path: Path) -> str:
    """DOM ya ejecutado por el navegador. El informe y la propuesta arman su contenido
    en runtime: leer el HTML crudo sería leer el molde, no el documento."""
    chrome = next((c for c in CHROME_CANDIDATOS if Path(c).exists()), None)
    if not chrome or not path.exists():
        return ""
    with tempfile.TemporaryDirectory() as td:
        cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
               f"--user-data-dir={td}", "--virtual-time-budget=12000",
               "--dump-dom", path.as_uri()]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 errors="replace", timeout=120)
            return out.stdout or ""
        except Exception:
            return ""


def _bloques_con_clase(markup: str, clase: str) -> list:
    """Devuelve la LISTA de bloques con esa clase, contando profundidad de <div>: los
    cards se anidan y un non-greedy cortaría antes de tiempo. Devuelve una lista y no un
    texto unido: los bloques no son contiguos en el documento, así que unirlos no
    permitiría borrarlos después."""
    salida, i = [], 0
    marca = f'class="{clase}"'
    while True:
        i = markup.find(marca, i)
        if i < 0:
            return salida
        ini = markup.rfind("<div", 0, i)
        profundidad, j = 1, markup.find(">", i) + 1
        while profundidad and j > 0:
            abre, cierra = markup.find("<div", j), markup.find("</div", j)
            if cierra < 0:
                break
            if 0 <= abre < cierra:
                profundidad += 1
                j = abre + 4
            else:
                profundidad -= 1
                j = cierra + 5
        salida.append(markup[ini:j])
        i = j


class _Prosa(HTMLParser):
    """Extrae el texto de una sección salteando los bloques que tienen su propio tope
    (§7.4: 5 líneas por hallazgo, 4 bullets por módulo, tablas y listas aparte). Con
    expresiones regulares los cards anidados se cortan mal; el parser mantiene la pila
    de anidamiento y no se equivoca."""

    SALTAR_TAGS = {"table", "ul", "ol", "script", "style"}
    SALTAR_CLASES = {"finding", "module-card", "kpi-row", "compare-table", "callout"}
    VACIAS = {"br", "hr", "img", "input", "meta", "link", "source", "wbr", "area", "col"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pila = []
        self.trozos = []

    def handle_starttag(self, tag, attrs):
        if tag in self.VACIAS:
            return
        clases = set((dict(attrs).get("class") or "").split())
        self.pila.append(tag in self.SALTAR_TAGS or bool(clases & self.SALTAR_CLASES))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if self.pila and tag not in self.VACIAS:
            self.pila.pop()

    def handle_data(self, data):
        if not any(self.pila):
            self.trozos.append(data)

    def texto(self) -> str:
        return " ".join(self.trozos)


def prosa_de(seccion: str) -> int:
    """Palabras de la PROSA de una sección (sin cards, tablas ni listas)."""
    p = _Prosa()
    p.feed(seccion)
    return palabras(p.texto())


def _paginas(dom: str) -> list:
    """Parte el informe en hojas: cada .page es una hoja del paginador."""
    partes = re.split(r'<div class="page[" ]', dom)
    return partes[1:]


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

    # ---- §2 / §7.1 / §7.4 sobre el DOM renderizado, no sobre el molde -------------
    dom_prop = render_dom(PROPUESTA)
    dom_inf = render_dom(INFORME)
    if not (dom_prop or dom_inf):
        manual.append("no pude renderizar (¿falta el navegador?): §2, §7.1 y §7.4 quedan a ojo")

    if dom_prop:
        # §2 — «Medido» arranca con el número, no con contexto.
        malos = [m.group(1).strip()[:38]
                 for m in re.finditer(r"Medido:</strong>\s*([^<]{0,40})", dom_prop)
                 if m.group(1).strip() and not m.group(1).strip()[0].isdigit()]
        if malos:
            fallas.append("§2 «Medido» no arranca con el número: " + " | ".join(malos[:3]))
        else:
            print("  ✓ §2 cada «Medido» arranca con el número")

        # §7.4 — ningún cuerpo de sección pasa las 200 palabras (prosa, no cards).
        largas = []
        for m in re.finditer(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|\Z)", dom_prop, re.S | re.I):
            titulo = re.sub(r"<[^>]+>", " ", m.group(1)).strip()[:38]
            n = prosa_de(m.group(2))
            if n > 200:
                largas.append(f"«{titulo}» ~{n}")
        if largas:
            fallas.append("§7.4 secciones de más de 200 palabras de prosa: " + "; ".join(largas[:3]))
        else:
            print("  ✓ §7.4 ninguna sección de la propuesta pasa 200 palabras de prosa")

        # §7.4 — y cada hallazgo, dentro de sus 5 líneas (≈80 palabras).
        anchos = []
        for bloque in _bloques_con_clase(dom_prop, "finding"):
            n = prosa_de(bloque)
            if n > 80:
                anchos.append(f"~{n} palabras")
        if anchos:
            fallas.append(f"§7.4 {len(anchos)} hallazgo(s) de la propuesta pasan 5 líneas: "
                          + ", ".join(anchos))
        else:
            print("  ✓ §7.4 cada hallazgo de la propuesta entra en 5 líneas")

    if dom_inf:
        # §7.1 — ningún H3 sin H2 padre, hoja por hoja.
        huerfanos = [i for i, pag in enumerate(_paginas(dom_inf), 1)
                     if re.search(r"<h3", pag, re.I) and not re.search(r"<h[12]", pag, re.I)]
        if huerfanos:
            fallas.append(f"§7.1 H3 sin H2 padre en la hoja {huerfanos}")
        else:
            print("  ✓ §7.1 ninguna hoja del informe tiene H3 sin H2 padre")

    # §8.1-4 — la tabla se convierte en bullets en mobile: se mide el layout real
    # (getComputedStyle a 375 px), no se inspecciona el CSS.
    sonda = ROOT / "scripts" / "verificar-tabla-mobile.py"
    if sonda.exists():
        try:
            import importlib.util
            sp = importlib.util.spec_from_file_location("vtabla", sonda)
            mod = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(mod)
            r = mod.medir(PROPUESTA)
        except Exception as exc:  # noqa: BLE001
            r = {"err": str(exc)}
        if r.get("err"):
            avisos.append(f"§8.1 no pude medir la tabla en mobile: {r['err']}")
        elif not r.get("hayTabla") and r.get("hayBullets"):
            print("  ✓ §8.1 sin tabla: el comparativo va en 3 bullets (§6.2)")
        elif (r.get("displayTabla") == "block" and r.get("displayThead") == "none"
              and r.get("displayFila") == "block" and (r.get("desbordePx") or 0) <= 1
              and r.get("dataCol")):
            print(f"  ✓ §8.1 la tabla pasa a bullets en mobile ({r.get('vista')} px), "
                  "sin desborde lateral")
        else:
            fallas.append(f"§8.1 la tabla no cumple la condición mobile: {r}")
    else:
        manual.append("§8.1 la tabla en mobile (falta scripts/verificar-tabla-mobile.py)")

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
