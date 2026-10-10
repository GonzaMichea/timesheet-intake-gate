import { ChevronDown } from "lucide-react";
import { formatEvidence } from "../lib/findings";
import { SEVERITY } from "../lib/severity";
import type { Finding } from "../types/api";
import SampleRowsTable from "./SampleRowsTable";

const MAX_ROWS_SHOWN = 40;
const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

type Props = { finding: Finding; expanded: boolean; onToggle: () => void };

export default function FindingItem({ finding, expanded, onToggle }: Props) {
  const severity = SEVERITY[finding.severity];
  const resolved = finding.status === "resolved_by_mapping";
  const panelId = `finding-${finding.id}`;
  const shown = finding.affected_rows.slice(0, MAX_ROWS_SHOWN);

  return (
    <li className="border-b border-line">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={panelId}
        className={`grid w-full grid-cols-[1fr_auto] items-start gap-x-4 gap-y-1 py-4 text-left hover:bg-surface md:grid-cols-[72px_104px_1fr_150px_90px_20px] ${focus}`}
      >
        <span className="text-sm font-semibold tabular-nums">{finding.ref}</span>
        <span className={`text-sm font-semibold ${severity.text} md:order-none`}>
          {severity.label}
          {resolved && <span className="ml-2 text-graphite">· resuelto</span>}
        </span>
        <span className="col-span-2 text-sm md:col-span-1">
          <span className="font-semibold tabular-nums">{finding.code}</span> {finding.code_description}
        </span>
        <span className="text-sm text-graphite">{finding.column ?? "Todo el archivo"}</span>
        <span className="text-sm tabular-nums text-graphite md:text-right">
          {finding.affected_count ? `${finding.affected_count} ${finding.affected_count === 1 ? "fila" : "filas"}` : "Archivo"}
        </span>
        <ChevronDown size={18} aria-hidden="true" className={`hidden self-center md:block ${expanded ? "rotate-180" : ""}`} />
      </button>

      {expanded && (
        <div id={panelId} className="space-y-5 bg-surface px-4 pb-6 pt-4 text-sm md:pl-[72px]">
          {resolved && (
            <p className="font-medium text-load">Resuelto: el analista aceptó un mapeo de columna y el archivo se revalidó.</p>
          )}
          <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-[140px_1fr]">
            <dt className="font-semibold">Regla aplicada</dt>
            <dd>
              {finding.rule_text} <span className="text-graphite">({finding.rule_id})</span>
            </dd>
            <dt className="font-semibold">Se encontró</dt>
            <dd className="tabular-nums">{formatEvidence(finding.evidence.found)}</dd>
            <dt className="font-semibold">Se esperaba</dt>
            <dd className="tabular-nums">{formatEvidence(finding.evidence.expected)}</dd>
            {finding.evidence.candidate != null && (
              <>
                <dt className="font-semibold">Equivale a</dt>
                <dd>
                  {formatEvidence(finding.evidence.candidate)}{" "}
                  <span className="text-graphite">(puntaje {formatEvidence(finding.evidence.score)})</span>
                </dd>
              </>
            )}
            {shown.length > 0 && (
              <>
                <dt className="font-semibold">Filas afectadas</dt>
                <dd className="tabular-nums">
                  {shown.join(", ")}
                  {finding.affected_rows.length > shown.length && (
                    <span className="text-graphite"> y {finding.affected_rows.length - shown.length} más</span>
                  )}
                </dd>
              </>
            )}
          </dl>
          <SampleRowsTable rows={finding.sample_rows} highlight={finding.column} />
        </div>
      )}
    </li>
  );
}
