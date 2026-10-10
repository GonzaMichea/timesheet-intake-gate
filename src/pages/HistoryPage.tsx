import { CircleCheck, Ban } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { getBatches } from "../services/api";
import type { BatchListItem } from "../types/api";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("es-CL", { dateStyle: "medium", timeStyle: "short" });
}

export default function HistoryPage() {
  useDocumentTitle("Historial de lotes");
  const [batches, setBatches] = useState<BatchListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const { data, error } = await getBatches();
    setBatches(data);
    setError(error);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <p className="text-sm font-medium uppercase tracking-widest text-graphite">Lotes validados</p>
      <h1 className="mt-2 font-display text-2xl font-extrabold">Historial</h1>

      {error && (
        <div role="alert" className="mt-8 max-w-xl border border-block p-6">
          <p className="font-medium text-block">{error}</p>
          <button type="button" onClick={load} className={`mt-4 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}>
            Reintentar conexión
          </button>
        </div>
      )}
      {!error && !batches && <p role="status" className="mt-8 text-graphite">Cargando los lotes…</p>}
      {batches && batches.length === 0 && (
        <div className="mt-8 max-w-xl border-y border-line py-8">
          <p className="font-semibold">Todavía no hay lotes validados.</p>
          <p className="mt-1 text-graphite">Sube los archivos de las sedes de un mes para crear el primero.</p>
          <Link to="/" className={`mt-4 inline-block bg-stamp px-4 py-2 text-sm font-semibold text-white hover:bg-ink ${focus}`}>
            Crear el primer lote
          </Link>
        </div>
      )}
      {batches && batches.length > 0 && (
        <ul className="mt-8 border-t border-line">
          {batches.map((batch) => {
            const Icon = batch.ready_for_load ? CircleCheck : Ban;
            return (
              <li key={batch.id} className="border-b border-line">
                <Link
                  to={`/lotes/${batch.id}`}
                  className={`grid grid-cols-[1fr_auto] items-center gap-x-6 gap-y-1 py-5 hover:bg-surface md:grid-cols-[140px_1fr_auto] ${focus}`}
                >
                  <span className="font-display text-xl font-bold tabular-nums">{batch.period}</span>
                  <span className={`inline-flex items-center gap-2 font-semibold md:order-last ${batch.ready_for_load ? "text-load" : "text-block"}`}>
                    <Icon size={18} aria-hidden="true" />
                    {batch.ready_for_load ? "Apto para carga" : "No apto para carga"}
                  </span>
                  <span className="col-span-2 text-sm text-graphite md:col-span-1">
                    {formatDate(batch.created_at)} · {batch.analyst_name} · {batch.file_count} entradas
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
