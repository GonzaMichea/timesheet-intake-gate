import type { DefectBrief, FileSummary, Severity } from "../types/api";
import DispositionSeal from "./DispositionSeal";
import RowRibbon from "./RowRibbon";

const SEVERITY: Record<Severity, { label: string; text: string }> = {
  BLOCKER: { label: "Bloqueante", text: "text-block" },
  ERROR: { label: "Error", text: "text-quarantine" },
  WARNING: { label: "Advertencia", text: "text-warn" },
};

// Qué columnas o filas explican el defecto; en defectos de archivo, lo encontrado frente a lo esperado
function defectDetail(defect: DefectBrief): string {
  const parts: string[] = [];
  if (defect.columns.length) parts.push(defect.columns.join(", "));
  if (defect.rows) parts.push(`${defect.rows} ${defect.rows === 1 ? "fila" : "filas"}`);
  if (!parts.length) {
    if (defect.found) parts.push(`encontrado: ${defect.found}`);
    if (defect.expected) parts.push(`esperado: ${defect.expected}`);
  }
  return parts.join(" · ");
}

function title(entry: FileSummary): string {
  if (entry.site) return entry.site;
  return "Fuera de patrón";
}

function subtitle(entry: FileSummary): string {
  if (entry.kind === "missing") return "Archivo no recibido";
  const rows = entry.row_count ? ` · ${entry.row_count.toLocaleString("es-CL")} filas` : "";
  return `${entry.filename}${rows}`;
}

export default function SiteRow({ entry }: { entry: FileSummary }) {
  return (
    <li className="border-b border-line py-8">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 className="font-display text-xl font-bold">{title(entry)}</h2>
          <p className="mt-1 break-all text-sm tabular-nums text-graphite">{subtitle(entry)}</p>
        </div>
        <DispositionSeal entry={entry} />
      </div>

      <div className="mt-5">
        <RowRibbon ribbon={entry.ribbon} />
        {entry.row_count > 0 && entry.defects.length > 0 && !/[WEB]/.test(entry.ribbon) && (
          <p className="mt-2 text-sm text-graphite">
            Ninguna fila concreta falla: el problema está en la estructura del archivo.
          </p>
        )}
      </div>

      {entry.defects.length === 0 ? (
        <p className="mt-4 text-sm text-graphite">Sin hallazgos: el archivo cumple el contrato.</p>
      ) : (
        <div className="mt-5">
          <p className="text-sm font-semibold">
            Por qué: <span className="font-normal text-graphite">{entry.disposition_explanation}</span>
          </p>
          <ul className="mt-3 space-y-2">
            {entry.defects.map((defect) => (
              <li key={defect.code} className="grid grid-cols-[88px_1fr] gap-x-3 text-sm sm:grid-cols-[104px_1fr]">
                <span className={`font-semibold ${SEVERITY[defect.severity].text}`}>
                  {SEVERITY[defect.severity].label}
                </span>
                <span>
                  <span className="font-semibold tabular-nums">{defect.code}</span> {defect.description}
                  {defectDetail(defect) && <span className="text-graphite"> — {defectDetail(defect)}</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}
