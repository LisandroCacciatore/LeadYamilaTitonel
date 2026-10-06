---
workflow: hermes-audit-propuesta
version: 2.0
fecha: 2026-10-05
autor: Lisandro Cacciatore
aplica-a: auditorías y propuestas comerciales para profesionales
estado: activo
---

# Spec de workflow: auditoría → propuesta comercial

Este documento define cómo se construyen, ordenan y publican las auditorías y propuestas comerciales para profesionales. Reemplaza el workflow anterior. Toda generación futura debe cumplir este spec sin excepciones.

---

## 0. Principios

1. **El resultado antes que el problema.** El lead ve primero cómo se vería su sitio nuevo, después lee el diagnóstico y la propuesta.
2. **Nada que no se pueda reproducir.** Cada número es `[MEDIDO]`, `[INFERIBLE]` o `[NO VERIFICADO]`. No hay afirmaciones sin etiqueta.
3. **Segunda persona, siempre.** El documento le habla al profesional en "vos". Nunca tercera persona.
4. **Sin datos inventados.** Si no se puede medir, se declara. Si no se conoce la tarifa, no se convierte.
5. **Todo CTA es un botón.** No hay llamadas a la acción en texto plano.
6. **El sitio nuevo pasa su propia auditoría.** Si no la pasa, no se publica.

---

## 1. Orden de presentación

**Antes:** informe → propuesta → (a veces) sitio nuevo.
**Ahora:** sitio nuevo → propuesta → informe (como respaldo).

Flujo de navegación obligatorio:

```
1. Home del lead (/LeadX/)
   → muestra el sitio nuevo arriba de todo
   → CTA principal: "Mirá cómo se vería tu sitio →"
   → CTA secundario: "Ver la propuesta →"
   → Link terciario: "Ver el informe completo →"

2. Propuesta (/LeadX/propuesta/)
   → arranca con el sitio nuevo como prueba
   → sigue con hallazgos resumidos
   → termina en precios y aceptación

3. Informe (/LeadX/informe/)
   → solo diagnóstico, sin precios
   → linkeado desde la propuesta como respaldo
```

**Regla dura:** el sitio nuevo (`/X/`) está linkeado desde el primer scroll de la home del lead, con botón explícito.

---

## 2. Home del lead (`/LeadX/`)

Reemplaza el placeholder actual. Orden exacto:

1. **H1:** `{Nombre del profesional} — Cómo se vería tu sitio`
2. **Subtítulo:** una línea con el gancho específico del caso.
3. **Botón al sitio nuevo:** bloque de portal (botón grande + dirección visible). **Sin captura ni iframe.** La captura se ve chica, se corta al paginar y no reemplaza al clic; el iframe directamente no imprime.
4. **Cuadro de 4-5 números grandes** del diagnóstico.
5. **CTAs:** `Ver la propuesta →` (primario) / `Ver el informe →` (secundario).
6. **Nota técnica** `noindex` / `robots.txt` al pie, colapsable.
7. **Footer:** "Si preferís que no te escriba más, respondé 'no gracias'".

**Eliminar:** "Auditoría medida y propuesta comercial", fecha de medición en el cuerpo principal.

---

## 3. Estructura de la propuesta (`/LeadX/propuesta/`)

Orden exacto:

```
1. Titular con gancho
2. Subtítulo con contexto: "medí X, Y y Z con la misma herramienta y el mismo día"
3. Cuadro de números grandes (4-5)
4. SECCIÓN "Tu sitio nuevo" — botón grande al sitio (bloque `.portal`), sin captura
5. "Lo que encontré" — hallazgos con patrón fijo (ver §5)
6. Tabla comparativa contra colegas (solo si cumple §6)
7. "Lo que dice esta tabla, en una línea"
8. Costo de no hacer nada / Lo que no puedo medir
9. Base + módulos
10. Escenarios
11. Precios (solo en USD, ver §7)
12. Qué no incluye
13. Lo que necesito de vos
14. Próximo paso + CTA
15. Alcance de esta revisión
16. Aceptación y firma
```

**Eliminar del documento:**
- Tabla "Agencia vs Esta propuesta".
- Conversión a pesos.
- Cualquier fecha futura.

---

## 4. Estructura del informe (`/LeadX/informe/`)

Orden exacto:

```
1. Portada: nombre + "Informe de Valor" + fecha real
2. Resumen ejecutivo (con el número más fuerte en titular)
3. Diagnóstico y hallazgos
4. Comparativo verificado
5. Alcance de esta revisión
6. Cierre: "Si querés ver qué propongo, andá a la propuesta →"
```

**Sin precios.** El informe es solo diagnóstico.

**Separación real:** informe y propuesta no comparten más del 30% del contenido. El informe detalla los hallazgos; la propuesta los resume en una línea cada uno.

---

## 5. Patrón de hallazgos

Formato fijo, sin excepciones:

```
[NIVEL] **N. Titular del hallazgo** · Prioridad {alta|media|baja}

**Medido:** {número crudo} sobre {de dónde sale}.
**Qué significa:** {consecuencia para el negocio del lead, 1-2 líneas}.
**Qué propongo:** {módulo Mx o acción concreta}.
```

**Niveles:**
- `[MEDIDO]` — medición reproducible
- `[INFERIBLE]` — estimación marcada
- `[NO VERIFICADO]` — no se pudo comprobar, se declara

**Tono:** segunda persona (vos). Nunca "él publica", "su sitio".

**Titulares:** directos, sin coloquialismos. Prohibido "casa desordenada" o similares. Usar el hallazgo: *"El sitio pesa 3,5 MB por visita y no tiene mapa del sitio"*.

---

## 6. Reglas para tablas comparativas

### 6.1 Tabla "Agencia vs Esta propuesta"

**Eliminar.** Mezcla datos verificados con estimaciones de mercado y confunde.

### 6.2 Tabla contra colegas

**Mantener solo si cumple las 4 condiciones:**

1. Todos los comparables medidos el mismo día con la misma herramienta.
2. Cada celda tiene número crudo o estado verificable (✓/✗/número).
3. Sin columnas vacías ni "sí (2)" sin explicación.
4. En mobile se convierte en bullets, no en tabla scrolleable.

**Si no cumple las 4:** reemplazar por 3 bullets resumen:

> - De 7 colegas con dominio propio, **ninguno** tiene botón de WhatsApp.
> - 3 de los 5 sitios vivos arrastran el mismo error de idioma que el tuyo.
> - 2 de los 7 dominios hoy no resuelven.

---

## 7. Precios

### 7.1 Regla dura: solo USD

Ningún documento muestra conversión a pesos, ni "equivale a X consultas/sesiones", ni tipo de cambio.

**Motivos:**
- La conversión introduce un dato no verificado (tarifa del profesional).
- El tipo de cambio cambia y desactualiza el documento.
- El profesional puede hacer la cuenta solo si quiere.

**Qué mostrar:**
- Precio base en USD.
- Módulos en USD.
- Total en USD.
- Escenarios en USD.

**Qué eliminar:**
- Tabla de conversión a ARS.
- Columna "Equivale a X sesiones".
- Referencia a dolarapi.com.
- Párrafos tipo "el pack completo se paga con 23,3 sesiones".
- Cualquier `[INFERIBLE]` aplicado al valor de la consulta del profesional.

**Excepción:** si el profesional publica su tarifa, se puede mencionar el costo de no hacer nada en su moneda **una sola vez**, en la sección específica, con marca `[INFERIBLE]` y sin convertir a USD.

### 7.2 Validez

La propuesta es válida por **30 días** desde la fecha de emisión. No más.

---

## 8. Fechas y metadatos

- Toda fecha de medición usa la **fecha real** en que se corrió el script.
- Si es demo sin fecha real: `Medición de demostración — {mes} {año}`.
- **Prohibido:** fechas futuras, fechas estimadas, validez superior a 30 días.

---

## 9. CTAs (botones reales)

**Regla:** todo CTA es un botón clickeable, no texto.

### Home del lead
- `Mirá cómo se vería tu sitio →` (link al sitio nuevo)
- `Ver la propuesta →`
- `Ver el informe →`

### Propuesta
- `Agendar llamada de 20 minutos →` (mailto o Cal.com)
- `Aceptar propuesta →` (mailto con asunto predefinido)

### Informe
- `Ver la propuesta →` (al final)
- `Volver al inicio →`

**Mailto con asunto predefinido:**
```
mailto:lisandrocacciatore@gmail.com?subject=Hablemos%20sobre%20mi%20sitio
```

**Si no hay Cal.com/Calendly:** CTA es mailto, texto: *"Respondé este mail con 'dale, hablemos'"*.

---

## 10. Coherencia sitio nuevo ↔ propuesta

**Regla dura:** todo lo que la propuesta promete, el sitio nuevo lo cumple visiblemente.

**Checklist antes de publicar la propuesta:**

- Si promete "N páginas", el sitio nuevo tiene N páginas navegables.
- Si promete "botón flotante de WhatsApp", el sitio nuevo lo tiene y se ve.
- Si promete "contraste medido y corregido", el sitio nuevo tiene el informe de contraste visible o linkeado.
- Si promete "X secciones", el sitio nuevo las tiene con anclas funcionales.

Si el sitio nuevo no cumple, la propuesta **baja la promesa** al nivel de lo que sí cumple.

---

## 11. Home del profesional (sitio nuevo)

Aplica las mismas reglas de calidad que la propuesta exige al sitio viejo:

- Idioma correcto (`lang="es"`)
- Descripción para buscadores (150-160 caracteres)
- Open Graph y Twitter Card
- Datos estructurados (`schema.org`)
- `sitemap.xml` y `robots.txt` funcionales
- Imágenes con `alt`, `loading="lazy"` y `srcset`
- Contraste verificado (mínimo 4,5:1 en cuerpo)
- Etiquetas `<label>` reales en formularios
- Peso total < 1 MB por página
- Verificación en mobile real

**Regla:** el sitio nuevo pasa su propia auditoría. Si no la pasa, no se publica.

---

## 12. Validaciones automáticas antes de publicar

**La checklist es un script.** Un comando:

```bash
bash scripts/verificar-todo.sh
```

Corre los seis gates en orden y resume al final:

| Gate | Qué cubre |
|---|---|
| 1 · construir | genera las dos piezas, verifica precios contra `catalogo.json` y el render real |
| 2 · workflow v2.0 | orden, fechas, solo USD, promesas de base, coherencia sitio↔propuesta |
| 3 · editorial v1.0 | patrón de hallazgos, segunda persona, mobile, tipografía |
| 4 · promesas | lo prometido contra el sitio publicado |
| 5 · PDF del informe | hojas, membrete repetido, sin precios (§4) |
| 6 · PDF de la propuesta | |

Dos fases, a propósito: los gates de diagnóstico corren **todos** aunque uno
falle (un rojo temprano no esconde los demás), y **los PDFs sólo se escriben si
la fase 1 quedó entera en verde**. Un entregable recién escrito con un error se
manda; por eso con gates en rojo los PDFs **no se tocan**.

**Regla para agregar un gate:** va como script en `scripts/` y se suma al
runner. Una regla que no es un script es una regla que se olvida — y los tres
errores que más caro salieron en este proyecto (precios de línea mal que se
cancelan en el total, hojas medio vacías por `break-inside`, desborde en mobile)
los cazó un script, no una relectura.

---

## 13. Lo que NO cambia

Para evitar regresiones, se preserva:

- La disciplina `[MEDIDO]` / `[INFERIBLE]` / `[NO VERIFICADO]`.
- La sección "Alcance de esta revisión" con ✓/✗.
- El "respondé 'no gracias' y no vuelvo a contactarte".
- La estructura Base + módulos + escenarios.
- El comparativo contra colegas medidos el mismo día (cuando cumple §6.2).
- El tono directo, sin adjetivos de más.
- El nombre del producto: "Informe de Valor".

---

## 14. Tabla resumen de cambios

| Cambio | Impacto |
|---|---|
| Sitio nuevo primero | El lead ve el resultado antes que el problema |
| Tabla agencia eliminada | Menos ruido, más credibilidad |
| Solo USD | Sin datos no verificados |
| Hallazgos con patrón fijo | Escaneable, comparable entre leads |
| Informe y propuesta separados | Cada uno tiene un rol claro |
| CTAs reales | El lead puede actuar sin copiar un mail |
| Validaciones automáticas | Nada se publica con fechas futuras o promesas incumplidas |

---

## 15. Referencias de implementación

- Script de medición: `scripts/medir.py --pares 00-auditoria/pares.txt`
- Estructura de carpetas por lead (el motor es `~/motor-leads`; cada lead es una copia):
  ```
  ~/lead-<cliente>/
    00-auditoria/    informe.html + informe-<slug>.pdf + evidencia
    01-propuesta/    propuesta.html + propuesta-<slug>.pdf
    02-sitio/        capturas y assets del sitio medido
    brand/           brand.css, membrete, pie, fuentes embebidas
    templates/       catalogo.json, secciones.json, plantillas
    config.json      datos y narrativa del cliente
    scripts/         el motor
  ```
- Fecha de corte de este spec: 2026-10-05
- Versión anterior (v1.0): deprecada.

---

**Fin del spec.**
