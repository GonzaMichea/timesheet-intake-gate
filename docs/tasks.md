# Tasks — Timesheet Intake Gate

> Ejecutar en orden, de a una. Una tarea se marca `[x]` solo cuando su criterio **"Listo cuando"** se verificó.
> No se avanza a una tarea si la anterior no está verificada (CLAUDE.md §14).
> 🧑 = requiere una acción del usuario (cuentas, claves, aprobaciones).
> Cada incremento termina con commit + push a su rama y la URL de preview de Vercel.

---

## Incremento 0 — Base verificada

- [x] **T0.1 Repositorio.** `git init`, `.gitignore` (`.env`, `.env.local`, `node_modules`, `__pycache__`, `.venv`, `dist`, `.vercel`), primer commit con `docs/` y `CLAUDE.md`.
  *Listo cuando:* `git status` está limpio y `.env.local` no aparece.
- [x] **T0.2 🧑 GitHub.** El usuario crea el repositorio (indica si es público o privado). Push de `main`.
  *Listo cuando:* el repositorio muestra el commit inicial.
- [x] **T0.3 Esqueleto frontend.** Vite + React + TypeScript + Tailwind 3 en la raíz. Fuentes Archivo e IBM Plex Sans, tokens de color y escala tipográfica en `tailwind.config.js` (design §9). Una página "Timesheet Intake Gate" que llama a `/api/health` y muestra el resultado.
  *Listo cuando:* `npm run build` termina sin errores.
- [x] **T0.4 Spike de la función Python.** `api/index.py` con FastAPI y `GET /api/health`, que importa pandas y openpyxl y devuelve sus versiones. `requirements.txt`, `vercel.json` (design §11).
  *Listo cuando:* `vercel dev` responde `/api/health` en local.
- [x] **T0.5 🧑 Vercel.** El usuario importa el repositorio en Vercel y carga `LLM_MODEL` (las demás variables, después).
  *Listo cuando:* la URL de producción muestra la página y `/api/health` responde con las versiones de pandas. **Si el build falla por tamaño → se aplica el plan B de design §11 y se avisa al usuario.**
- [x] **T0.6 🧑 Supabase.** El usuario crea el proyecto. Se escribe `supabase/migrations/001_create_core_tables.sql` (7 tablas, RLS, rol `tig_api`, trigger de solo inserción). El usuario lo ejecuta en el SQL Editor, le asigna la contraseña a `tig_api` y carga `DATABASE_URL` (pooler 6543) en `.env.local` y en Vercel.
  *Listo cuando:* `/api/health` informa `db: ok` en la URL de Vercel, y una consulta con la clave anon a cualquier tabla devuelve vacío o error de permisos.

## Incremento 1 — Contrato y motor determinístico (rama `feature/motor`)

- [x] **T1.1 Contrato.** `spec/timesheet_spec.yaml` completo (design §3), un maestro mínimo y `backend/app/contract/` con los modelos pydantic `Contract` y `Master` y su loader.
  *Listo cuando:* hay tests de que el contrato válido carga, el YAML con un campo inválido falla nombrando el campo (R1.3) y el hash es estable.
- [x] **T1.2 Modelos del motor.** `InputFile`, `Finding`, `Disposition`, `FileResult` y `BatchResult` en `engine/models.py`.
  *Listo cuando:* importan sin errores y pasa `test_engine_does_not_import_ai` (también prohíbe importar `db`).
- [x] **T1.3 Ingesta.** Lectura de CSV (UTF-8/BOM/Latin-1, `,`/`;`), XLSX (primera hoja, fechas nativas) y ZIP (subcarpetas, `__MACOSX`, ocultos), y límite de tamaño.
  *Listo cuando:* hay tests por cada formato y de zip corrupto (R2.3–R2.6).
- [x] **T1.4 Nombres: D01, D02, D03.**
  *Listo cuando:* pasan `test_d01_missing_expected_file`, `test_d02_unexpected_or_bad_name`, `test_d02_duplicate_site` y `test_d03_period_mismatch`.
- [x] **T1.5 Estructura: D04, D05, D06**, con el puntaje de design §4.3 y la aplicación de mapeos.
  *Listo cuando:* pasan `test_d04_missing_required_column`, `test_d05_renamed_column_detected`, `test_d06_extra_column` y un test de que un mapeo aplicado deja D04/D05 en `resolved_by_mapping`.
- [x] **T1.6 Contenido: D07**, con severidad por columna y elevación por exceso de nulos.
  *Listo cuando:* pasan `test_d07_text_in_hours_blocks`, `test_d07_bad_date` y un test de nulos sobre el umbral → BLOCKER.
- [x] **T1.7 Contenido: D08, D09, D10.**
  *Listo cuando:* pasan `test_d08_duplicate_rows`, `test_d09_date_outside_period`, `test_d10_hours_out_of_range` y `test_d10_daily_total`, más un test de que una celda con D07 no se reevalúa (R5.9).
- [x] **T1.8 Contenido: D11, D12.**
  *Listo cuando:* pasan `test_d11_unknown_catalog_value` y `test_d12_unknown_inactive_or_unapproved`.
- [x] **T1.9 Disposición.** `decide()` con las reglas del YAML y la explicación numérica.
  *Listo cuando:* pasan los tests de BLOCK, QUARANTINE, LOAD_WITH_WARNINGS y LOAD, el borde de exactamente 2 % → no es QUARANTINE, y D02 → QUARANTINE (R16.2).
- [x] **T1.10 Orquestación del motor.** `validate_batch()` completo y `test_clean_file_has_no_findings`.
  *Listo cuando:* `pytest` está en verde y un test de determinismo corre dos veces el mismo lote y obtiene resultados idénticos (R7.6).

## Incremento 2 — Dataset sintético y evaluación (rama `feature/evaluacion`)

- [x] **T2.1 Generador base.** `scripts/generate_dataset.py --seed 42`: maestro de 60 empleados y `batch_00_clean`.
  *Listo cuando:* dos ejecuciones dan archivos idénticos byte a byte y el motor da 0 hallazgos y LOAD ×4.
- [x] **T2.2 Operaciones de siembra** y cálculo independiente de la disposición esperada.
  *Listo cuando:* hay tests unitarios de cada operación que registran su unidad en el ground truth.
- [x] **T2.3 Lotes 01–05** según la tabla de design §10.
  *Listo cuando:* cada código D01–D12 aparece en al menos 2 `ground_truth.json` (verificado por un test).
- [x] **T2.4 `scripts/evaluate.py`.** Métricas de R15.2, `reports/evaluation.md` y `.json`, y código de salida (R15.4).
  *Listo cuando:* corre sin IA y muestra **≥ 95 % de detección y 0 disposiciones incorrectas**. Si no, se corrige el motor o el generador (no el umbral) antes de seguir.

## Incremento 3 — Persistencia y API (rama `feature/api`)

- [x] **T3.1 Modelos SQLAlchemy y sesión** (Postgres con pooler / SQLite en tests).
  *Listo cuando:* pasa `test_migration_matches_models`.
- [x] **T3.2 `POST /api/batches`, `GET /api/batches`, `GET /api/batches/{id}`.** Guardan la copia del contrato, los archivos, los hallazgos y los tiempos.
  *Listo cuando:* hay tests de API con período inválido → 400 en español, sin archivos → 400, y un lote válido → resumen correcto.
- [x] **T3.3 `GET /api/files/{id}`, `/api/contract`, `/api/batches/{id}/audit`.**
  *Listo cuando:* hay tests de API.
- [x] **T3.4 Mapeos: aceptar/rechazar** con revalidación transaccional y auditoría.
  *Listo cuando:* pasan los tests de aceptar → disposición recalculada + entrada de auditoría, y de rechazar → hallazgos abiertos.
- [x] **T3.5 Overrides: crear/retirar** con aviso de "Override permisivo" y "calculada cambió".
  *Listo cuando:* pasan los tests de override sin justificación → 400, override permisivo marcado y cada acción con su auditoría.
- [ ] **T3.6 Verificación en Vercel.** Crear un lote real desde la URL de preview (con `curl` o un formulario mínimo).
  *Listo cuando:* el lote aparece en Supabase y `/api/batches/{id}` responde desde la preview.

## Incremento 4 — Pantallas (una por iteración, con aprobación entre cada una)

Cada pantalla cumple: estados cargando/vacío/error, 375/768/1280 px, hover y foco visible, título de pestaña, autocrítica CLAUDE.md §5.4 y checklist §15.

- [x] **T4.1 Layout y navegación.** Router, barra superior del acta, `AnalystContext` (pide el nombre), `services/api.ts`, `useDocumentTitle`, tipos en `src/types/api.ts`.
- [x] **T4.2 Nuevo lote** (R13.1): período, arrastrar/elegir archivos o `.zip`, botón "Validar lote".
- [x] **T4.3 Resumen del lote** (R13.2): veredicto "Apto / No apto para carga", renglón por sede con sello de disposición, **cinta de filas** y conteos, tiempo de procesamiento.
- [x] **T4.4 Detalle de archivo** (R13.3): tabla de hallazgos filtrable, evidencia, filas de ejemplo, disposición calculada vs. final y su regla. Las secciones IA quedan en "No disponible" por ahora.
- [x] **T4.5 Cola de revisión** (R13.4): aceptar/rechazar mapeos (o elegir otro destino) y formulario de override.
- [x] **T4.6 Auditoría e Historial** (R13.5, R13.8).

*Listo cuando (cada una):* el usuario la revisa en la URL de preview y la aprueba.

## Incremento 5 — Asistencia IA (rama `feature/ia`)

- [x] **T5.1 Cliente y payload.** `ai/client.py` (tool use forzado, timeout, sin clave → `no_disponible`) y `build_payload` con ≤ 5 filas.
  *Listo cuando:* pasan el test de límite del payload y el de sin clave → `no_disponible` sin llamada de red.
- [x] **T5.2 Esquemas y guardas** (design §7.3–7.4).
  *Listo cuando:* hay tests con IA simulada de ref inexistente → descartada, sin refs → "Sin respaldo", confianza 0,5 → `needs_review`, y destino inválido → descartado.
- [x] **T5.3 Endpoint `POST /api/files/{id}/ai/{kind}`** y obsolescencia al revalidar.
  *Listo cuando:* pasan `test_app_works_without_ai` (R16.3), `test_ai_failure_or_invalid_json` (R16.4) y un test de que las disposiciones no cambian tras llamar a la IA (R16.5).
- [ ] **T5.4 🧑 Clave en Vercel.** El usuario carga `ANTHROPIC_API_KEY` en Vercel.
  *Listo cuando:* en la preview, un archivo de `batch_01` muestra la sugerencia "Horas Extra → overtime_hours" con confianza.
- [x] **T5.5 UI de IA** en el Detalle y la Cola: "Generando…", etiqueta "IA – no vinculante", "Requiere revisión humana", botón "Copiar mensaje".
- [x] **T5.6 `evaluate.py --with-ai`**: precisión de los mapeos IA.
  *Listo cuando:* la tabla incluye la fila de precisión IA.

## Incremento 6 — Reporte, métricas y cierre (rama `feature/reporte`)

- [x] **T6.1 Reporte HTML** autocontenido (R13.6), descargable desde el Resumen.
  *Listo cuando:* el archivo descargado se abre sin conexión y se imprime a PDF legible.
- [x] **T6.2 Pantalla Métricas** (R13.7) desde `/api/metrics`.
- [x] **T6.3 README**: problema, diagrama, frontera IA vs. código, control de incertidumbre, resultados de evaluación, limitaciones y el comando único `vercel dev`.
- [ ] **T6.4 Verificación final.** Checklist CLAUDE.md §15 en producción, `pytest` en verde, `evaluate.py` con exit 0.
  *Listo cuando:* el usuario aprueba y se fusiona a `main`.

---

## Avance

| Incremento | Estado |
|---|---|
| 0 Base verificada | **completo** |
| 1 Motor | **completo** (37 tests en verde, en rama feature/motor) |
| 2 Evaluación | **completo** (66/66 unidades detectadas, 0 disposiciones incorrectas; 43 tests) |
| 3 API | **completo** salvo la verificación de POST en Vercel, que se hace con la pantalla Nuevo lote (T4.2) |
| 4 Pantallas | **completo** (Nuevo lote, Resumen, Detalle, Revisión, Auditoría, Historial) |
| 5 IA | **completo salvo T5.4** (clave real de Anthropic en Vercel; 72 tests con IA simulada) |
| 6 Cierre | en curso (T6.1–T6.3 listas; T6.4 verificación final en producción) |
