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

export type Finding = {
  id: string;
  ref: string;
  code: string;
  code_description: string;
  severity: Severity;
  column: string | null;
  rule_id: string;
  rule_text: string;
  affected_count: number;
  affected_rows: number[];
  sample_rows: Record<string, unknown>[];
  evidence: Record<string, unknown>;
  status: "open" | "resolved_by_mapping";
};

export type AiStatus = "ok" | "no_disponible" | "invalido";

export type AiSuggestion = {
  target_column: string;
  confidence: number;
  justification: string;
  needs_review: boolean;
};

export type AiStatement = { text: string; finding_refs: string[]; confidence: number; needs_review: boolean; unsupported: boolean };
export type AiRemediation = { subject: string; body: string; finding_refs: string[]; confidence: number; needs_review: boolean; unsupported: boolean };

export type AiResult = {
  id: string;
  kind: "mapping" | "cause" | "remediation";
  status: AiStatus;
  model: string | null;
  latency_ms: number | null;
  reason: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
};

export type MappingReview = {
  id: string;
  file_id: string;
  filename: string | null;
  site: string | null;
  source_column: string;
  candidate_column: string | null;
  candidate_score: number | null;
  status: "pending" | "accepted" | "rejected";
  chosen_column: string | null;
  decided_by: string | null;
  decided_at: string | null;
  missing_columns: string[];
  ai_suggestion: AiSuggestion | null;
};

export type ReviewQueue = {
  pending: MappingReview[];
  files: FileSummary[];
  ai_mapping: Record<string, { status: AiStatus; reason: string | null } | null>;
};

export type OverrideEntry = {
  id: string;
  disposition: Disposition | null;
  justification: string;
  actor: string;
  created_at: string;
  computed_disposition: Disposition | null;
};

export type FileDetail = FileSummary & {
  period: string;
  findings: Finding[];
  mappings: MappingReview[];
  overrides: OverrideEntry[];
  missing_columns: string[];
  required_columns: string[];
  ai: Partial<Record<AiResult["kind"], AiResult>>;
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
  pending_reviews: number;
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

export type BatchListItem = {
  id: string;
  period: string;
  analyst_name: string;
  created_at: string;
  ready_for_load: boolean;
  file_count: number;
};

export type AuditSnapshot = {
  file?: string;
  column?: string;
  target?: string;
  status?: string;
  computed?: Disposition;
  final?: Disposition;
  counts?: SeverityCounts;
};

export type AuditEntry = {
  id: string;
  created_at: string;
  actor: string;
  action: "mapping_accepted" | "mapping_rejected" | "override_created" | "override_withdrawn";
  entity_type: string;
  entity_id: string;
  before: AuditSnapshot | null;
  after: AuditSnapshot | null;
  justification: string | null;
};

export type EvaluationBatch = {
  batch: string;
  ms: number;
  files: number;
  wrong_dispositions: { file: string; expected: string | null; computed: string | null }[];
};

export type Evaluation = {
  generated_at: string;
  summary: {
    by_code: Record<string, { expected: number; detected: number; false_positives: number }>;
    detection: number | null;
    false_positive_rate: number | null;
    disposition_accuracy: number | null;
    wrong_dispositions: number;
    d05_precision: number | null;
    ai: { precision: number | null; suggestions: number; correct: number; unavailable: string | null } | null;
    units: { expected: number; detected: number; found: number };
  };
  batches: EvaluationBatch[];
};
