import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import BatchTabs from "../components/BatchTabs";
import BatchVerdict from "../components/BatchVerdict";
import SiteRow from "../components/SiteRow";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { getBatch } from "../services/api";
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
      <Link to="/" className={`mt-8 inline-block text-sm font-semibold underline underline-offset-4 ${focus}`}>
        Validar otro lote
      </Link>
    </div>
  );
}
