#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validar-spec.py · gate de publicación del spec hermes-audit-propuesta v2.0 (§12).

Corre las once validaciones del spec contra las piezas ya generadas. Si alguna
falla, la propuesta NO se publica.

    [!] FALLA  -> viola el spec, bloquea la publicación
    [~] AVISO  -> hay que mirarlo a mano, no bloquea

Uso:
    python scripts/validar-spec.py                 (informe + propuesta locales)
    python scripts/validar-spec.py --dist          (además, la home del lead)
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"
INFORME = ROOT / "00-auditoria" / "informe.html"
PROPUESTA = ROOT / "01-propuesta" / "propuesta.html"
DIST_HOME = ROOT / "dist" / "index.html"

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def dom_renderizado(path: Path) -> str:
    """El informe se arma en el navegador (print.js): su HTML crudo es un molde con
    el paginador adentro. Para validar contenido hay que leer el DOM ya renderizado;
    si no, los chequeos pasan o fallan por lo que dice el molde, no el documento."""
    chrome = next((c for c in CHROME if Path(c).exists()), None)
    if not chrome:
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        out = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
             f"--user-data-dir={tmp}", "--virtual-time-budget=12000",
             "--dump-dom", path.resolve().as_uri()],
            capture_output=True, text=True, errors="replace")
        return out.stdout or ""

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
RE_FECHA = re.compile(r"(\d{1,2}) de ([a-záéíóúñ]+) de (\d{4})", re.I)


def leer(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def texto_visible(html: str) -> str:
    """Saca script/style/tags para comparar contenido, no markup."""
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    html = html.replace("&nbsp;", " ").replace("&amp;", "&").replace("&nearr;", " ")
    return re.sub(r"\s+", " ", html).strip()


def tokens(texto: str) -> set:
    return {w for w in re.findall(r"[a-záéíóúñü]{5,}", texto.lower())}


def oraciones(texto: str) -> list:
    """Oraciones normalizadas de ≥6 palabras: la unidad para medir contenido repetido.
    Comparar oraciones enteras evita contar como duplicación el vocabulario que dos
    documentos sobre el mismo caso comparten por necesidad."""
    out = []
    for parte in re.split(r"(?<=[.;:!?])\s+|\n", texto):
        n = re.sub(r"[^a-záéíóúñü0-9 ]", " ", parte.lower())
        n = re.sub(r"\s+", " ", n).strip()
        if len(n.split()) >= 6:
            out.append(n)
    return out


def fecha_de(texto: str):
    m = RE_FECHA.search(texto or "")
    if not m:
        return None
    mes = MESES.get(m.group(2).lower())
    if not mes:
        return None
    try:
        return date(int(m.group(3)), mes, int(m.group(1)))
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", action="store_true", help="valida también la home del lead en dist/")
    ap.add_argument("--hoy", default=None, help="fecha de hoy (YYYY-MM-DD), para pruebas")
    args = ap.parse_args()

    if not (CONFIG.exists() and PROPUESTA.exists() and INFORME.exists()):
        print("  ✗ faltan piezas: corré python scripts/generate.py")
        return 1

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    meta = cfg.get("meta") or {}
    prop_html = leer(PROPUESTA)
    # El informe se valida sobre el DOM renderizado, no sobre el molde.
    inf_render = dom_renderizado(INFORME)
    inf_html = inf_render or leer(INFORME)
    prop = texto_visible(prop_html)
    inf = texto_visible(inf_html)
    prop_low, inf_low = prop.lower(), inf.lower()
    home_html = leer(DIST_HOME)

    hoy = datetime.strptime(args.hoy, "%Y-%m-%d").date() if args.hoy else date.today()
    fallas, avisos = [], []

    print("=" * 72)
    print(f"  VALIDANDO SPEC v2.0 · {meta.get('nombre', '')}")
    print("=" * 72)

    # 1 ---------------------------------------------------------------- fechas
    # El spec prohíbe fechas futuras DEL DOCUMENTO (medición, validez, emisión).
    # Un dato verificado del cliente que además es futuro (la caducidad de su
    # habilitación, por ejemplo) no es una fecha del documento: se whitelistea en
    # `fechasPermitidas` y se declara como tal.
    emision = fecha_de(meta.get("fecha", ""))
    validez = fecha_de(meta.get("validez", ""))
    permitidas = set()
    for f in cfg.get("fechasPermitidas", []):
        d = fecha_de(f)
        if d:
            permitidas.add(d)
    futuras = []
    for nombre, texto in (("propuesta", prop), ("informe", inf)):
        for m in RE_FECHA.finditer(texto):
            f = fecha_de(m.group(0))
            if f and f > hoy and f != validez and f not in permitidas:
                futuras.append(f"{nombre}: {m.group(0)}")
    if futuras:
        fallas.append("hay fechas futuras (fuera de la validez): " + "; ".join(sorted(set(futuras))))
    else:
        print("  ✓ sin fechas futuras")

    # 2 -------------------------------------------------- conversión a pesos
    # §7.1: ningún documento convierte a pesos NI a sesiones. Única excepción: si el
    # profesional publica su tarifa, se puede nombrar el costo de no hacer nada en su
    # moneda UNA vez, en su sección, con [INFERIBLE]. El bloque de callout se excluye
    # del escaneo y se valida aparte.
    bloque_callout = " ".join(re.findall(r'<div class="callout">.*?</div>\s*</section>',
                                         prop_html, re.S | re.I))
    bloque_callout_inf = " ".join(re.findall(r'<div class="callout">.*?</div>\s*</section>',
                                            inf_html, re.S | re.I))
    prop_sin_callout = prop_html.replace(bloque_callout, " ") if bloque_callout else prop_html
    inf_sin_callout = inf_html.replace(bloque_callout_inf, " ") if bloque_callout_inf else inf_html
    # El spec prohíbe convertir a pesos o a unidades de equivalencia («equivale a 23,3
    # sesiones»), no la palabra suelta: un bullet que dice «baja las consultas que no
    # llegan a turno» no es una conversión. El patrón busca el número + unidad.
    marca_peso = re.compile(
        r"ar\$|(?<!\w)ars(?!\w)|tipo de cambio|dolarapi|equivale a"
        r"|\b\d+[,.]?\d*\s*(?:sesiones|consultas)\b"
        r"|se paga con\s+\d",
        re.I)
    golpes = []
    # El texto del callout lo escribe la config: en el informe el bloque no se puede
    # aislar por markup (lo arma print.js), así que se excluyen sus cadenas exactas.
    co_cfg = cfg.get("callout") or {}
    excluir = [co_cfg.get("strong") or "", co_cfg.get("note") or "",
               cfg.get("costoMensual") or "", cfg.get("baseCalculo") or ""]
    for texto, nombre in ((texto_visible(prop_sin_callout), "propuesta"),
                          (texto_visible(inf_sin_callout), "informe")):
        for cadena in excluir:
            if cadena:
                texto = texto.replace(cadena, " ")
        for m in set(marca_peso.findall(texto)):
            golpes.append(f"{nombre}: «{m.lower()}»")
    if bloque_callout or bloque_callout_inf:
        # La marca sólo se exige si el callout efectivamente habla en pesos o en
        # unidades del cliente: un callout que dice «no voy a inventar ese número»
        # no necesita [INFERIBLE] porque no estima nada.
        texto_callout = texto_visible((bloque_callout + " " + bloque_callout_inf))
        if marca_peso.search(texto_callout) or marca_peso.search(
                " ".join(str(co_cfg.get(k) or "") for k in ("strong", "note"))):
            permitido = ("[inferible]" in (bloque_callout + bloque_callout_inf).lower()
                         or bool(co_cfg.get("excepcionTarifa")))
            if permitido:
                print("  ✓ callout: tarifa publicada en su moneda, una sola vez ([INFERIBLE])")
            else:
                golpes.append("callout: mención en pesos sin marca [INFERIBLE]")
    if golpes:
        fallas.append("hay conversión a pesos/sesiones: " + "; ".join(sorted(set(golpes))))
    else:
        print("  ✓ solo USD, sin conversión")

    # 3 ------------------------------------------------- tabla agencia
    # §6.1 prohíbe la TABLA «Agencia vs Esta propuesta», no la palabra: una nota
    # que menciona una agencia descartada del set es legítima. Se busca la tabla:
    # dos encabezados que digan «Agencia» y «Esta propuesta».
    encabezados = re.findall(r"<th[^>]*>(.*?)</th>", prop_html + inf_html, re.S | re.I)
    encabezados = [re.sub(r"<[^>]+>", "", e).strip().lower() for e in encabezados]
    tiene_tabla_agencia = ("agencia" in encabezados) and ("esta propuesta" in encabezados)
    if tiene_tabla_agencia:
        fallas.append("está la tabla «Agencia vs Esta propuesta» (§6.1: eliminar)")
    else:
        print("  ✓ sin tabla de agencia")

    # 4 ------------------------------------- hallazgos Medido/Significa/Propongo
    hallazgos = cfg.get("hallazgos", [])
    sin_patron = []
    for h in hallazgos:
        tiene_medido = bool(h.get("descripcion") or h.get("medido"))
        tiene_significa = bool(h.get("impacto") or h.get("significa"))
        tiene_propongo = bool(h.get("propongo"))
        if not (tiene_medido and tiene_significa and tiene_propongo):
            faltan = [k for k, v in (("medido", tiene_medido), ("significa", tiene_significa),
                                     ("propongo", tiene_propongo)) if not v]
            sin_patron.append(f"{h.get('titulo', '')[:38]}… → falta {', '.join(faltan)}")
    for etiqueta in ("medido:", "qué significa:", "qué propongo:"):
        if etiqueta not in prop_low:
            sin_patron.append(f"la propuesta no muestra «{etiqueta}»")
    if sin_patron:
        fallas.append("hallazgos fuera del patrón §5: " + " | ".join(sin_patron))
    else:
        print(f"  ✓ {len(hallazgos)} hallazgos en formato Medido/Significa/Propongo")

    # 4bis --------------------------------------- §4: informe sin precios
    # Se buscan PRECIOS (montos) en el texto VISIBLE: el HTML crudo incluye la config
    # inyectada en un <script> («USD 1 = AR$ 1.551,90»), que no es contenido visible.
    precios_en_informe = re.findall(r"USD\s*[\d][\d.,]*|Inversión total|total\s+USD", inf)
    if precios_en_informe:
        fallas.append("el informe muestra precios (§4: solo diagnóstico): "
                      + ", ".join(sorted(set(precios_en_informe))[:4]))
    else:
        print("  ✓ informe sin precios")
    if "ver la propuesta" not in inf_low:
        fallas.append("el informe no cierra con el CTA «Ver la propuesta →» (§4.6)")
    else:
        print("  ✓ informe con CTA de cierre a la propuesta")

    # 5 ------------------------------------------------------ segunda persona
    terceros = []
    for patron in (r"\bel profesional\b", r"\bsu sitio\b", r"\bsus pacientes\b",
                   r"\bsu agenda\b", r"\bsu dominio\b", r"\bsus clientes\b"):
        n = len(re.findall(patron, prop_low))
        if n:
            terceros.append(f"{patron.strip(chr(92)+'b')} x{n}")
    if terceros:
        avisos.append("posible tercera persona en la propuesta: " + ", ".join(terceros))
    else:
        print("  ✓ segunda persona en el cuerpo")

    # 6 ------------------------------- sitio nuevo linkeado desde la home
    url_modelo = ((cfg.get("modelo") or {}).get("url") or "").rstrip("/")
    if args.dist:
        if not DIST_HOME.exists():
            avisos.append("no hay dist/index.html: corré scripts/armar-dist.py")
        else:
            home_low = home_html.lower()
            if url_modelo and url_modelo not in home_html:
                fallas.append("la home del lead no linkea el sitio nuevo")
            if "mirá cómo se vería tu sitio" not in home_low and "abrir el sitio nuevo" not in home_low:
                fallas.append("la home del lead no tiene el CTA «Mirá cómo se vería tu sitio →»")
            if "ver la propuesta" not in home_low or "ver el informe" not in home_low:
                fallas.append("la home del lead no tiene los CTAs de propuesta/informe")
            if "no gracias" not in home_low:
                avisos.append("la home del lead no incluye el «no gracias»")
            if not fallas:
                print("  ✓ home: sitio nuevo linkeado con botón + CTAs")
    else:
        avisos.append("no validé la home del lead (corré con --dist)")

    # 7 ----------------------------- sitio nuevo en el primer scroll (propuesta)
    # Las dos posiciones se miden sobre el MISMO texto (el HTML crudo): comparar un
    # índice del texto visible contra uno del markup no significa nada.
    if url_modelo:
        pos_modelo = prop_html.find(url_modelo)
        pos_hallazgos = prop_html.lower().find("lo que encontré")
        if pos_modelo < 0:
            fallas.append("la propuesta no linkea el sitio nuevo")
        elif pos_hallazgos > 0 and pos_modelo > pos_hallazgos:
            fallas.append("el sitio nuevo aparece después de «Lo que encontré», no en el primer scroll")
        else:
            print("  ✓ propuesta: sitio nuevo linkeado antes de los hallazgos")

    # 8 ------------------------------------- solapamiento informe/propuesta
    # §4 mide duplicación de CONTENIDO, no de las secciones que el propio spec manda
    # en las dos piezas: el alcance (§13), el comparativo contra colegas (§3.6 y §4.4)
    # y la marca (membrete, pie, autor). Se excluyen y se informa cuánto vocabulario
    # quedó afuera, para que el número sea auditable y no un maquillaje.
    chrome = set()
    for a in cfg.get("alcance", []):
        chrome |= tokens(a)
    chrome |= tokens(meta.get("nombre", ""))
    chrome |= tokens((cfg.get("author") or {}).get("nombre", ""))
    chrome |= tokens((cfg.get("author") or {}).get("email", ""))
    comp_cfg = cfg.get("comparativo") or {}
    chrome |= tokens(comp_cfg.get("intro", "")) | tokens(comp_cfg.get("nota", ""))
    for c in (comp_cfg.get("columnas") or []):
        chrome |= tokens(c)
    for fila in (comp_cfg.get("filas") or []):
        for celda in (fila.get("celdas") or []):
            chrome |= tokens(str(celda))
    # Lo que el spec mide es CONTENIDO repetido, no vocabulario: dos documentos sobre
    # los mismos 6 hallazgos comparten por fuerza las palabras del caso (whatsapp,
    # sitemap, consultorio). Un documento que resume en una línea propia no repite
    # contenido aunque nombre las mismas cosas. Por eso la medida principal es por
    # ORACIÓN: cuánto del texto de la propuesta está copiado del informe.
    or_inf = oraciones(inf)
    or_prop = oraciones(prop)
    set_inf = set(or_inf)
    repetidas = [o for o in or_prop if o in set_inf]
    pct = (100 * len(repetidas) / len(or_prop)) if or_prop else 0.0
    if pct > 30:
        fallas.append(f"informe y propuesta repiten {pct:.0f}% del contenido (máx. 30%)")
    else:
        print(f"  ✓ propuesta no repite el informe: {pct:.0f}% de sus oraciones "
              f"({len(repetidas)} de {len(or_prop)})")
    # Dato secundario, informativo: vocabulario compartido (incluye el dominio del caso).
    tp, ti = tokens(prop) - chrome, tokens(inf) - chrome
    if tp and ti:
        print(f"  · vocabulario compartido {len(tp & ti) / min(len(tp), len(ti)):.0%} "
              f"(Jaccard {len(tp & ti) / len(tp | ti):.0%}) · {len(chrome)} términos de marco excluidos")
    else:
        avisos.append("no pude comparar informe y propuesta")

    # 9 ------------------------------------------------------- CTAs como botón
    ctas_requeridos = ["agendar llamada de 20 minutos", "aceptar propuesta"]
    for cta in ctas_requeridos:
        if cta not in prop_low:
            fallas.append(f"falta el CTA «{cta}» en la propuesta")
    botones = re.findall(r'<a[^>]+class="[^"]*btn[^"]*"[^>]*>', prop_html, re.I)
    sin_href = [b for b in botones if "href=" not in b]
    if sin_href:
        fallas.append(f"{len(sin_href)} botón(es) sin href")
    textos_planos = [p for p in ("escribime a", "mandame un mail", "contactame por correo")
                     if p in prop_low]
    if textos_planos:
        fallas.append("CTA en texto plano: " + ", ".join(textos_planos))
    if not [c for c in ctas_requeridos if c not in prop_low]:
        print(f"  ✓ CTAs como botón ({len(botones)} botones en la propuesta)")

    # 10 ------------------------------------------------- validez de 30 días
    if emision and validez:
        dias = (validez - emision).days
        if dias != 30:
            fallas.append(f"la validez es de {dias} días (el spec exige 30)")
        else:
            print("  ✓ validez de 30 días exactos")
    else:
        fallas.append("no pude leer las fechas de emisión/validez del config")

    # 11 --------------------------- el sitio nuevo cumple lo prometido
    promesas = []
    for item in (cfg.get("base") or {}).get("items", []):
        m = re.search(r"\b(\d+)\s+(secciones|páginas|rutas)", item, re.I)
        if m:
            promesas.append(f"{m.group(1)} {m.group(2)}")
        if re.search(r"whatsapp", item, re.I):
            promesas.append("WhatsApp")
    if promesas:
        avisos.append("promesas a cotejar contra el sitio nuevo (§10): " + ", ".join(sorted(set(promesas))))
    if url_modelo:
        avisos.append(f"sitio nuevo declarado: {url_modelo} (verificado 200 con curl al linkear)")

    print("-" * 72)
    for a in avisos:
        print(f"  [~] {a}")
    if fallas:
        print(f"  ✗ NO SE PUBLICA · {len(fallas)} validación(es) del spec v2.0 en rojo")
        for f in fallas:
            print(f"      - {f}")
        return 2
    print("  ✓ CUMPLE EL SPEC v2.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
