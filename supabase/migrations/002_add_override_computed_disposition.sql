-- Guarda qué disposición calculada había cuando se creó cada override.
-- Permite avisar "La disposición calculada cambió después del override" (R9.5).
alter table public.overrides add column computed_disposition text
  check (computed_disposition in ('LOAD', 'LOAD_WITH_WARNINGS', 'QUARANTINE', 'BLOCK'));
