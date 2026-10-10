-- Crea las 7 tablas del sistema, activa RLS en todas y define el rol que usa la API.
-- Ejecutar completo en Supabase > SQL Editor. Después, asignar la contraseña de tig_api (ver README / tasks T0.6).

-- 1. Rol de la API (sin contraseña; se asigna aparte para que nunca quede en el repositorio)
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'tig_api') then
    create role tig_api login;
  end if;
end $$;

grant usage on schema public to tig_api;

-- 2. Tablas
create table public.batches (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  period text not null check (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
  analyst_name text not null,
  contract_yaml text not null,
  master_csv text not null,
  contract_hash text not null,
  processing_ms integer,
  ready_for_load boolean not null default false
);

create table public.batch_files (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  batch_id uuid not null references public.batches(id) on delete cascade,
  kind text not null check (kind in ('site_file', 'unexpected', 'missing')),
  filename text,
  site text,
  content bytea,
  row_count integer,
  applied_mapping jsonb not null default '{}'::jsonb,
  computed_disposition text not null
    check (computed_disposition in ('LOAD', 'LOAD_WITH_WARNINGS', 'QUARANTINE', 'BLOCK')),
  disposition_rule text,
  disposition_explanation text,
  processing_ms integer
);
create index batch_files_batch_id_idx on public.batch_files(batch_id);

create table public.findings (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  file_id uuid not null references public.batch_files(id) on delete cascade,
  ref text not null,
  code text not null check (code ~ '^D(0[1-9]|1[0-2])$'),
  severity text not null check (severity in ('BLOCKER', 'ERROR', 'WARNING')),
  column_name text,
  rule_id text not null,
  rule_text text not null,
  affected_count integer not null default 0,
  affected_rows jsonb not null default '[]'::jsonb,
  sample_rows jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '{}'::jsonb,
  status text not null default 'open' check (status in ('open', 'resolved_by_mapping')),
  unique (file_id, ref)
);
create index findings_file_id_idx on public.findings(file_id);

create table public.mapping_reviews (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  file_id uuid not null references public.batch_files(id) on delete cascade,
  source_column text not null,
  candidate_column text,
  candidate_score numeric(4, 3),
  status text not null default 'pending' check (status in ('pending', 'accepted', 'rejected')),
  chosen_column text,
  decided_by text,
  decided_at timestamptz,
  unique (file_id, source_column)
);
create index mapping_reviews_file_id_idx on public.mapping_reviews(file_id);

-- Solo inserción: vale la última fila de cada archivo (disposition null = override retirado)
create table public.overrides (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  file_id uuid not null references public.batch_files(id) on delete cascade,
  disposition text check (disposition in ('LOAD', 'LOAD_WITH_WARNINGS', 'QUARANTINE', 'BLOCK')),
  justification text not null check (char_length(btrim(justification)) >= 20),
  actor text not null
);
create index overrides_file_id_idx on public.overrides(file_id);

create table public.ai_results (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  file_id uuid not null references public.batch_files(id) on delete cascade,
  kind text not null check (kind in ('mapping', 'cause', 'remediation')),
  status text not null check (status in ('ok', 'no_disponible', 'invalido')),
  model text,
  latency_ms integer,
  payload jsonb,
  reason text,
  is_stale boolean not null default false
);
create index ai_results_file_id_idx on public.ai_results(file_id);

-- Solo inserción: bitácora de acciones humanas
create table public.audit_log (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  batch_id uuid not null references public.batches(id) on delete cascade,
  actor text not null,
  action text not null,
  entity_type text not null,
  entity_id text not null,
  before jsonb,
  after jsonb,
  justification text
);
create index audit_log_batch_id_idx on public.audit_log(batch_id);

-- 3. Seguridad: RLS activo en todas las tablas y ningún acceso para anon / authenticated
alter table public.batches enable row level security;
alter table public.batch_files enable row level security;
alter table public.findings enable row level security;
alter table public.mapping_reviews enable row level security;
alter table public.overrides enable row level security;
alter table public.ai_results enable row level security;
alter table public.audit_log enable row level security;

revoke all on all tables in schema public from anon, authenticated;

-- 4. Permisos y políticas de tig_api (el único rol con acceso)
grant select, insert, update, delete on public.batches, public.batch_files, public.findings,
  public.mapping_reviews, public.ai_results to tig_api;
grant select, insert on public.overrides, public.audit_log to tig_api;

create policy tig_api_all on public.batches for all to tig_api using (true) with check (true);
create policy tig_api_all on public.batch_files for all to tig_api using (true) with check (true);
create policy tig_api_all on public.findings for all to tig_api using (true) with check (true);
create policy tig_api_all on public.mapping_reviews for all to tig_api using (true) with check (true);
create policy tig_api_all on public.ai_results for all to tig_api using (true) with check (true);
create policy tig_api_select on public.overrides for select to tig_api using (true);
create policy tig_api_insert on public.overrides for insert to tig_api with check (true);
create policy tig_api_select on public.audit_log for select to tig_api using (true);
create policy tig_api_insert on public.audit_log for insert to tig_api with check (true);

-- 5. Defensa extra: ni siquiera un rol con permisos puede modificar o borrar estas dos tablas
create or replace function public.reject_modification() returns trigger
language plpgsql as $$
begin
  raise exception 'La tabla % es de solo inserción', tg_table_name;
end $$;

create trigger audit_log_append_only before update or delete on public.audit_log
  for each row execute function public.reject_modification();
create trigger overrides_append_only before update or delete on public.overrides
  for each row execute function public.reject_modification();
