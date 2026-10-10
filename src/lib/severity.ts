import type { Severity } from "../types/api";

export const SEVERITY: Record<Severity, { label: string; text: string }> = {
  BLOCKER: { label: "Bloqueante", text: "text-block" },
  ERROR: { label: "Error", text: "text-quarantine" },
  WARNING: { label: "Advertencia", text: "text-warn" },
};
