import { Ban, CircleCheck } from "lucide-react";
import type { BatchSummary } from "../types/api";

const TOTALS = [
  { key: "BLOCKER", label: "Bloqueantes", text: "text-block" },
  { key: "ERROR", label: "Errores", text: "text-quarantine" },
  { key: "WARNING", label: "Advertencias", text: "text-warn" },
] as const;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("es-CL", { dateStyle: "medium", timeStyle: "short" });
}

// Lo primero que se lee: el veredicto del lote. Todo lo demás lo explica
export default function BatchVerdict({ batch }: { batch: BatchSummary }) {
  const ready = batch.ready_for_load;
  const stopped = batch.entries.filter((e) => ["BLOCK", "QUARANTINE"].includes(e.final_disposition)).length;
  const Icon = ready ? CircleCheck : Ban;

  return (
    <header>
      <p className="text-sm font-medium uppercase tracking-widest text-graphite">
        Período {batch.period} · validado por {batch.analyst_name} · {formatDate(batch.created_at)}
      </p>
      <h1 className={`mt-3 flex items-center gap-3 font-display text-2xl font-extrabold ${ready ? "text-load" : "text-block"}`}>
        <Icon size={36} aria-hidden="true" className="shrink-0" />
        {ready ? "Lote apto para carga" : "Lote no apto para carga"}
      </h1>
      <p className="mt-3 max-w-xl text-base text-graphite">
        {ready
          ? "Ninguna sede quedó en cuarentena ni bloqueada."
          : `${stopped} de ${batch.entries.length} ${batch.entries.length === 1 ? "entrada" : "entradas"} no puede cargarse a nómina todavía.`}
      </p>
      <dl className="mt-8 flex flex-wrap gap-x-10 gap-y-3 border-y border-line py-4">
        {TOTALS.map(({ key, label, text }) => (
          <div key={key} className="flex items-baseline gap-2">
            <dd className={`font-display text-xl font-bold tabular-nums ${text}`}>{batch.totals[key]}</dd>
            <dt className="text-sm text-graphite">{label}</dt>
          </div>
        ))}
        {batch.processing_ms !== null && (
          <div className="flex items-baseline gap-2 sm:ml-auto">
            <dd className="font-display text-xl font-bold tabular-nums">{batch.processing_ms} ms</dd>
            <dt className="text-sm text-graphite">de procesamiento</dt>
          </div>
        )}
      </dl>
    </header>
  );
}
