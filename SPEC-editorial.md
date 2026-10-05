---
workflow: hermes-editorial
version: 1.0
fecha: 2026-10-05
autor: Lisandro Cacciatore
aplica-a: redacción, copy, organización y presentación de auditorías y propuestas
complementa-a: hermes-audit-propuesta v2.0
estado: activo
---

# Spec editorial

Este documento define **cómo se escribe, organiza y presenta** una auditoría o propuesta. Es complementario al spec `hermes-audit-propuesta` v2.0, que define **qué** contiene y en qué orden.

Regla de precedencia: si hay conflicto entre estructura y redacción, manda la estructura (v2.0). Este spec solo gobierna la forma.

---

## 0. Principios editoriales

1. **Un registro por zona.** Gancho coloquial solo en H1 y subtítulo. Cuerpo directo y técnico. Cierre en tono de par.
2. **Una idea por titular.** Máximo 12 palabras.
3. **Un dato, una aparición.** Cada número aparece una vez en su hallazgo. Nunca repetido en tabla + línea resumen + cuadro.
4. **Segunda persona siempre.** "Vos" de principio a fin. Nunca "él", "ella", "su".
5. **Sin muletillas.** Prohibidas las frases gastadas.
6. **Sin inferencias sin marcar.** Toda estimación lleva `[INFERIBLE]`. Toda afirmación no verificable lleva `[NO VERIFICADO]`.
7. **Bloques cortos.** Ningún cuerpo de sección supera 200 palabras. Ningún hallazgo supera 5 líneas.

---

## 1. Registro y tono

### 1.1 Los tres registros (no mezclar)

| Zona | Registro | Ejemplo |
|---|---|---|
| H1 + subtítulo | Gancho coloquial, directo | "Tu sitio te pide WhatsApp. No tiene WhatsApp." |
| Cuerpo (hallazgos, precios) | Técnico, sin adjetivos | "0 apariciones de `wa.me` en el HTML servido." |
| Cierre (próximos pasos) | Par, informal profesional | "Nos sentamos veinte minutos." |

**Prohibido:** pasar de coloquial a técnico dentro del mismo párrafo. Prohibido usar ganchos coloquiales en el cuerpo.

### 1.2 Muletillas y frases gastadas

**Prohibidas**, en cualquier zona del documento:

- "es la ventaja más barata sobre la mesa"
- "para que no haya sorpresas"
- "no hay una sola afirmación que no se pueda reproducir" (doble negación)
- "sin inventar métricas ni testimonios"
- "el cambio, en una mirada"
- "casa desordenada"
- "techo duro"
- "puerta de entrada"
- "cuello de botella" (excepto si es cita del propio profesional)
- "en un mundo lleno de..."
- "las organizaciones no cambian por decretos" (y similares)

### 1.3 Persona gramatical

El documento le habla al profesional en **vos**, sin excepción.

**Errores a corregir on sight:**
- "él mismo publica" → "vos publicás" / "tu tarifa publicada"
- "su sitio" → "tu sitio"
- "el profesional" → "vos"
- "a la tarifa que él publica" → "a tu tarifa publicada"

Si el documento arranca en "vos", no puede derivar a tercera persona. Ni una vez.

### 1.4 Frases que confunden

Revisar y reformular:

- Frases incompletas con causa sin consecuencia: *"La persona lee la instrucción, busca el botón, no está, y cierra."* → agregar consecuencia: *"...no lo encuentra y se va."*
- Inferencias no marcadas: *"Tu bio hoy cobra por otros."* → marcar `[INFERIBLE]` o reformular: *"Tu bio manda visitas a 18 marcas que no te dejan el contacto."*
- Personificaciones: *"seguidores que dependen del algoritmo"* → *"seguidores que solo alcanzás si el algoritmo quiere"*.
- Preguntas retóricas en cuerpo técnico (prohibidas).

---

## 2. Estructura de un titular de hallazgo

**Formato fijo:**

```
[NIVEL] **N. Titular del hallazgo** · Prioridad {alta|media|baja}

**Medido:** {dato crudo} sobre {fuente}.
**Qué significa:** {consecuencia para el negocio del lead, 1-2 líneas}.
**Qué propongo:** {módulo Mx o acción concreta}.
```

**Reglas del titular:**
- Máximo 12 palabras.
- Una sola idea.
- Sin coloquialismos.
- Sin adjetivos ("casa desordenada" ✗).
- Sin tres datos concatenados.

**Ejemplos:**

| Mal | Bien |
|---|---|
| "En Doctoralia tenés 5 opiniones de 5 estrellas; la mediana de tu categoría es 14 y el máximo, 142" | "Tenés 5 opiniones. La mediana de tu categoría es 14, y el máximo, 142." |
| "Casa desordenada: 3,5 MB por visita, sin mapa del sitio y con las imágenes sin describir" | "El sitio pesa 3,5 MB por visita y no tiene mapa del sitio." |
| "Tu sitio te pide que le escribas por WhatsApp y no tiene WhatsApp" | "Tu sitio te pide WhatsApp. No tiene ningún WhatsApp." |

**Reglas del cuerpo del hallazgo:**
- Máximo 5 líneas totales (contando Medido + Significa + Propongo).
- "Medido" empieza con el número, no con contexto.
- "Qué significa" es consecuencia, no repetición del dato.
- "Qué propongo" nombra el módulo o la acción, no la repite.

---

## 3. Repeticiones

Cada dato aparece **una sola vez** en su hallazgo. Si es el número más fuerte del documento, se permite una repetición adicional en el **cuadro de números** (arriba). Nunca en:

- Tabla comparativa
- "Lo que dice esta tabla, en una línea"
- "Lo que hoy ya se mide"
- Resumen ejecutivo (si ya está en el cuerpo)

**Ejemplo de cadena repetida a eliminar:**

Lagos dice "ninguno de los 7 tiene WhatsApp" en:
1. Cuadro de números
2. Hallazgo 1
3. Tabla comparativa (columna)
4. "Lo que dice esta tabla, en una línea"

Sobreviven (1) y (2). Se eliminan (3) y (4) para ese dato.

**Regla general:** ningún dato clave aparece más de dos veces en el mismo documento.

---

## 4. Cuadros de números

### 4.1 Composición

- Máximo 4 números (no 5).
- Misma unidad o justificación explícita.
- Si no hay unidad común, elegir los 3 más fuertes y descartar el resto.

**Unidades problemáticas:**

| Cuadro | Problema |
|---|---|
| Lagos | `0 de 7` (conteo), `3,5 MB` (peso), `0,7 MB` (peso), `14 vs 5` (conteo), `2 de 7` (conteo) — mezcla |
| Campanaro | `0 canales`, `5 de 6`, `0 etiquetas`, `3,85:1`, `118 KB` — cinco unidades |
| Titonel | `18`, `3`, `0`, `0`, `420.000` — todas cantidades de links/personas, coherente |

**Regla:** el cuadro ideal es como el de Titonel. Si se aleja, reducir a 3 números.

### 4.2 Formato de cada número

- Número grande arriba.
- Etiqueta abajo, en una línea.
- Máximo 8 palabras en la etiqueta.
- Sin signos de exclamación.
- Sin flechas ni emojis.

---

## 5. Listas

### 5.1 Longitud

- Máximo 5 elementos visibles.
- Si hay más, agrupar o resumir.

**Ejemplo (Titonel):**

Mal:
> Fabletics, Babbel, Headspace, Talkspace, HelloFresh, Factor75, Gobble, Maev, Daily Harvest, Purple Carrot, Clearstem, ARMR A, Omnilux, The Zero Proof, Equip Foods, JLab y Upside.

Bien:
> 18 marcas, entre ellas Fabletics, Babbel, Headspace, HelloFresh y Talkspace.

El listado completo va al informe, en anexo.

### 5.2 Puntuación

- Sin punto final en el último ítem de una lista.
- Sin dos puntos después del encabezado si la lista ya lo dice.
- Comas entre ítems, "y" antes del último.

---

## 6. Números, unidades, comillas

### 6.1 Números

- Decimales con coma: `3,5`.
- Miles con punto: `420.000`.
- Espacio entre símbolo y número: `AR$ 240.000`, `USD 350`.
- Unidad siempre explícita: `3,5 MB`, no `3,5`.
- Sin `K` cuando el número es menor a 10.000: usar `9.500`, no `9,5K`.
- Ratios siempre con dos puntos: `3,85:1`.
- Porcentajes con espacio: `15 %`.

### 6.2 Comillas

| Uso | Comillas |
|---|---|
| Cita textual de tercero (sitio, Doctoralia, paciente) | `« »` |
| Término técnico o extranjerismo | `" "` |
| Nombre de marca o institución | sin comillas |
| Cita del propio documento (autorreferencia) | sin comillas |

### 6.3 Fechas

- Formato: `5 de octubre de 2026`.
- En tablas: `05/10/2026` o `2026-10-05`.
- Nunca `oct-26`, `5/10`, `octubre`.

### 6.4 Moneda

- Solo USD. Sin conversión (ver spec v2.0 §7).
- Formato: `USD 350`, `+ USD 120`, `Total USD 900`.

---

## 7. Organización del documento

### 7.1 Jerarquía de títulos

| Nivel | Uso | Cantidad |
|---|---|---|
| H1 | Titular del documento | 1 solo |
| H2 | Secciones del flujo (Sitio nuevo, Hallazgos, Precios, Próximos pasos) | 5-8 |
| H3 | Sub-bloques (hallazgo individual, módulo individual) | variable |

**Prohibido:** H3 sin H2 padre en la misma página.

### 7.2 Secciones que se consolidan

Tres secciones declaraban límites en lugares distintos:
- "Lo que no puedo medir"
- "Alcance de esta revisión — qué miré y qué no"
- "Qué no incluye"

**Consolidar en una sola sección al final:**

```
## Límites de este documento

**Lo que medí:** {lista de ✓}
**Lo que no pude medir:** {lista de ✗}
**Lo que no incluye la propuesta:** {lista}
```

### 7.3 CTA intermedio

Agregar un CTA después del primer bloque de hallazgos, antes de precios:

> **Si querés, hablamos. Y si no, seguí leyendo.**
> [Botón: Agendar 20 minutos →]

Razón: el lector que ya se convenció no tiene que scrollear 4 pantallas más para actuar.

### 7.4 Longitud por sección

- Cuerpo de sección: máximo 200 palabras.
- Hallazgo individual: máximo 5 líneas.
- Módulo individual: máximo 4 bullets.
- Próximos pasos: máximo 4 bullets.

Si excede, cortar o mover al informe.

---

## 8. Tablas

### 8.1 Regla de uso

Solo se permite tabla si cumple **las cuatro**:

1. Todos los datos fueron medidos el mismo día con la misma herramienta.
2. Cada celda tiene número crudo o estado verificable.
3. Sin celdas vacías ni "sí (2)" sin contexto.
4. En mobile se convierte en bullets, no en tabla scrolleable.

**Si no cumple las cuatro:** reemplazar por 3 bullets resumen.

### 8.2 Tabla "Agencia vs Esta propuesta"

**Eliminada.** Mezcla datos verificados con estimaciones de mercado, y confunde más de lo que aporta.

### 8.3 Formato de tabla

- Encabezados en negrita.
- Alineación: números a la derecha, texto a la izquierda.
- Sin líneas verticales, solo horizontales.
- Caption arriba, no abajo.

---

## 9. Presentación visual

### 9.1 Cards de hallazgo

```
[MEDIDO · Prioridad alta]
Titular del hallazgo
Medido: ...
Significa: ...
Propongo: ...
```

### 9.2 Cards de módulo

```
[+ USD 120 · M1]
Nombre del módulo
- bullet
- bullet
- bullet
- bullet
```

### 9.3 Unificación

Hallazgo y módulo usan **el mismo esquema de dos líneas de metadata** arriba, y contenido abajo. No uno con etiqueta y otro con número suelto.

### 9.4 Capturas

Toda captura lleva caption. Formato:

- Izquierda: `Hoy — {estado actual concreto}`
- Derecha: `Nuevo — {mejora concreta}`

**Ejemplo:**

| Mal | Bien |
|---|---|
| "Las dos capturas son reales." | Izq: "Hoy — plantilla de Docplanner, sin WhatsApp, sin descripción para Google." / Der: "Nuevo — sitio propio, botón flotante, habilitación como texto." |

### 9.5 CTAs

Todo CTA es un `<a>` o `<button>`. Nunca texto suelto.

**Permitidos:**
- `mailto:lisandrocacciatore@gmail.com?subject=Hablemos%20sobre%20mi%20sitio`
- Link a Cal.com / Calendly
- Link interno entre documentos

**Prohibidos:**
- "Escribime a lisandrocacciatore@gmail.com" como texto plano.
- "Una llamada de veinte minutos" sin botón.
- Instrucciones sin acción clickeable.

---

## 10. Escenarios de precio

**Formato:**

| Escenario | Precio |
|---|---|
| Entrada — Base sola | USD 350 |
| Intermedio — Base + M1 + M2 | USD 550 |
| **Recomendado — Base + M1 + M2 + M3** | **USD 650** |
| Pack completo — Base + los 6 módulos | USD 900 |
| Pack completo con 15 % off | USD 765 |

**Reglas:**
- El "Recomendado" va marcado visualmente (negrita o fondo distinto).
- Al lado de la tabla, una línea: *"Recomendado para tu caso: Base + M1 + M2 + M3 = USD 650."*
- Sin explicar por qué es recomendado en la tabla. La razón va en el bloque anterior (hallazgos).
- Sin conversión a pesos.

---

## 11. Errores concretos, por documento

Registro de errores ya identificados que deben corregirse en la próxima pasada:

### Lagos
- "él mismo publica" → "tu tarifa publicada"
- "Casa desordenada" → eliminar del titular
- "0,7 MB bajaría el sitio nuevo" → agregar de dónde sale o eliminar
- "Cómo se ve hoy y cómo se vería" → "Tu sitio, antes y después"
- Titular hallazgo 4 (15 palabras) → cortar a 2 oraciones
- Capturas sin caption → agregar caption por captura

### Campanaro
- "5 de 6" y "Cinco de los seis" → unificar en un formato
- "0 canales directos" → "0 formas de contacto directo"
- "Lo que no puedo medir" → subir al resumen ejecutivo
- Ejemplo de Luis Tesolat → contextualizar por qué él
- Tabla con filas vacías → completar o eliminar

### Titonel
- Lista de 17 marcas → 5 marcas + "entre ellas"
- "Tu bio hoy cobra por otros" → marcar `[INFERIBLE]` o reformular
- Tabla "Agencia vs Esta propuesta" → eliminar (ver §8.2)
- "Lo que dice esta tabla, en una línea" → eliminar si duplica
- "Lo que hoy ya se mide" → eliminar si duplica
- "seguidores que dependen del algoritmo" → [TRUNCADO: el mensaje cortó acá. Completar.]

> **Nota de recepción:** el mensaje con este spec llegó cortado en el último ítem de
> Titonel (§11). El resto del documento está completo.

---

**Fin del spec.**
