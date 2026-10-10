import { useCallback, useEffect, useState } from "react";
import { Download, Printer } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import BatchTabs from "../components/BatchTabs";
import BatchVerdict from "../components/BatchVerdict";
import SiteRow from "../components/SiteRow";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { getBatch, reportUrl } from "../services/api";
import type { BatchSummary } from "../types/api";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

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
      <div role="alert" className="max-w-xl border border-block p-6">
        <p className="font-medium text-block">{error}</p>
        <button
          type="button"
          onClick={load}
          className={`mt-4 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}
        >
          Reintentar conexión
        </button>
      </div>
    );
  }
  if (!batch) {
    return (
      <p role="status" className="text-graphite">
        Cargando el resumen del lote…
      </p>
    );
  }

  return (
    <div>
      <BatchTabs batchId={batch.id} pendingReviews={batch.pending_reviews} />
      <BatchVerdict batch={batch} />
      {batch.entries.length === 0 ? (
        <p className="mt-8 text-graphite">Este lote no tiene entradas para mostrar.</p>
      ) : (
        <ul className="mt-2" aria-label="Resultado por sede">
          {batch.entries.map((entry) => (
            <SiteRow key={entry.id} entry={entry} />
          ))}
        </ul>
      )}
      <div className="mt-8 flex flex-wrap items-center gap-x-8 gap-y-3">
        <a href={reportUrl(batch.id, true)} target="_blank" rel="noreferrer" className={`inline-flex items-center gap-2 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}>
          <Printer size={16} aria-hidden="true" />
          Ver reporte para imprimir
        </a>
        <a href={reportUrl(batch.id, false)} download className={`inline-flex items-center gap-2 text-sm font-semibold underline underline-offset-4 ${focus}`}>
          <Download size={16} aria-hidden="true" />
          Descargar reporte HTML
        </a>
        <Link to="/" className={`text-sm font-semibold underline underline-offset-4 ${focus}`}>
          Validar otro lote
        </Link>
      </div>
    </div>
  );
}
