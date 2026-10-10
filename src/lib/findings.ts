import type { Finding } from "../types/api";

export type Filters = {
  severity: string;
  code: string;
  column: string;
  status: string;
  row: string;
};

export const NO_FILTERS: Filters = { severity: "", code: "", column: "", status: "", row: "" };

export function filterFindings(findings: Finding[], filters: Filters): Finding[] {
  const row = Number.parseInt(filters.row, 10);
  return findings.filter(
    (f) =>
      (!filters.severity || f.severity === filters.severity) &&
      (!filters.code || f.code === filters.code) &&
      (!filters.column || f.column === filters.column) &&
      (!filters.status || f.status === filters.status) &&
      (Number.isNaN(row) || f.affected_rows.includes(row)),
  );
}

export function hasActiveFilters(filters: Filters): boolean {
  return Object.values(filters).some((value) => value !== "");
}

// La evidencia llega como JSON libre: se muestra en texto legible
export function formatEvidence(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, val]) => `fila ${key} repite la fila ${String(val)}`)
      .join("; ");
  }
  return String(value);
}
