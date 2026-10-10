import { FilterX } from "lucide-react";
import { SEVERITY } from "../lib/severity";
import { hasActiveFilters, NO_FILTERS, type Filters } from "../lib/findings";
import type { Finding, Severity } from "../types/api";

const field =
  "mt-1 w-full border border-graphite bg-surface px-2 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

type Props = { findings: Finding[]; filters: Filters; onChange: (filters: Filters) => void };

function Select({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: { value: string; text: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm font-medium">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className={field}>
        <option value="">Todos</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.text}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function FindingsFilters({ findings, filters, onChange }: Props) {
  const set = (key: keyof Filters) => (value: string) => onChange({ ...filters, [key]: value });
  const unique = (values: (string | null)[]) => [...new Set(values.filter((v): v is string => !!v))].sort();

  return (
    <form
      onSubmit={(event) => event.preventDefault()}
      aria-label="Filtros de hallazgos"
      className="grid grid-cols-2 items-end gap-x-4 gap-y-3 border-y border-line py-4 md:grid-cols-6"
    >
      <Select
        label="Severidad"
        value={filters.severity}
        onChange={set("severity")}
        options={unique(findings.map((f) => f.severity)).map((s) => ({ value: s, text: SEVERITY[s as Severity].label }))}
      />
      <Select
        label="Código"
        value={filters.code}
        onChange={set("code")}
        options={unique(findings.map((f) => f.code)).map((c) => ({ value: c, text: c }))}
      />
      <Select
        label="Columna"
        value={filters.column}
        onChange={set("column")}
        options={unique(findings.map((f) => f.column)).map((c) => ({ value: c, text: c }))}
      />
      <Select
        label="Estado"
        value={filters.status}
        onChange={set("status")}
        options={[
          { value: "open", text: "Abierto" },
          { value: "resolved_by_mapping", text: "Resuelto por mapeo" },
        ]}
      />
      <label className="block text-sm font-medium">
        Número de fila
        <input
          type="number"
          min={2}
          inputMode="numeric"
          value={filters.row}
          onChange={(event) => set("row")(event.target.value)}
          placeholder="Ej. 45"
          className={`${field} tabular-nums`}
        />
      </label>
      <button
        type="button"
        disabled={!hasActiveFilters(filters)}
        onClick={() => onChange(NO_FILTERS)}
        className="inline-flex items-center justify-center gap-2 border border-ink px-3 py-2 text-sm font-semibold hover:bg-ink hover:text-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp disabled:cursor-not-allowed disabled:border-line disabled:text-graphite disabled:hover:bg-transparent"
      >
        <FilterX size={16} aria-hidden="true" />
        Limpiar filtros
      </button>
    </form>
  );
}
