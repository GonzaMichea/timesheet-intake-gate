// Espejo manual de los modelos pydantic del backend (design D-12)

export type Disposition = "LOAD" | "LOAD_WITH_WARNINGS" | "QUARANTINE" | "BLOCK";
export type Severity = "BLOCKER" | "ERROR" | "WARNING";

export type SeverityCounts = Record<Severity, number>;

export type DefectBrief = {
  code: string;
  description: string;
  severity: Severity;
  columns: string[];
  rows: number;
  found: string | null;
  expected: string | null;
};

export type FileSummary = {
  id: string;
  batch_id: string;
  kind: "site_file" | "unexpected" | "missing";
  filename: string | null;
  site: string | null;
  row_count: number;
  computed_disposition: Disposition;
  final_disposition: Disposition;
  disposition_rule: string | null;
  disposition_explanation: string | null;
  override_active: boolean;
  permissive_override: boolean;
  calculated_changed_after_override: boolean;
  counts: SeverityCounts;
  defects: DefectBrief[];
  // Un carácter por fila: "." sin hallazgos, W advertencia, E error, B bloqueante
  ribbon: string;
};

export type BatchSummary = {
  id: string;
  period: string;
  analyst_name: string;
  created_at: string;
  processing_ms: number | null;
  contract_hash: string;
  ready_for_load: boolean;
  totals: SeverityCounts;
  entries: FileSummary[];
};

export type ContractInfo = {
  sites: string[];
  code_descriptions: Record<string, string>;
  quarantine_error_row_pct: number;
  ai_min_confidence: number;
  max_upload_mb: number;
};

export type ApiResult<T> =
  | { data: T; error: null }
  | { data: null; error: string };
