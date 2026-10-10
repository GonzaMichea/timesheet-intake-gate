import { DISPOSITIONS, RANK } from "../lib/disposition";
import type { AuditEntry, Disposition, Severity } from "../types/api";

const SEVERITY_LABEL: Record<Severity, string> = { BLOCKER: "bloqueantes", ERROR: "errores", WARNING: "advertencias" };

const label = (value?: Disposition) => (value ? DISPOSITIONS[value].label : "—");

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("es-CL", { dateStyle: "medium", timeStyle: "short" });
}

// Qué hizo la persona, en una frase
function headline(entry: AuditEntry): string {
  const file = entry.after?.file ?? entry.before?.file ?? "el archivo";
  switch (entry.action) {
    case "mapping_accepted":
      return `Aceptó el mapeo «${entry.before?.column}» → ${entry.after?.target} en ${file}`;
    case "mapping_rejected":
      return `Rechazó el mapeo «${entry.before?.column}» en ${file}`;
    case "override_created":
      return `Fijó otra disposición en ${file}`;
    case "override_withdrawn":
      return `Retiró el override de ${file}`;
  }
}

// Qué cambió: la disposición final y, si varió, el conteo de hallazgos
function changes(entry: AuditEntry): string[] {
  const lines: string[] = [];
  const { before, after } = entry;
  if (entry.action === "mapping_rejected" || !before || !after) return lines;
  lines.push(
    before.final === after.final
      ? `La disposición final no cambió: sigue en ${label(after.final)}`
      : `Disposición final: ${label(before.final)} → ${label(after.final)}`,
  );
  if (entry.action === "override_created" && before.computed && after.final && RANK[after.final] < RANK[before.computed]) {
    lines.push("Override permisivo: relaja lo que calculó el código");
  }
  if (before.counts && after.counts) {
    const moved = (Object.keys(SEVERITY_LABEL) as Severity[])
      .filter((s) => before.counts![s] !== after.counts![s])
      .map((s) => `${SEVERITY_LABEL[s]} ${before.counts![s]} → ${after.counts![s]}`);
    if (moved.length) lines.push(`Hallazgos abiertos: ${moved.join(", ")}`);
  }
  return lines;
}

export default function AuditEntryItem({ entry }: { entry: AuditEntry }) {
  return (
    <li className="grid gap-x-8 gap-y-1 border-b border-line py-5 md:grid-cols-[200px_1fr]">
      <div className="text-sm text-graphite">
        <p className="tabular-nums">{formatDate(entry.created_at)}</p>
        <p className="font-semibold text-ink">{entry.actor}</p>
      </div>
      <div className="min-w-0">
        <p className="font-semibold">{headline(entry)}</p>
        <ul className="mt-1 space-y-0.5 text-sm text-graphite">
          {changes(entry).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        {entry.justification && (
          <blockquote className="mt-3 border-l-2 border-graphite pl-3 text-sm">
            <span className="font-medium">Justificación: </span>
            {entry.justification}
          </blockquote>
        )}
      </div>
    </li>
  );
}
