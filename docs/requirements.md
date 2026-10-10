# Requirements — Timesheet Intake Gate

> Validación determinística de hojas de tiempo mensuales antes de la carga a nómina.
> La IA apoya la interpretación, el código decide, el humano aprueba lo consecuente.

## 0. Convenciones

### 0.1 Formato EARS (en español)

| Patrón EARS | Forma usada en este documento |
|---|---|
| Ubicuo | **EL sistema DEBERÁ** … |
| Evento | **CUANDO** \<evento\>, **EL sistema DEBERÁ** … |
| Estado | **MIENTRAS** \<estado\>, **EL sistema DEBERÁ** … |
| No deseado | **SI** \<condición\>, **ENTONCES EL sistema DEBERÁ** … |
| Opcional | **DONDE** \<característica\>, **EL sistema DEBERÁ** … |

Cada criterio tiene un ID `R<n>.<m>` que se referencia desde `design.md`, `tasks.md` y los tests.

### 0.2 Glosario

| Término | Definición |
|---|---|
| **Contrato** | `spec/timesheet_spec.yaml` + `spec/employee_master.csv`. Única fuente de reglas, severidades y umbrales. |
| **Período** | Mes a validar, formato `YYYY-MM`, elegido por el analista. |
| **Lote** | Conjunto de archivos subidos en una validación para un período. Inmutable: una corrección es un lote nuevo. |
| **Sede esperada** | Código de sede listado en el contrato (SCL, VAP, CCP, ANF). |
| **Archivo de sede** | Archivo cuyo nombre calza con el patrón y con una sede esperada. |
| **Hallazgo** | Defecto detectado (D01–D12) con evidencia. |
| **Disposición calculada** | Resultado de aplicar las reglas del contrato a los hallazgos abiertos: `LOAD`, `LOAD_WITH_WARNINGS`, `QUARANTINE`, `BLOCK`. |
| **Disposición final** | Disposición calculada, o la del override humano si existe. |
| **Fila** | Número de fila tal como lo ve el analista en Excel: encabezado = fila 1, primer dato = fila 2. |
| **Columna desconocida** | Columna del archivo que, tras normalizar su nombre (sin espacios al borde, sin distinguir mayúsculas), no coincide con ninguna columna requerida. |
| **Mapeo** | Asociación aceptada por el analista entre una columna desconocida y una columna requerida. |
| **Unidad de evaluación** | Lo que se cuenta en métricas: una fila afectada (defectos de fila) o un archivo/columna (defectos de archivo y estructura). Ver R15. |

### 0.3 Severidades por defecto (configurables en el contrato)

| Código | Defecto | Nivel | Severidad por defecto |
|---|---|---|---|
| D01 | Archivo esperado faltante | Lote | BLOCKER |
| D02 | Archivo inesperado o nombre fuera de patrón | Archivo | ERROR (cuenta como 100 % de filas → QUARANTINE) |
| D03 | Período del nombre ≠ período seleccionado | Archivo | BLOCKER |
| D04 | Columna requerida faltante (sin mapeo aceptado) | Estructura | BLOCKER |
| D05 | Columna renombrada (posible equivalencia) | Estructura | WARNING |
| D06 | Columna extra no especificada | Estructura | WARNING |
| D07 | Tipo de dato inválido | Fila | BLOCKER en `regular_hours`/`overtime_hours`; ERROR en el resto |
| D08 | Filas duplicadas (`employee_id` + `work_date`) | Fila | ERROR |
| D09 | `work_date` fuera del período | Fila | ERROR |
| D10 | Horas fuera de rango o total diario > 14 | Fila | ERROR |
| D11 | Valor de catálogo desconocido | Fila | ERROR |
| D12 | Empleado inexistente/inactivo o fila sin aprobación | Fila | ERROR |

---

## R1. Contrato de validación

**Historia:** Como analista, quiero que las reglas vivan en un archivo de configuración para poder ajustarlas sin tocar código.

- **R1.1** EL sistema DEBERÁ cargar desde `spec/timesheet_spec.yaml`: sedes esperadas, patrón de nombre, extensiones permitidas, columnas requeridas (nombre, tipo, nullable, patrón/rango/catálogo), catálogos, formatos de fecha aceptados, alias de columnas, umbrales (nulos por columna, total diario, umbral de cuarentena, umbral de similitud para D05, umbral de confianza IA), severidad de cada código y reglas de disposición ordenadas.
- **R1.2** EL sistema DEBERÁ cargar el maestro de empleados desde `spec/employee_master.csv` (`employee_id`, `site`, `active`).
- **R1.3** SI el YAML o el maestro no cumplen su esquema, ENTONCES EL sistema DEBERÁ negarse a iniciar e indicar el campo y el motivo.
- **R1.4** EL sistema DEBERÁ obtener las severidades, umbrales y reglas de disposición exclusivamente del contrato; ningún valor de este tipo DEBERÁ estar fijo en el código ni en un prompt.
- **R1.5** CUANDO se crea un lote, EL sistema DEBERÁ guardar una copia del contrato vigente y su hash, y toda revalidación de ese lote DEBERÁ usar esa copia.

## R2. Creación de lote e ingesta

**Historia:** Como analista, quiero subir los archivos del mes de una vez y obtener la validación con un clic.

- **R2.1** CUANDO el analista elige un período, sube uno o más archivos (`.csv`, `.xlsx` o `.zip`) y presiona "Validar", EL sistema DEBERÁ crear un lote nuevo y ejecutar la validación completa.
- **R2.2** SI el período no tiene formato `YYYY-MM` válido o no se subió ningún archivo, ENTONCES EL sistema DEBERÁ rechazar la solicitud con un mensaje en español y no crear el lote.
- **R2.3** CUANDO se sube un `.zip`, EL sistema DEBERÁ extraer sus archivos (incluidos los de subcarpetas, usando el nombre base), ignorar carpetas, archivos ocultos y `__MACOSX`, y tratarlos como si se hubieran subido de forma individual.
- **R2.4** SI un `.zip` está corrupto o la carga supera el tamaño máximo configurado (por defecto 4 MB en total por request, bajo el límite de 4,5 MB de Vercel), ENTONCES EL sistema DEBERÁ rechazar el lote con un mensaje que nombre el problema.
- **R2.5** EL sistema DEBERÁ leer CSV en UTF-8 (con o sin BOM) con respaldo a Latin-1, detectando separador `,` o `;`, y DEBERÁ leer la primera hoja de cada `.xlsx`.
- **R2.6** SI un archivo de sede no se puede leer o no tiene fila de encabezados, ENTONCES EL sistema DEBERÁ registrar D04 para todas las columnas requeridas con la evidencia "archivo ilegible o sin encabezados".
- **R2.7** EL sistema DEBERÁ registrar el tiempo de procesamiento determinístico del lote y de cada archivo, en milisegundos.
- **R2.8** EL sistema DEBERÁ tratar cada validación como un lote nuevo e independiente; los archivos de un lote existente no se reemplazan.

## R3. Validación de nombres y completitud (D01, D02, D03)

**Historia:** Como analista, quiero saber de inmediato si falta una sede o si alguien mandó el archivo equivocado.

- **R3.1** EL sistema DEBERÁ reconocer como archivo de sede el que calce exactamente con `TS_{SEDE}_{YYYYMM}.csv|.xlsx` (extensión sin distinguir mayúsculas) con `SEDE` en la lista de sedes esperadas.
- **R3.2** SI el nombre de un archivo no calza con el patrón o su sede no está en la lista, ENTONCES EL sistema DEBERÁ registrar **D02** y no validar su contenido.
- **R3.3** SI más de un archivo corresponde a la misma sede, ENTONCES EL sistema DEBERÁ considerar archivo de sede al primero en orden alfabético y registrar **D02** ("sede duplicada") en los demás.
- **R3.4** SI el `YYYYMM` del nombre difiere del período seleccionado, ENTONCES EL sistema DEBERÁ registrar **D03** con el período encontrado y el esperado, contar el archivo como el de su sede (sin generar D01) y no validar su contenido.
- **R3.5** CUANDO termina el análisis de nombres, SI una sede esperada no tiene archivo, ENTONCES EL sistema DEBERÁ registrar **D01** asociado a esa sede, indicando el nombre esperado (`TS_{SEDE}_{YYYYMM}.csv|.xlsx`).

## R4. Validación estructural (D04, D05, D06)

**Historia:** Como analista, quiero detectar plantillas cambiadas antes de que rompan la carga.

- **R4.1** EL sistema DEBERÁ comparar encabezados normalizados (sin espacios al borde, sin distinguir mayúsculas); una coincidencia exacta con una columna requerida no genera hallazgo.
- **R4.2** SI una columna requerida no está presente y no tiene un mapeo aceptado, ENTONCES EL sistema DEBERÁ registrar **D04**, uno por columna.
- **R4.3** EL sistema DEBERÁ calcular, para cada columna desconocida y cada columna requerida faltante, un puntaje determinístico de equivalencia (0–1) que combine: coincidencia con los alias del contrato, similitud textual del nombre normalizado y proporción de valores de muestra que cumplen el tipo de la columna requerida.
- **R4.4** SI el mejor puntaje de una columna desconocida alcanza el umbral de similitud del contrato, ENTONCES EL sistema DEBERÁ registrar **D05** con la columna candidata y el puntaje como evidencia; cada columna requerida faltante DEBERÁ ser candidata de a lo más una columna desconocida (la de mayor puntaje).
- **R4.5** SI una columna desconocida no queda como D05, ENTONCES EL sistema DEBERÁ registrar **D06**.
- **R4.6** MIENTRAS una columna requerida falte, EL sistema DEBERÁ omitir las validaciones de contenido que dependan de ella y ejecutar las demás.

## R5. Validación de contenido (D07–D12)

**Historia:** Como analista, quiero saber exactamente qué filas tienen datos que la nómina no puede procesar.

Aplica solo a archivos de sede con nombre y período válidos.

- **R5.1** SI un valor no se puede convertir al tipo declarado (horas no decimales, fecha que no calza con ningún formato aceptado, `employee_id` que no cumple `E\d{5}`) o es nulo en una columna no nullable, ENTONCES EL sistema DEBERÁ registrar **D07** para esa columna, agrupando las filas afectadas. Los nulos en `approved_by`/`approval_date` se registran como D12 y no como D07. Se aceptan `.` y `,` como separador decimal.
- **R5.2** EL sistema DEBERÁ asignar a D07 la severidad definida por columna en el contrato (por defecto BLOCKER en columnas de horas y ERROR en el resto).
- **R5.3** SI el porcentaje de nulos de una columna no nullable supera el máximo configurado, ENTONCES EL sistema DEBERÁ elevar a BLOCKER el hallazgo correspondiente de esa columna (D07, o D12 si es de aprobación).
- **R5.4** SI dos o más filas comparten `employee_id` + `work_date` válidos, ENTONCES EL sistema DEBERÁ registrar **D08** marcando cada ocurrencia posterior a la primera e indicando la fila de la primera ocurrencia.
- **R5.5** SI un `work_date` válido cae fuera del período seleccionado, ENTONCES EL sistema DEBERÁ registrar **D09**.
- **R5.6** SI `regular_hours` está fuera de [0, 12], `overtime_hours` está fuera de [0, 4] o su suma supera el total diario máximo (14), ENTONCES EL sistema DEBERÁ registrar **D10**, con la subregla incumplida en el campo "regla aplicada".
- **R5.7** SI `shift_code` no pertenece a su catálogo, o `absence_code` no es nulo y no pertenece a su catálogo (comparación sin espacios al borde y distinguiendo mayúsculas), ENTONCES EL sistema DEBERÁ registrar **D11**.
- **R5.8** SI un `employee_id` válido no existe en el maestro o figura como inactivo, o si `approved_by` o `approval_date` están vacíos, ENTONCES EL sistema DEBERÁ registrar **D12**, con la subregla incumplida en "regla aplicada".
- **R5.9** EL sistema NO DEBERÁ reevaluar en D08–D12 un valor que ya produjo D07 en la misma columna.

## R6. Estructura del hallazgo

- **R6.1** Cada hallazgo DEBERÁ tener: id único dentro del lote, archivo (o sede esperada en D01), código, severidad, columna (si aplica), regla aplicada (id de regla del contrato y descripción legible en español), cantidad de filas afectadas, lista completa de filas afectadas, hasta 5 filas de ejemplo con sus valores, evidencia (valor encontrado vs. valor esperado) y estado (`abierto`, `resuelto_por_mapeo`).
- **R6.2** EL sistema DEBERÁ mostrar al analista la descripción de cada código en español, nunca solo el código.

## R7. Severidad y disposición

**Historia:** Como analista, quiero una decisión clara por archivo, explicada y siempre igual para los mismos datos.

- **R7.1** EL sistema DEBERÁ calcular la disposición de cada archivo de sede, de cada sede con D01 y de cada archivo con D02, aplicando las reglas ordenadas del contrato (gana la primera que se cumple):
  1. `BLOCK` si existe al menos un hallazgo abierto BLOCKER.
  2. `QUARANTINE` si el porcentaje de filas distintas afectadas por hallazgos abiertos ERROR supera el umbral de cuarentena (por defecto 2 %). Los ERROR de nivel archivo (D02) cuentan como 100 %.
  3. `LOAD_WITH_WARNINGS` si existe al menos un hallazgo abierto.
  4. `LOAD` en otro caso.
- **R7.2** EL sistema DEBERÁ guardar junto a cada disposición la regla que se cumplió y los números que la justifican (p. ej. "3,4 % de filas con ERROR > 2 %").
- **R7.3** CUANDO cambian los hallazgos de un archivo (por aceptar o rechazar un mapeo), EL sistema DEBERÁ recalcular su disposición con las mismas reglas.
- **R7.4** EL sistema NO DEBERÁ usar ninguna salida de la IA como entrada del cálculo de hallazgos, severidades o disposiciones.
- **R7.5** EL sistema DEBERÁ marcar el lote como "Apto para carga" solo si ningún archivo ni sede tiene disposición final `BLOCK` o `QUARANTINE`.
- **R7.6** Para los mismos archivos y el mismo contrato, EL sistema DEBERÁ producir exactamente los mismos hallazgos y disposiciones.

## R8. Revisión humana de mapeos

**Historia:** Como analista, quiero aprobar o rechazar equivalencias de columnas sin que nada se aplique solo.

- **R8.1** EL sistema DEBERÁ listar en la cola de revisión cada columna con D05 o D06 pendiente, mostrando la candidata determinística (si existe) y la sugerencia de IA (si existe) con su confianza, justificación y la marca "Requiere revisión humana" cuando corresponda.
- **R8.2** EL sistema NO DEBERÁ aplicar ningún mapeo sin una acción explícita del analista.
- **R8.3** CUANDO el analista acepta un mapeo columna X → columna requerida Y (Y debe ser una columna requerida faltante en ese archivo, sugerida o elegida por el analista), EL sistema DEBERÁ revalidar el archivo completo con la copia del contrato del lote, regenerar sus hallazgos (D04/D05 de esa columna pasan a `resuelto_por_mapeo`), recalcular la disposición y registrar la acción en auditoría.
- **R8.4** CUANDO el analista rechaza un mapeo, EL sistema DEBERÁ marcarlo como rechazado, mantener los hallazgos abiertos y registrar la acción en auditoría.
- **R8.5** EL sistema DEBERÁ aplicar un mapeo aceptado solo al archivo de ese lote.

## R9. Override de disposición

**Historia:** Como analista, quiero poder corregir una disposición cuando tengo contexto que el sistema no tiene, dejando constancia.

- **R9.1** EL sistema DEBERÁ permitir al analista fijar cualquier disposición final para un archivo o sede, en cualquier dirección.
- **R9.2** SI la justificación está vacía o tiene menos de 20 caracteres, ENTONCES EL sistema DEBERÁ rechazar el override.
- **R9.3** EL sistema DEBERÁ mostrar siempre la disposición calculada y la final, una junto a la otra.
- **R9.4** CUANDO un override relaja la disposición (orden de restricción `BLOCK` > `QUARANTINE` > `LOAD_WITH_WARNINGS` > `LOAD`), EL sistema DEBERÁ marcarlo como "Override permisivo" en el resumen, en el detalle y en el reporte.
- **R9.5** SI la disposición calculada cambia después de un override (por una revalidación), ENTONCES EL sistema DEBERÁ mantener el override y mostrar el aviso "La disposición calculada cambió después del override".
- **R9.6** EL sistema DEBERÁ permitir retirar un override, con justificación y con registro en auditoría.

## R10. Auditoría

- **R10.1** CUANDO ocurre una acción humana (aceptar o rechazar mapeo, crear o retirar override) o una revalidación derivada, EL sistema DEBERÁ registrar: actor, acción, entidad (lote/archivo/hallazgo), fecha y hora (UTC, mostrada en hora local), estado anterior, estado posterior y justificación.
- **R10.2** EL sistema DEBERÁ tratar el log de auditoría como de solo inserción: no DEBERÁ existir forma de editarlo ni borrarlo desde la API o la UI, y la base de datos (Supabase Postgres) DEBERÁ impedir `UPDATE`/`DELETE` sobre esa tabla.
- **R10.3** MIENTRAS no exista autenticación, EL sistema DEBERÁ pedir el nombre del analista una vez (recordado en el navegador) y enviarlo con cada acción; SI falta el nombre, ENTONCES EL sistema DEBERÁ rechazar la acción.
- **R10.4** EL sistema DEBERÁ mostrar el log de auditoría del lote en la UI e incluirlo en el reporte.

## R11. Asistencia de IA

**Historia:** Como analista, quiero que la IA me ayude a entender y comunicar los problemas, sin que decida por mí.

- **R11.1** DONDE exista `ANTHROPIC_API_KEY`, EL sistema DEBERÁ generar, a pedido del frontend y por archivo: (a) sugerencias de mapeo para cada columna desconocida (D05/D06), (b) causa probable para archivos con hallazgos abiertos y (c) borrador de mensaje de remediación para el responsable de la sede.
- **R11.2** EL sistema DEBERÁ entregar los hallazgos y disposiciones sin esperar a la IA; mientras la IA trabaja, sus secciones DEBERÁN mostrar "Generando…".
- **R11.3** EL sistema DEBERÁ enviar a la IA solo: nombre de archivo, sede, período, encabezados, columnas requeridas, hallazgos del archivo (id, código, severidad, columna, evidencia, cantidad) y como máximo 5 filas o 5 valores de muestra; nunca el archivo completo.
- **R11.4** EL sistema DEBERÁ usar el modelo indicado en `LLM_MODEL` y validar cada respuesta contra un esquema pydantic; SI la respuesta no es JSON válido o no cumple el esquema, ENTONCES EL sistema DEBERÁ descartarla y mostrar "No disponible".
- **R11.5** Cada afirmación de causa probable y remediación DEBERÁ referenciar al menos un id de hallazgo existente en ese archivo. EL sistema DEBERÁ descartar las afirmaciones con ids inexistentes y DEBERÁ mostrar como "Sin respaldo en hallazgos" las que la IA declare sin referencia.
- **R11.6** SI una salida de IA tiene confianza menor al umbral del contrato (por defecto 0,7), ENTONCES EL sistema DEBERÁ marcarla como "Requiere revisión humana".
- **R11.7** SI una sugerencia de mapeo propone un destino que no es una columna requerida (o "ninguna"), ENTONCES EL sistema DEBERÁ descartarla.
- **R11.8** EL sistema DEBERÁ presentar el borrador de remediación en español, con los hallazgos concretos (ids, filas, valores), copiable con un botón, y NUNCA DEBERÁ enviarlo automáticamente.
- **R11.9** EL sistema DEBERÁ distinguir visualmente todo contenido generado por IA (etiqueta "IA – no vinculante").
- **R11.10** EL sistema DEBERÁ guardar cada resultado de IA con modelo, fecha, latencia y estado (`ok`, `no_disponible`, `invalido`).
- **R11.11** EL sistema DEBERÁ cortar cada llamada a la IA después de un timeout configurable (por defecto 30 s).

## R12. Funcionamiento sin IA

- **R12.1** SI no hay `ANTHROPIC_API_KEY`, o la API falla, excede el timeout o responde algo inválido, ENTONCES EL sistema DEBERÁ entregar completos los hallazgos, disposiciones, la cola de revisión (con candidatas determinísticas), overrides, auditoría y reporte, y las secciones de IA DEBERÁN mostrar "No disponible" con un motivo breve.
- **R12.2** EL sistema NO DEBERÁ mostrar trazas técnicas al analista.

## R13. Pantallas (UI en español)

- **R13.1 Nuevo lote:** selector de período, carga de varios archivos o un `.zip` (arrastrar o elegir) y botón "Validar".
- **R13.2 Resumen del lote:** una tarjeta por sede esperada y por archivo D02, con color y texto de la disposición final (verde `LOAD`, amarillo `LOAD_WITH_WARNINGS`, naranjo `QUARANTINE`, rojo `BLOCK`), marca de override, totales por severidad, tiempo de procesamiento y estado "Apto / No apto para carga". El color nunca es el único indicador.
- **R13.3 Detalle de archivo:** tabla de hallazgos filtrable por severidad, código, columna y estado; evidencia, filas de ejemplo, disposición con la regla que se cumplió; causa probable (IA) y borrador de remediación (IA, copiable).
- **R13.4 Cola de revisión humana:** mapeos pendientes del lote (aceptar/rechazar, o elegir otro destino) y formulario de override con justificación obligatoria.
- **R13.5 Auditoría:** vista del log del lote.
- **R13.6 Reporte exportable:** HTML autocontenido descargable (imprimible a PDF desde el navegador) con período, fecha, hash del contrato, resumen, hallazgos por archivo, disposiciones calculadas y finales, overrides, auditoría y secciones de IA rotuladas como no vinculantes.
- **R13.7 Métricas:** muestra el último resultado de `evaluate.py` (tabla y fecha de ejecución), leído del `evaluation.json` versionado en el repo e incluido en el deploy; SI no existe, ENTONCES muestra cómo generarlo.
- **R13.8 Historial:** lista de lotes con período, fecha y estado, para navegar entre ellos.
- **R13.9** Toda pantalla que lee de la API DEBERÁ tener tres estados diseñados: cargando, vacío y error (con mensaje en español y acción para reintentar). Nunca una pantalla en blanco.
- **R13.10** Cada pantalla DEBERÁ verse y operarse correctamente en 375 px, 768 px y 1280 px de ancho, con hover y foco visible en todo elemento interactivo y contraste AA mínimo.
- **R13.11** Cada pantalla DEBERÁ tener una ruta propia, un enlace en la navegación y un título propio en la pestaña del navegador.

## R14. Dataset sintético

- **R14.1** `scripts/generate_dataset.py` DEBERÁ aceptar una seed (por defecto 42) y, con la misma seed, producir archivos idénticos byte a byte.
- **R14.2** DEBERÁ generar un maestro de ~60 empleados repartidos en las 4 sedes, incluidos algunos inactivos.
- **R14.3** DEBERÁ generar un lote limpio (4 archivos, mezcla CSV/XLSX) cuyo resultado esperado sea cero hallazgos y `LOAD` en todas las sedes.
- **R14.4** DEBERÁ generar 5 lotes con defectos sembrados, de modo que cada código D01–D12 aparezca en al menos 2 lotes, e incluya columnas renombradas con destino conocido (para medir los mapeos de IA).
- **R14.5** DEBERÁ escribir un `ground_truth.json` por lote con: período, archivos (archivo, sede, disposición esperada), defectos (archivo, código, columna si aplica, filas) y mapeos esperados (archivo, columna, destino).
- **R14.6** El ground truth DEBERÁ derivarse del plan de siembra del generador (incluida la disposición esperada, calculada por el generador desde lo sembrado), nunca de ejecutar el motor.
- **R14.7** Los datos base DEBERÁN generarse de forma que no contengan defectos no sembrados.

## R15. Evaluación

- **R15.1** `scripts/evaluate.py` DEBERÁ ejecutar el motor sobre todos los lotes sintéticos sin IA por defecto, y con IA cuando se pase `--with-ai`.
- **R15.2** DEBERÁ calcular:
  - tasa de detección por código y global (unidades del ground truth detectadas / unidades del ground truth), donde la unidad es la fila para D07–D12 y el archivo/columna para D01–D06;
  - tasa de falsos positivos (unidades detectadas que no están en el ground truth / unidades detectadas);
  - exactitud de disposición (disposiciones calculadas iguales a la esperada / total) y cantidad de disposiciones incorrectas;
  - precisión de las candidatas determinísticas de D05 y, con `--with-ai`, precisión de los mapeos sugeridos por la IA (destino correcto / sugerencias con destino); sin IA se informa "N/A";
  - tiempo por lote (determinístico y, aparte, IA).
- **R15.3** DEBERÁ ejecutarse localmente, imprimir una tabla markdown y escribir `reports/evaluation.md` y `reports/evaluation.json`. Este último se versiona en el repo y la pantalla Métricas lo consume tras el deploy.
- **R15.4** DEBERÁ terminar con código de salida distinto de 0 si la detección global es < 95 % o hay alguna disposición incorrecta.

## R16. Tests (pytest)

- **R16.1** DEBERÁ existir al menos un test positivo por cada código D01–D12 y un test de archivo limpio sin hallazgos.
- **R16.2** DEBERÁ existir al menos un test por regla de disposición (`BLOCK`, `QUARANTINE`, `LOAD_WITH_WARNINGS`, `LOAD`), incluido el borde del umbral (exactamente 2 % → no es `QUARANTINE`).
- **R16.3** DEBERÁ existir un test de extremo a extremo vía API sin `ANTHROPIC_API_KEY`, que verifique hallazgos, disposiciones y secciones de IA en estado `no_disponible`.
- **R16.4** DEBERÁ existir un test con la IA simulada fallando o devolviendo JSON inválido, con el mismo resultado que R16.3.
- **R16.5** DEBERÁN existir tests de: payload de IA con ≤ 5 filas de muestra, salidas de IA que no alteran disposiciones, y descarte de referencias a hallazgos inexistentes.
- **R16.6** DEBERÁN existir tests de: aceptar un mapeo revalida y recalcula la disposición, override sin justificación se rechaza, y cada acción humana genera una entrada de auditoría.
- **R16.7** Los tests NO DEBERÁN requerir red, clave de API ni conexión a Supabase (usan SQLite en memoria vía la misma capa SQLAlchemy).

## R17. Requisitos no funcionales

- **R17.1** La infraestructura DEBERÁ ser solo Vercel (frontend estático Vite + backend FastAPI como función Python) y Supabase (Postgres). No se usa Docker ni otros servicios.
- **R17.2** La app DEBERÁ levantarse localmente con un solo comando documentado (`vercel dev`), que sirve frontend y API juntos, y DEBERÁ estar desplegada en una URL de Vercel.
- **R17.3** EL sistema DEBERÁ leer la conexión a base de datos desde `DATABASE_URL` (Supabase Postgres); las variables `DATABASE_URL`, `ANTHROPIC_API_KEY` y `LLM_MODEL` DEBERÁN configurarse como variables de entorno de Vercel.
- **R17.4** Un lote de 4 archivos de hasta 2.000 filas cada uno DEBERÁ validarse (sin IA) en menos de 5 segundos, dentro del límite de duración de la función de Vercel; cada llamada de IA DEBERÁ ser un request separado.
- **R17.5** La UI y los mensajes al analista DEBERÁN estar en español; identificadores de código y API, en inglés.
- **R17.6** EL sistema DEBERÁ usar solo datos sintéticos; la clave de API y la conexión a Supabase NO DEBERÁN registrarse en logs, enviarse al frontend ni versionarse (`.env` en `.gitignore`).
- **R17.7** El frontend DEBERÁ construirse con React + Vite + **TypeScript** + Tailwind CSS, sin librerías de componentes; los íconos DEBERÁN venir de `lucide-react`. El backend DEBERÁ usar Python 3.12, FastAPI, pandas y pydantic, con acceso a datos vía SQLAlchemy/SQLModel.
- **R17.8** Cada tabla DEBERÁ crearse con un archivo SQL numerado en `supabase/migrations/`, con `id uuid primary key default gen_random_uuid()` y `created_at timestamptz default now()`, y con Row Level Security activado en el mismo archivo.
- **R17.9** El frontend NO DEBERÁ acceder a Supabase directamente: todo dato pasa por la API FastAPI. Las tablas NO DEBERÁN tener políticas para los roles `anon` ni `authenticated`, de modo que la API pública de Supabase no exponga nada. La clave `service_role` NO DEBERÁ usarse.
- **R17.10** El README DEBERÁ incluir: problema, arquitectura (diagrama simple), frontera IA vs. código, control de incertidumbre, resultados de evaluación y limitaciones conocidas.

---

## Fuera de alcance

Autenticación real, múltiples usuarios o roles, integración con sistemas de nómina reales, datos reales de personas, reemplazo de archivos dentro de un lote, envío automático de mensajes, defectos fuera de D01–D12 (p. ej. empleado de otra sede; se anota como limitación), Docker, Supabase Auth/Storage (la URL pública queda sin autenticación; se mitiga con Vercel Deployment Protection y datos solo sintéticos).

## Trazabilidad defecto → requisito → test

| Código | Requisito | Test (nombre previsto) |
|---|---|---|
| D01 | R3.5 | `test_d01_missing_expected_file` |
| D02 | R3.2, R3.3 | `test_d02_unexpected_or_bad_name`, `test_d02_duplicate_site` |
| D03 | R3.4 | `test_d03_period_mismatch` |
| D04 | R4.2, R2.6 | `test_d04_missing_required_column` |
| D05 | R4.3, R4.4 | `test_d05_renamed_column_detected` |
| D06 | R4.5 | `test_d06_extra_column` |
| D07 | R5.1–R5.3 | `test_d07_text_in_hours_blocks`, `test_d07_bad_date` |
| D08 | R5.4 | `test_d08_duplicate_rows` |
| D09 | R5.5 | `test_d09_date_outside_period` |
| D10 | R5.6 | `test_d10_hours_out_of_range`, `test_d10_daily_total` |
| D11 | R5.7 | `test_d11_unknown_catalog_value` |
| D12 | R5.8 | `test_d12_unknown_inactive_or_unapproved` |

## Decisiones ya tomadas (detalle en design.md)

1. **D05 es determinístico** (alias + similitud + perfil de valores); la IA solo propone y justifica el mapeo. Así las métricas de detección no dependen de la API.
2. **Infraestructura solo Vercel + Supabase:** `vercel dev` en local, deploy en Vercel, Postgres en Supabase. Sin Docker.
3. **Corrección = lote nuevo;** los lotes son inmutables.
4. **El override se permite en cualquier dirección,** con justificación obligatoria y marca de "Override permisivo".
5. **La IA se pide por llamadas separadas desde el frontend** (no hay tareas en segundo plano), porque las funciones de Vercel no siguen corriendo después de responder.
6. **Interpretaciones del enunciado (aprobadas por el usuario el 2026-10-10):** D02 como ERROR al 100 % (→ QUARANTINE); D02 y D03 cortan la validación de contenido; encabezados sin distinguir mayúsculas pero catálogos sí; un exceso de nulos eleva a BLOCKER; la numeración de filas sigue a Excel; tamaño máximo de 4 MB en total por request (límite de Vercel); override en cualquier dirección con justificación de al menos 20 caracteres.
7. **Frontend en TypeScript** por pedido del usuario, aunque `CLAUDE.md` usa JavaScript por defecto.
8. **Sin cliente Supabase en el frontend.** Se aparta de `CLAUDE.md` §3.2: como el backend es FastAPI, el navegador no habla con Supabase. Así RLS cierra todo el acceso público y los datos solo se leen a través de la API.
