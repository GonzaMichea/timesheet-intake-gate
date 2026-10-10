import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { DISPOSITIONS } from "../lib/disposition";
import { getBatch } from "../services/api";
import type { BatchSummary } from "../types/api";

// Versión provisional: el resumen completo con la cinta de filas llega en la tarea T4.3
export default function BatchSummaryPage() {
  useDocumentTitle("Resumen del lote");
  const { batchId = "" } = useParams();
  const [batch, setBatch] = useState<BatchSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const { data, error } = await getBatch(batchId);
    setBatch(data);
    setError(error);
  }, [batchId]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return (
      <div role="alert">
        <p className="font-medium text-block">{error}</p>
        <button
          type="button"
          onClick={load}
          className="mt-4 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp"
        >
          Reintentar conexión
        </button>
      </div>
    );
  }
  if (!batch) return <p role="status" className="text-graphite">Cargando el lote…</p>;

  return (
    <div>
      <p className="text-sm font-medium uppercase tracking-widest text-graphite">Período {batch.period}</p>
      <h1 className="mt-2 font-display text-2xl font-extrabold">
        {batch.ready_for_load ? "Lote apto para carga" : "Lote no apto para carga"}
      </h1>
      <ul className="mt-8 divide-y divide-line border-y border-line">
        {batch.entries.map((entry) => {
          const { label, Icon, text } = DISPOSITIONS[entry.final_disposition];
          return (
            <li key={entry.id} className="flex flex-wrap items-center gap-x-6 gap-y-1 py-4">
              <span className="w-20 font-display text-lg font-bold">{entry.site ?? "Sin sede"}</span>
              <span className="min-w-0 flex-1 truncate text-sm tabular-nums text-graphite">
                {entry.filename ?? "Archivo no recibido"}
              </span>
              <span className={`inline-flex items-center gap-2 font-semibold ${text}`}>
                <Icon size={18} aria-hidden="true" />
                {label}
              </span>
            </li>
          );
        })}
      </ul>
      <Link
        to="/"
        className="mt-8 inline-block text-sm font-semibold underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp"
      >
        Validar otro lote
      </Link>
    </div>
  );
}
