#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate.py · genera los documentos del lead desde un solo config.json.

Uso:
    python scripts/generate.py
    python scripts/generate.py --config config.json --informe 00-auditoria/informe.html --propuesta 01-propuesta/propuesta.html

Produce:
    informe.html    documento A4 con membrete y pie en cada hoja, paginado por
                    templates/print.js (el paginador se auto-verifica: data-desbordes=0)
    propuesta.html  propuesta comercial narrativa + selector interactivo de módulos

Regla de la casa: los totales se calculan, nunca se escriben. Este script es el
único que resuelve los placeholders; si queda uno sin resolver, falla.
"""

import argparse
import base64
import html
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
TEMPLATES = ROOT / "templates"

PRINT_JS_MARKER = "Paginador del informe"

# Secciones compartidas de la propuesta (índice, glosario, etapas, pago...). El texto
# vive en datos y cada cliente lo puede pisar desde su config.
SECCIONES = json.loads((TEMPLATES / "secciones.json").read_text(encoding="utf-8")) \
    if (TEMPLATES / "secciones.json").exists() else {}


def read(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=False)


def money(n) -> str:
    return f"USD {int(n):,}".replace(",", ".")


def miles(n) -> str:
    """Separador de miles argentino: 1.551.900"""
    return f"{int(round(n)):,}".replace(",", ".")


def dec1(n) -> str:
    """Un decimal con coma decimal: 9,1"""
    return f"{n:.1f}".replace(".", ",")


def render(tpl: str, data: dict) -> str:
    out = tpl
    for key, value in data.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


# ---------------------------------------------------------------- bloques

def finding_card(h: dict, idx: int = 0) -> str:
    """Patrón fijo del spec §5: Medido / Qué significa / Qué propongo.
    En la propuesta el «Medido» va resumido a una línea (`resumen`); el detalle
    completo vive en el informe, para que las dos piezas no repitan contenido."""
    tipo = (h.get("tipo") or "[MEDIDO]").strip("[]").lower()
    cls = {"medido": "tag-medido", "inferible": "tag-inferible"}.get(tipo, "tag-noverif")
    prio = (h.get("prioridad") or "").strip().lower()
    prio_tag = (f'<span class="tag tag-prio-{esc(prio)}">Prioridad {esc(prio)}</span>'
                if prio else "")
    # La propuesta titula corto (`tituloCorto`); el informe conserva el título largo.
    # Con el mismo texto en las dos piezas, el vocabulario se repetía entre documentos.
    base_titulo = h.get("tituloCorto") or h.get("titulo")
    titulo = f"{idx}. {base_titulo}" if idx else str(base_titulo)
    medido = h.get("resumen") or h.get("descripcion")
    # §4: la propuesta usa una consecuencia redactada para ella (`significa`); el
    # informe usa la suya (`impacto`). Si coincidieran, las piezas repetirían contenido.
    significa = h.get("significa") or h.get("impacto")
    propongo = h.get("propongo") or "[a definir]"
    return f"""
    <div class="finding">
      <div class="finding-head">
        <span class="tag {cls}">{esc(h.get('tipo') or '[MEDIDO]')}</span>
        {prio_tag}
        <span class="finding-title">{esc(titulo)}</span>
      </div>
      <p><strong>Medido:</strong> {esc(medido)}</p>
      <p><strong>Qué significa:</strong> {esc(significa)}</p>
      <p><strong>Qué propongo:</strong> {esc(propongo)}</p>
    </div>"""


def compare_table(comp: dict) -> str:
    # §6.2 del spec editorial: cuando no hay colegas medidos el mismo día con la misma
    # herramienta, NO va tabla (y menos una «Agencia vs Esta propuesta», §6.1): van tres
    # bullets resumen. La tabla se reserva para datos comparables de verdad.
    bullets = comp.get("bullets")
    if bullets and not comp.get("filas"):
        return ('<ul class="comp-bullets">'
                + "".join(f"<li>{esc(b)}</li>" for b in bullets) + "</ul>")
    cols = comp.get("columnas", [])
    head = "<thead><tr>" + "".join(f"<th>{esc(c)}</th>" for c in cols) + "</tr></thead>"
    rows = []
    for fila in comp.get("filas", []):
        celdas = []
        for i, c in enumerate(fila.get("celdas", [])):
            txt = str(c)
            cls = ""
            if i > 0:
                if re.match(r"^(200|✓)", txt):
                    cls = "ok"
                elif re.search(r"✗|404|0$|no resuelve|bloqueó", txt):
                    cls = "bad"
                elif txt == "—":
                    cls = "meh"
            # data-col: en mobile la tabla se convierte en bullets y cada celda
            # necesita decir de qué columna viene (§6.2 condición 4).
            etiqueta = f' data-col="{esc(cols[i])}"' if i < len(cols) else ""
            celdas.append(f'<td class="{cls}"{etiqueta}>{esc(txt)}</td>')
        rowcls = "row-client" if fila.get("cliente") else ""
        rows.append(f'<tr class="{rowcls}">' + "".join(celdas) + "</tr>")
    return f'<table class="compare-table">{head}<tbody>' + "".join(rows) + "</tbody></table>"


def alcance_item(texto: str) -> str:
    """El alcance declara qué se miró (✓) y qué no (✗). La marca la pone la config."""
    t = str(texto).strip()
    if t.startswith("✓"):
        marca, resto, cls = "✓", t[1:].strip(), "yes"
    elif t.startswith("✗"):
        marca, resto, cls = "✗", t[1:].strip(), "no"
    else:
        marca, resto, cls = "·", t, "no"
    return f'<li><span class="{cls}">{marca}</span> {esc(resto)}</li>'


def kpi_row(kpis: list, excluir: str = "") -> str:
    """§4.1 del spec editorial: máximo 4 números en el cuadro.

    `excluir` saca el número que ya va gigante en el hero: repetir el mismo
    dato dos veces en la misma pantalla le baja el peso a los dos.
    """
    kpis = [
        k for k in list(kpis)
        if str(k.get("valor", "")).strip() != str(excluir).strip()
    ][:4]
    if not kpis:
        return ""
    items = "".join(
        f'<div class="kpi"><span class="kpi__value">{esc(k.get("valor"))}</span>'
        f'<span class="kpi__label">{esc(k.get("label"))}</span></div>'
        for k in kpis
    )
    return f'<div class="kpi-row">{items}</div>'


def scenarios(base: int, modulos: list) -> list:
    """Mismos escenarios que calcula el paginador. Se derivan, no se escriben.

    Con el catálogo único el «Recomendado» dejó de ser «los tres primeros»: es
    exactamente el subconjunto que el config marcó como recomendado.
    """
    recs = [m for m in modulos if m.get("recomendado")] or modulos[:3]
    prices = [int(m.get("price", 0)) for m in modulos]
    total = base + sum(prices)
    codes = [m.get("code", "") for m in recs]
    return [
        ("Entrada", "Base sola", base),
        ("Recomendado", f"Base + {len(codes)} add-ons ({', '.join(codes)})",
         base + sum(int(m.get("price", 0)) for m in recs)),
        ("Pack completo", f"Base + los {len(modulos)} add-ons del catálogo", total),
    ]


def seccion(cfg: dict, clave: str):
    """Un bloque de secciones.json, pisable desde la config (propuesta.<clave>).

    El texto vive en datos, no en la plantilla: así el mismo motor sirve para otro
    cliente sin editar HTML.
    """
    override = (cfg.get("propuesta") or {}).get(clave)
    return override if override is not None else SECCIONES.get(clave)


def indice_html(items) -> str:
    if not items:
        return ""
    lis = "".join(f'<li><a href="{esc(h)}">{esc(t)}</a></li>' for t, h in items)
    return f'<ol class="toc-prop">{lis}</ol>'


def glosario_html(g) -> str:
    if not g or not g.get("items"):
        return ""
    cards = "".join(
        f'<div class="glos-card">'
        f'<div class="glos-sigla">{esc(i.get("sigla"))}</div>'
        f'<h3>{esc(i.get("titulo"))}</h3><p>{esc(i.get("body"))}</p></div>'
        for i in g["items"]
    )
    nota = f'<p class="evsrc">{esc(g.get("nota"))}</p>' if g.get("nota") else ""
    return f'<p>{esc(g.get("intro", ""))}</p><div class="grid-3">{cards}</div>{nota}'


def etapas_html(items) -> str:
    if not items:
        return ""
    return "".join(
        f'<div class="etapa"><div class="etapa-cuando">{esc(e.get("cuando"))}</div>'
        f'<h3>{esc(e.get("titulo"))}</h3><p>{esc(e.get("body"))}</p></div>'
        for e in items
    )


def lista_titulada(bloque, default_titulo: str = "") -> str:
    """Bloque {titulo|intro, items, nota|cierre}.

    `items` acepta las dos formas que usa secciones.json:
      - pares       [["Mitad y mitad", "Mitad al confirmar..."], ...]   (pago)
      - objetos     [{"titulo": "...", "body": "..."}, ...]             (valor)
    Sin normalizar, la forma de objeto se desempaqueta como (clave, clave) y el
    documento imprime literalmente «título body»: pasó, y ningún gate lo vio.
    """
    if not bloque:
        return ""
    titulo = bloque.get("titulo") or default_titulo
    head = f"<p><strong>{esc(titulo)}</strong></p>" if titulo else ""
    lis = []
    for it in bloque.get("items", []) or []:
        if isinstance(it, dict):
            lis.append(f'<li><strong>{esc(it.get("titulo"))}</strong> {esc(it.get("body"))}</li>')
        else:
            a, b = it
            lis.append(f"<li><strong>{esc(a)}</strong> {esc(b)}</li>")
    cola = bloque.get("nota") or bloque.get("cierre")
    tail = f'<p class="evsrc">{esc(cola)}</p>' if cola else ""
    return f"{head}<ul>{''.join(lis)}</ul>{tail}"


def valor_html(v) -> str:
    return lista_titulada(v)


def wordpress_html(w, stack_actual: str) -> str:
    """La banda de WordPress sólo entra si el sitio actual del cliente lo es.

    No se afirma sobre un stack que no se midió: el dato lo pone la config.
    """
    if not w:
        return ""
    aplica = (w.get("aplica") or "").strip().lower()
    if not stack_actual or aplica not in stack_actual.strip().lower():
        return ""
    items = "".join(
        f"<li><strong>{esc(a)}</strong> {esc(b)}</li>" for a, b in w.get("items", [])
    )
    return (f'<p>{esc(w.get("intro", ""))}</p><ul>{items}</ul>'
            f'<p class="evsrc">{esc(w.get("cierre", ""))}</p>')


def brand_override(cfg: dict) -> str:
    """El color de marca del cliente pisa el default del sistema de diseño.
    Un solo color en la config: el hover y el fondo suave se derivan."""
    color = ((cfg.get("branding") or {}).get("colorPrimario") or "").strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", color):
        return ""

    def mezclar(hexc: str, hacia: str, t: float) -> str:
        a = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(hacia[i:i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{int(round(x + (y - x) * t)):02X}" for x, y in zip(a, b))

    return (
        "\n/* Identidad del cliente: el color lo pone su config, no el sistema */\n"
        ":root {\n"
        f"  --brand-default: {color};\n"
        f"  --brand-hover:   {mezclar(color, '#000000', 0.16)};\n"
        f"  --brand-soft:    {mezclar(color, '#FFFFFF', 0.92)};\n"
        "}\n"
    )


# Tratamientos que no cuentan como nombre propio: «Lic. Yamila Titonel» da las
# iniciales YT, no LYT. Mismo criterio que el slug del archivo PDF, para que la
# referencia del folio y el nombre del archivo no se contradigan.
HONORIFICOS = ("lic", "dr", "dra", "sr", "sra")


def palabras_nombre(nombre: str) -> list:
    """Las palabras del nombre del cliente, sin el tratamiento."""
    return [
        p for p in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", nombre or "")
        if p.lower() not in HONORIFICOS
    ]


def folio_data(cfg: dict, titulo: str) -> dict:
    """Datos del folio (la línea de expediente del membrete).

    `titulo` es el nombre del DOCUMENTO, no del cliente: el folio del informe
    dice «INFORME DE AUDITORÍA» y el de la propuesta «PROPUESTA COMERCIAL».
    Importa que sean distintos y que no repitan el nombre de una sección: el
    membrete se repite en cada hoja, así que un título que contenga «Diagnóstico»
    aparece ANTES del «Resumen Ejecutivo» y el chequeo de orden de secciones
    del PDF lo lee como una sección adelantada.

    El resto se DERIVA de la config y se puede pisar desde `cfg.folio`: la
    referencia sale de las iniciales del cliente + el año, y el mes del texto
    de la fecha. Así el folio existe sin pedirle un dato más al cliente.
    """
    meta = cfg.get("meta") or {}
    folio = cfg.get("folio") or {}

    # Sin el tratamiento: «Lic. Lisandro Lagos» tiene que dar LL, no LLL.
    iniciales = "".join(p[0] for p in palabras_nombre(meta.get("nombre")))[:3].upper() or "XX"

    fecha = (meta.get("fecha") or "").strip()
    m = re.search(r"\b(\d{4})\b", fecha)
    anio = m.group(1) if m else ""

    mes = ""
    for nombre_mes in ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                       "agosto", "septiembre", "octubre", "noviembre", "diciembre"):
        if nombre_mes in fecha.lower():
            mes = nombre_mes.upper()
            break

    return {
        "FOLIO_REF": esc((folio.get("ref") or f"{iniciales}-{anio}").strip()),
        "FOLIO_VERSION": esc(str(folio.get("version") or "V1.0").strip()),
        "FOLIO_TITULO": esc(str(folio.get("titulo") or titulo).strip()),
        "FOLIO_FECHA": esc((f"{mes} {anio}".strip() or fecha.upper())),
        "FOLIO_EJEMPLAR": esc(str(folio.get("ejemplar") or "01").strip()),
    }


# Anclas de sección que la plantilla de propuesta numera. El número sale del
# índice (secciones.json); acá viven sólo los nombres de las anclas, para poder
# emitir el slot aunque una sección no esté listada en el índice.
ANCLAS_PROPUESTA = [
    "evidencia", "sitio-nuevo", "comparativo", "propuesta", "pago", "valor",
    "glosario", "wordpress", "etapas", "cierre", "aceptacion",
]


def eyebrows(cfg: dict) -> dict:
    """Numeración de los eyebrows: «01 · Tu situación hoy».

    El número NO se escribe en la plantilla: sale del índice, que ya es la
    fuente única del orden de las secciones. Importa porque el orden del DOM
    NO es el del índice (la propuesta muestra el resultado antes que el
    problema, §3.4), así que un contador por orden daría números cruzados.
    """
    numeros = {}
    for i, par in enumerate(seccion(cfg, "indice") or [], 1):
        try:
            ancla = str(par[1])
        except (TypeError, IndexError):
            continue
        numeros[ancla.lstrip("#")] = f"{i:02d} / "

    return {f"EB_{a}": esc(numeros.get(a, "")) for a in ANCLAS_PROPUESTA}


def hero_stat_valor(cfg: dict) -> str:
    """El número que va gigante en el hero, crudo (sin escapar)."""
    prop = cfg.get("propuesta") or {}
    kpis = (cfg.get("comparativo") or {}).get("kpis") or []
    return str(
        (prop.get("heroStat") or {}).get("valor")
        or (kpis[0].get("valor") if kpis else "")
        or ""
    )


def hero_stat(cfg: dict) -> dict:
    """Slots de la métrica gigante: valor, leyenda y pie.

    Sale de `cfg.propuesta.heroStat`; si no está declarado, cae al primer KPI
    del comparativo. El pie es opcional (queda vacío si no se declara).
    """
    prop = cfg.get("propuesta") or {}
    hs = prop.get("heroStat") or {}
    kpis = (cfg.get("comparativo") or {}).get("kpis") or []
    base = kpis[0] if kpis else {}
    return {
        "HERO_STAT": esc(hero_stat_valor(cfg)),
        "HERO_STAT_LABEL": esc(str(hs.get("label") or base.get("label") or "")),
        "HERO_STAT_CAPTION": esc(str(hs.get("caption") or "")),
    }


def imagen_uri(path: Path, ancho: int = 900, calidad: int = 72) -> str:
    """Embebe una imagen como data URI JPEG, redimensionada. Sin red, sin archivos sueltos."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if im.width > ancho:
        alto = round(im.height * ancho / im.width)
        im = im.resize((ancho, alto), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=calidad, optimize=True, progressive=True)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{data}"


def fuentes_css() -> str:
    """@font-face con las tipografias embebidas como data URI.

    Misma logica que las imagenes: sin red y sin archivos sueltos, para que el
    PDF salga igual en cualquier maquina. Las dos familias son variables, asi que
    se declaran con un RANGO de peso (`font-weight: 100 900`) apuntando a un solo
    archivo; declararlas por peso con el mismo archivo haria que el navegador
    sintetice el peso y todo salga igual de grueso.

    Si los .woff2 no estan, no rompe: devuelve "" y el CSS cae a la pila del
    sistema (`--font-sans` / `--font-mono` ya la traen).
    """
    familias = [("Inter", "Inter"), ("JetBrains Mono", "JetBrainsMono")]
    bloques = []
    for nombre_css, archivo in familias:
        ruta = BRAND / "assets" / "fonts" / f"{archivo}.woff2"
        if not ruta.exists():
            continue
        b64 = base64.b64encode(ruta.read_bytes()).decode("ascii")
        bloques.append(
            f"@font-face {{\n"
            f"  font-family: '{nombre_css}';\n"
            f"  src: url(data:font/woff2;base64,{b64}) format('woff2-variations');\n"
            f"  font-weight: 100 900;\n"
            f"  font-style: normal;\n"
            f"  font-display: swap;\n"
            f"}}\n"
        )
    return "\n".join(bloques)


def shots_band(cfg: dict) -> str:
    """Banda de antes/después. Sólo se arma si las dos capturas existen."""
    imgs = cfg.get("imagenes") or {}
    antes, despues = imgs.get("antes"), imgs.get("despues")
    if not (antes and despues):
        return ""
    pa, pd = ROOT / antes, ROOT / despues
    if not (pa.exists() and pd.exists()):
        return ""
    cap_antes = imgs.get("captionAntes") or "Hoy — sin los canales y señales que el rubro ya usa"
    cap_despues = imgs.get("captionDespues") or "Propuesta — sitio propio, con tus datos reales y verificados"
    return f"""
<section class="band band--soft">
  <div class="wrap">
    <span class="eyebrow">El cambio, en una mirada</span>
    <h2 style="font-size:1.5rem;margin-top:.75rem">Cómo se ve hoy y cómo se vería</h2>
    <p>Las dos capturas son reales: la de la izquierda es tu sitio actual, tomada el {esc(cfg.get('meta', {}).get('fecha'))};
       la de la derecha es el sitio nuevo, funcionando y verificado.</p>
    <div class="grid-2">
      <div class="shot">
        <img src="{imagen_uri(pa)}" alt="Sitio actual de {esc(cfg.get('meta', {}).get('nombre'))}">
        <div class="shot__cap">{esc(cap_antes)}</div>
      </div>
      <div class="shot">
        <img src="{imagen_uri(pd)}" alt="Propuesta de sitio nuevo para {esc(cfg.get('meta', {}).get('nombre'))}">
        <div class="shot__cap">{esc(cap_despues)}</div>
      </div>
    </div>
  </div>
</section>"""


def sitio_nuevo_html(cfg: dict) -> str:
    """§3.4 y §4: el resultado antes que el problema. Botón directo, SIN captura.

    La captura era un proxy del sitio y jugaba en contra: se ve chica, se corta
    cuando la hoja pagina, y muestra una foto fija de algo que es navegable. El
    que la mira tiene que scrollear hasta el boton igual — o sea que la foto no
    reemplaza al clic, lo posterga.

    Va un solo bloque: el boton grande, y la direccion visible porque el PDF se
    lee tambien en papel. El link queda como anotacion clickeable en el PDF, asi
    que desde el archivo se llega al sitio con un clic.
    """
    m = cfg.get("modelo") or {}
    url = (m.get("url") or "").strip()
    if not url:
        return "<p>[falta configurar el sitio nuevo: config.json → modelo.url]</p>"

    visible = re.sub(r"^https?://", "", url).rstrip("/")
    return f"""
    <p>{esc(m.get("bajada") or "El rediseño ya está construido. No es un boceto.")}</p>
    <div class="portal">
      <span class="label-mono">El sitio nuevo, online</span>
      <p class="portal-lead">{esc(m.get("invitacion") or "Abrilo y recorrélo: es tu sitio, con los cambios ya aplicados.")}</p>
      <a class="btn btn-brand btn-lg" href="{esc(url)}">{esc(m.get("cta") or "Abrir el sitio nuevo")} &rarr;</a>
      <p class="portal-url">{esc(visible)}</p>
    </div>"""


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--informe", default="00-auditoria/informe.html")
    ap.add_argument("--propuesta", default="01-propuesta/propuesta.html")
    args = ap.parse_args()

    config_path = ROOT / args.config
    if not config_path.exists():
        print(f"ERROR: no existe {config_path}")
        return 1

    cfg = json.loads(read(config_path))
    meta = cfg.get("meta", {})
    author = cfg.get("author", {})
    hallazgos = cfg.get("hallazgos", [])
    modulos = cfg.get("modulos", [])
    pasos = cfg.get("nextSteps", [])
    comp = cfg.get("comparativo", {})
    base = int(cfg.get("base", {}).get("precio", 0))
    base_items = cfg.get("base", {}).get("items", [])

    costo_mensual = cfg.get("costoMensual", "[NO DECLARADO]")
    base_calculo = cfg.get("baseCalculo", "[NO DECLARADO]")
    comparativos = str(cfg.get("comparativos", 0))
    total_all = base + sum(int(m.get("price", 0)) for m in modulos)

    # ---- marca y fragmentos compartidos
    # Las fuentes van primero: los tokens de brand.css las referencian por nombre.
    brand_css = fuentes_css() + read(BRAND / "brand.css") + brand_override(cfg)
    print_css = read(TEMPLATES / "print.css")
    logo_svg = read(BRAND / "assets" / "logo.svg")

    def armar_header(titulo_doc: str) -> str:
        """El membrete es el mismo para las dos piezas, salvo el título del
        documento: el folio del informe y el de la propuesta no dicen lo mismo."""
        return render(read(BRAND / "header.html"), {
            "LOGO_SVG": logo_svg,
            "DOC_TITLE": esc(meta.get("nombre", "")),
            **folio_data(cfg, titulo_doc),
        })

    header_informe = armar_header("INFORME DE AUDITORÍA")
    header_propuesta = armar_header("PROPUESTA COMERCIAL")
    footer = render(read(BRAND / "footer.html"), {
        "FOOTER_META": esc(
            f"{author.get('nombre', 'Lisandro Cacciatore')} · Consultor de IA"
            f" · {meta.get('fecha', '')}"
        ),
    })

    common = {
        "BRAND_CSS": brand_css,
        "HEADER": header_informe,
        "FOOTER": footer,
        "NOMBRE_CLIENTE": esc(meta.get("nombre")),
        "NOMBRE_CLIENTE_ENCODED": esc(meta.get("nombre", "")).replace(" ", "%20"),
        "PROFESION": esc(meta.get("profesion")),
        "MATRICULA": esc(meta.get("matricula")),
        "RUBRO": esc(meta.get("rubro")),
        "FECHA": esc(meta.get("fecha")),
        "VALIDEZ": esc(meta.get("validez")),
        "URL_CLIENTE": esc(meta.get("url")),
        "META_URL": esc(meta.get("url")),
        "AUTHOR_NOMBRE": esc(author.get("nombre")),
        "AUTHOR_EMAIL": esc(author.get("email")),
        "NUM_HALLAZGOS": str(len(hallazgos)),
        "NUM_COMPARATIVOS": comparativos,
        "COSTO_MENSUAL": esc(costo_mensual),
        "BASE_CALCULO": esc(base_calculo),
        "PRECIO_BASE": str(base),
        "TOTAL": str(total_all),
        "PASOS_HTML": "".join(f"<li>{esc(p)}</li>" for p in pasos),
        "BASE_ITEMS_HTML": "".join(f"<li>{esc(i)}</li>" for i in base_items),
        "ALCANCE_HTML": "".join(alcance_item(a) for a in cfg.get("alcance", [])),
        # §7.2 del spec editorial: los límites se separan en lo que medí (✓) y lo que no
        # pude medir (✗), en una sola sección en vez de tres sueltas.
        "MEDIDO_HTML": "".join(alcance_item(a) for a in cfg.get("alcance", [])
                               if str(a).strip().startswith("✓")),
        "NO_MEDIDO_HTML": "".join(alcance_item(a) for a in cfg.get("alcance", [])
                                  if not str(a).strip().startswith("✓")),
        "PREGUNTAS_HTML": "".join(f"<li>{esc(p)}</li>" for p in cfg.get("preguntasAbiertas", [])),
        "SIN_INCLUIR_HTML": "".join(f"<li>{esc(p)}</li>" for p in cfg.get("sinIncluir", [])),
        "MODULOS_JSON": json.dumps(modulos, ensure_ascii=False),
        "KPI_HTML": kpi_row(comp.get("kpis", [])),
        # acceso directo -> no se usa en el informe, sí en la propuesta
        "HALLAZGOS_HTML": "".join(finding_card(h, i) for i, h in enumerate(hallazgos, 1)),
    }

    # ---- propuesta: bloques propios
    conv = cfg.get("conversion") or {}
    prop = cfg.get("propuesta") or {}
    callout = cfg.get("callout") or {}
    modelo = cfg.get("modelo") or {}
    saludo = prop.get("saludo") or (meta.get("nombre", "").split()[-1] or "")
    nombre_enc = esc(meta.get("nombre", "")).replace(" ", "%20")
    saludo_enc = str(saludo).replace(" ", "%20")

    def narrativa(clave: str, default: str) -> str:
        """Texto narrativo de la propuesta: lo escribe la config, no la plantilla."""
        return str(prop.get(clave) or default)

    propuesta_data = dict(common)
    propuesta_data["HEADER"] = header_propuesta
    propuesta_data.update(eyebrows(cfg))
    propuesta_data.update(hero_stat(cfg))
    # El KPI que va gigante en el hero se saca de la fila de indicadores:
    # es el mismo número y no se muestra dos veces en la misma pantalla.
    propuesta_data["KPI_HTML"] = kpi_row(comp.get("kpis", []), excluir=hero_stat_valor(cfg))
    propuesta_data.update({
        "HERO_TITULO": narrativa(
            "heroTitulo",
            "Tu sitio le pide a la gente que te escriba por WhatsApp.<br>Y no tiene WhatsApp."),
        "HERO_LEAD": narrativa(
            "heroLead",
            f"{esc(meta.get('nombre'))}: medí tu sitio y medí los {comparativos} sitios de "
            f"referencia del mismo rubro, con la misma herramienta y el mismo día. Esto no es una "
            f"opinión sobre tu diseño: son {len(hallazgos)} cosas medidas, cada una con el número que la respalda."),
        "COMPARATIVO_TITULO": narrativa("comparativoTitulo", "Tu categoría, medida el mismo día"),
        "COMPARATIVO_CIERRE": narrativa(
            "comparativoCierre",
            "No estás solo: el problema es del conjunto. La mejora más barata del rubro "
            "y todavía nadie la levantó."),
        # §11 del spec editorial: «Lo que dice esta tabla, en una línea» se elimina si
        # no hay tabla o si no aporta. El bloque entero es opcional.
        "COMPARATIVO_CIERRE_BLOCK": (
            '<div class="todo" style="margin-top:1.25rem">'
            "<strong>Lo que dice esto, en una línea:</strong>"
            f'<p style="margin:.5rem 0 0">{esc(narrativa("comparativoCierre", ""))}</p>'
            "</div>" if narrativa("comparativoCierre", "") else ""),
        "COSTO_NOTA": narrativa("costoNota", "en la llamada lo validamos con tus números reales, que yo no veo."),
        "PROPUESTA_TITULO": narrativa("propuestaTitulo", "Un sitio tuyo, y los add-ons que quieras sumar"),
        "PROPUESTA_INTRO": narrativa(
            "propuestaIntro",
            "La base es no depender más de una plataforma de terceros: sitio propio, tus datos reales "
            "y las señales que Google necesita para mostrarte. Los add-ons se suman según lo que más "
            "te duela y según el presupuesto. Están todos a la vista: tildá los que quieras."),
        "BASE_LABEL": narrativa("baseLabel", "Base — Sitio profesional propio"),
        "PREGUNTAS_TITULO": narrativa("preguntasTitulo", "Datos que no puedo inventar"),
        "CIERRE_TITULO": narrativa("cierreTitulo", "Una llamada de veinte minutos"),
        "CIERRE_BODY": narrativa(
            "cierreBody",
            "No hace falta que decidas nada por mensaje. Veinte minutos alcanzan para revisar los "
            "hallazgos, contestar las preguntas y elegir por dónde empezar."),
        "CALLOUT_LABEL": callout.get("label") or "Costo de no hacer nada",
        "CALLOUT_STRONG": callout.get("strong") or f"Seguir así cuesta {costo_mensual} por mes.",
        "CALLOUT_NOTE": callout.get("note") or (
            f"Cálculo: {esc(base_calculo)} · [INFERIBLE] — " + narrativa(
                "costoNota", "en la llamada lo validamos con tus números reales, que yo no veo.")),
        "SITIO_NUEVO_HTML": sitio_nuevo_html(cfg),
        "MODELO_CTA_HTML": (
            # Sin target="_blank": en el panel de previsualización (y en webviews) la
            # apertura de ventanas nuevas se bloquea en silencio y el clic no hace nada.
            f'<a class="btn btn-light" href="{esc(modelo.get("url"))}" rel="noopener">'
            f'{esc(modelo.get("cta") or "Ver la página modelo")} &nearr;</a>'
            if (modelo.get("url") or "").strip() else ""
        ),
        "MAILTO_INTERESA": (
            f"mailto:{esc(author.get('email'))}?subject=Propuesta%20-%20{nombre_enc}"
            f"&body=Hola%20{saludo_enc}%2C%20me%20interesa%20avanzar%20con%3A%20"),
        "MAILTO_AVANZAR": (
            f"mailto:{esc(author.get('email'))}?subject=Propuesta%20-%20{nombre_enc}"
            f"&body=Hola%20{saludo_enc}%2C%20quiero%20avanzar%20con%3A%20"),
        # §9: los dos CTA de la propuesta, como botones, con asunto predefinido.
        "MAILTO_LLAMADA": (
            f"mailto:{esc(author.get('email'))}?subject=Hablemos%20sobre%20mi%20sitio"
            f"&body=Hola%2C%20quiero%20agendar%20la%20llamada%20de%2020%20minutos."),
        "MAILTO_ACEPTAR": (
            f"mailto:{esc(author.get('email'))}?subject="
            f"Acepto%20la%20propuesta%20-%20{nombre_enc}"
            f"&body=Hola%2C%20acepto%20la%20propuesta.%20Arrancamos."),
        "COMPARATIVO_HTML": compare_table(comp),
        "COMPARATIVO_INTRO": esc(comp.get("intro", "")),
        "COMPARATIVO_NOTA": esc(comp.get("nota", "")),
        "COMPARATIVO_FUENTE": esc(
            f"Medición propia del {comp.get('medidoEl', '')} · reproducible con: "
            "python scripts/medir.py --pares 00-auditoria/pares.txt"
        ),
        "ESCENARIOS_HTML": "".join(
            f"<li><strong>{esc(n)}:</strong> {esc(d)} — <strong>{money(u)}</strong></li>"
            for n, d, u in scenarios(base, modulos)
        ),
        # §10 del spec editorial: al lado de la tabla, la línea del recomendado.
        # Con el catálogo único el recomendado son TODOS los marcados, no los tres primeros.
        "RECOMENDADO_LINE": (
            "Recomendado para tu caso: Base + " +
            " + ".join(str(m.get("code")) for m in modulos if m.get("recomendado")) +
            f" = {money(base + sum(int(m.get('price', 0)) for m in modulos if m.get('recomendado')))}."
            if any(m.get("recomendado") for m in modulos) else ""),
        "N_RECOMENDADOS": str(sum(1 for m in modulos if m.get("recomendado"))),
        "N_CATALOGO": str(len(modulos)),

        # ---- Secciones nuevas (documento aprobado 3/10). El texto vive en
        # templates/secciones.json y cada cliente puede pisarlo desde su config.
        "INDICE_HTML": indice_html(seccion(cfg, "indice")),
        "GLOSARIO_HTML": glosario_html(seccion(cfg, "glosario")),
        "ETAPAS_HTML": etapas_html(seccion(cfg, "etapas")),
        "VALOR_HTML": valor_html(seccion(cfg, "valor")),
        "NO_WORDPRESS_HTML": wordpress_html(
            seccion(cfg, "noWordpress"), cfg.get("stackActual") or ""),
        "PAGO_HTML": lista_titulada(seccion(cfg, "pago")),
        "CONDICIONES": esc(seccion(cfg, "condiciones") or ""),

        "SHOTS_BAND": shots_band(cfg),
        "WHATSAPP_CTA_HTML": (
            f'<a class="btn btn-wa" href="https://wa.me/{esc(author.get("whatsapp"))}'
            f'?text=Hola%2C%20vi%20la%20propuesta%20para%20{nombre_enc}" rel="noopener">'
            'Responder por WhatsApp</a>' if author.get("whatsapp") else ""
        ),
    })

    # ---- informe: shell + paginador
    def js_json(obj) -> str:
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    informe_data = dict(common)
    informe_data.update({
        "PRINT_CSS": print_css,
        "CONFIG_JSON": js_json(cfg),
        "HEADER_JSON": js_json(header_informe),
        "FOOTER_JSON": js_json(footer),
        "PAGINATOR_JS": read(TEMPLATES / "print.js"),
    })

    informe_html = render(read(TEMPLATES / "informe.html"), informe_data)
    propuesta_html = render(read(TEMPLATES / "propuesta.html"), propuesta_data)

    out_informe = ROOT / args.informe
    out_propuesta = ROOT / args.propuesta
    out_informe.parent.mkdir(parents=True, exist_ok=True)
    out_propuesta.parent.mkdir(parents=True, exist_ok=True)
    out_informe.write_text(informe_html, encoding="utf-8")
    out_propuesta.write_text(propuesta_html, encoding="utf-8")

    # ---- verificación: se relee de disco, se valida el archivo real
    errores = []
    producidos = {
        "informe": out_informe.read_text(encoding="utf-8"),
        "propuesta": out_propuesta.read_text(encoding="utf-8"),
    }

    for name, text in producidos.items():
        left = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
        if left:
            errores.append(f"{name}: placeholders sin resolver -> {left}")

    for name, text in producidos.items():
        if "--brand-default" not in text:
            errores.append(f"{name}: falta el CSS de marca inyectado")
        if "brand-header" not in text or "brand-footer" not in text:
            errores.append(f"{name}: falta el membrete o el pie compartido")

    if PRINT_JS_MARKER not in producidos["informe"]:
        errores.append("informe: el paginador no se inyectó")

    m_inj = re.search(r"window\.CLIENT_CONFIG = (\{.*?\});", producidos["informe"], re.S)
    if not m_inj:
        errores.append("informe: no pude leer la config inyectada")
    else:
        try:
            inj = json.loads(m_inj.group(1).replace("<\\/", "</"))
            inj_total = int(inj.get("base", {}).get("precio", 0)) + sum(
                int(m.get("price", 0)) for m in inj.get("modulos", [])
            )
            if inj_total != total_all:
                errores.append(f"config inyectada suma {inj_total} y el generador calculó {total_all}")
        except Exception as e:  # noqa: BLE001
            errores.append(f"informe: la config inyectada no es JSON válido ({e})")

    for m in modulos:
        if m.get("title") and m["title"] not in producidos["informe"]:
            errores.append(f"módulo '{m['title']}' falta en el informe")
        if m.get("code") and f'"{m["code"]}"' not in producidos["propuesta"]:
            errores.append(f"módulo {m['code']} falta en el selector de la propuesta")

    # El total de la propuesta tiene que aparecer calculado, no escrito a mano.
    if f"USD {base}" not in producidos["propuesta"]:
        errores.append("propuesta: el total inicial no coincide con el precio base")

    # Cada hallazgo tiene que haber entrado con su prioridad visible.
    for h in hallazgos:
        if (h.get("prioridad") or "").lower() not in producidos["propuesta"].lower():
            errores.append(f"propuesta: hallazgo sin prioridad visible -> {h.get('titulo')[:40]}")
            break

    print("=" * 68)
    print(f"  GENERANDO LEAD: {meta.get('nombre')}")
    print("=" * 68)
    print(f"  hallazgos        : {len(hallazgos)}")
    print(f"  módulos          : {len(modulos)}")
    print(f"  comparativo      : {len(comp.get('filas', []))} filas")
    print(f"  base             : {money(base)}")
    print(f"  pack completo    : {money(total_all)}")
    print(f"  informe          : {out_informe.relative_to(ROOT)}")
    print(f"  propuesta        : {out_propuesta.relative_to(ROOT)}")
    print("-" * 68)
    if errores:
        print("  ✗ VERIFICACIÓN FALLÓ")
        for e in errores:
            print(f"      - {e}")
        return 2
    print("  ✓ Sin placeholders sin resolver")
    print(f"  ✓ Config inyectada válida y consistente (total {money(total_all)})")
    print(f"  ✓ Paginador inyectado · {len(modulos)} módulos · {len(hallazgos)} hallazgos")
    print("  ✓ CSS de marca, membrete y pie en las dos piezas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
