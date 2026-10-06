# motor-leads

Motor de auditorías y propuestas comerciales para profesionales.
Este repo es la **plantilla**: cada lead es una copia (`~/lead-<cliente>`).

---

## El estándar

Un entregable son **dos piezas**, y se genera con **un comando**:

```bash
bash scripts/verificar-todo.sh
```

Las reglas de fondo están en los dos specs, que son la fuente de verdad:
**`SPEC-workflow-audit-propuesta.md`** (orden, precios, promesas) y
**`SPEC-editorial.md`** (tono, patrones, tipografía).

| Pieza | Qué es | Dónde |
|---|---|---|
| **Informe de Valor** | solo diagnóstico, **sin precios** (§4 del spec) | `00-auditoria/informe-<slug>.pdf` |
| **Propuesta** | oferta: base + módulos + escenarios, en USD | `01-propuesta/propuesta-<slug>.pdf` |

Si ese comando sale en verde, el entregable es publicable.
Si algo falla, **no hay entregable** — y no se manda "casi".

Ese script corre los seis gates en orden y resume al final, así que un rojo
temprano no esconde los demás:

```
1/6  construir          generate + precios + render
2/6  spec del workflow  orden, promesas de base, fechas, solo USD
3/6  spec editorial     tono, patrón de hallazgos, mobile, tipografía
4/6  promesas           lo prometido contra el sitio publicado
5/6  PDF del informe    hojas, membrete repetido, sin precios
6/6  PDF de la propuesta
```

`generar.sh` suelto solo **construye**: sirve para iterar contenido sin pagar
el costo de los seis gates. No exporta PDF y no reclama que el documento esté
bien.

---

## Las reglas de diseño (no se tocan por cliente)

La identidad vive en **`brand/brand.css`** — fuente única. Ningún template
declara colores, fuentes ni medidas propias.

**Dos roles de color, no uno.** `--navy` es la **estructura** (títulos, reglas,
botones, membrete) y es fija: es la identidad del expediente. El **acento** es
lo que señala (eyebrows, métricas, badges) y lo puede pisar el cliente desde
`branding.colorPrimario` de su config. Si el acento del cliente es casi el mismo
navy, **queda invisible**: hay que compararlos antes de publicar.

**El documento es de quien lo firma.** El membrete, el pie y el acento son la
identidad de Lisandro; la marca del cliente va *adentro*, en lo que se muestra.

**Las fuentes van embebidas como data URI** (`scripts/bajar-fuentes.py`), igual
que las imágenes. Sin red y sin archivos sueltos: el PDF sale igual en cualquier
máquina. Inter y JetBrains Mono son **variables** — Google devuelve el mismo
archivo para cada peso, así que se guarda uno por familia y se declara con un
rango (`font-weight: 100 900`). Declararlas por peso hace que el navegador
sintetice el peso y salga todo igual de grueso.

**Cero border-radius, sin sombras.** El lenguaje es editorial, no de app.

**El sitio nuevo va con botón, no con captura.** Vale para las **dos** piezas:
la propuesta y la home del preview. La captura se ve chica, se corta al paginar
y no reemplaza al clic: el que la mira igual tiene que scrollear hasta el botón.
Va el bloque `.portal` (definido en `brand.css`, así las dos piezas no se
separan) con el botón grande y la dirección visible. El link viaja como anotación
clickeable en el PDF. **Nunca un `<iframe>`**: Chrome no los imprime y queda un
recuadro vacío; y en la home además trae su propio layout y su propio CSS.

**El membrete se repite en cada hoja.** Cualquier palabra del folio que también
sea nombre de sección rompe el chequeo de orden de secciones del PDF.

---

## Cómo nace un lead

```bash
cp -r ~/motor-leads ~/lead-<cliente>          # o usar scripts/nuevo-lead.py
python scripts/nuevo-lead.py --url <sitio>    # mide el sitio y arma el borrador
```

Después se redacta `config.json` (hallazgos con el patrón §5, narrativa, precios)
y se corre `bash scripts/verificar-todo.sh`.

### Dónde vive cada cosa

| Qué | Dónde | Nota |
|---|---|---|
| Precios de los add-ons | `templates/catalogo.json` | **fuente única**. Se materializa con `sincronizar-catalogo.py` |
| Textos compartidos (índice, glosario, etapas, pago) | `templates/secciones.json` | un cliente los puede pisar desde su config |
| Datos y narrativa del cliente | `config.json` | hallazgos, KPIs, escenarios, promesas |
| Identidad visual | `brand/brand.css` | dos roles de color, fuentes, cero radio |
| Plantillas | `templates/*.html` | estructura, no datos |

---

## Lo que NO hay que hacer

Errores que ya nos costaron una corrida, en orden de frecuencia:

- **Pisar el template para cambiar contenido.** El contenido va en
  `config.json` o `secciones.json`. Tocar el template rompe a todos los leads.
- **Confiar en el total.** Un total que cierra no dice nada sobre los precios de
  línea: tres precios mal pueden **cancelarse entre sí** y dar el total correcto.
  Por eso existe `verificar-precios.py`.
- **Poner `break-inside: avoid` en cada sección.** Una sección que no entra se va
  entera a la hoja siguiente y deja media hoja en blanco. Las bandas fluyen; lo
  atómico (tarjetas, capturas, KPIs) se marca pieza por pieza.
- **Numerar secciones con un contador de CSS.** Numera por orden del DOM, y el
  índice no sigue ese orden (la propuesta muestra el resultado antes que el
  problema, §3.4). El número sale del índice.
- **Poner `white-space: nowrap` en el membrete o en una fecha.** Desborda la
  pantalla angosta. Está medido: 168 px.
- **Publicar con datos de relleno.** Testimonios, teléfonos o métricas de
  maqueta en un documento que va a un cliente: no.
- **Datos que vienen de otra IA.** Un mockup o una spec de un tercero trae
  números inventados y arquitecturas que reinventan lo que ya existe. Se porta la
  **idea**; cada número se verifica contra la fuente antes de entrar.

---

## Verificación

`verificar-todo.sh` es la puerta. Si querés mirar el detalle:

```bash
python scripts/diagnostico-desborde.py 01-propuesta/propuesta.html 512   # qué desborda
python scripts/movil.py                                                  # capturas mobile
python scripts/consolidar-evidencia.py                                   # evidencia machine-readable
python -c "import pypdf; ..."                                            # hojas, texto, links del PDF
```

Y **mirá las hojas**. Renderizá el PDF a imágenes y revisá con visión: los
defectos que aparecieron **solo** así fueron una métrica partida en dos líneas,
una bandera tapando un precio, hojas medio vacías y una referencia de folio
tomada del tratamiento del nombre (`LLL` por «Lic. Lagos`).
