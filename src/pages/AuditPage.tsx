import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import AuditEntryItem from "../components/AuditEntryItem";
import BatchTabs from "../components/BatchTabs";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { getAudit } from "../services/api";
import type { AuditEntry } from "../types/api";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

export default function AuditPage() {
  useDocumentTitle("Auditoría del lote");
  const { batchId = "" } = useParams();
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const { data, error } = await getAudit(batchId);
    setEntries(data);
    setError(error);
  }, [batchId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <BatchTabs batchId={batchId} />
      <h1 className="font-display text-2xl font-extrabold">Auditoría del lote</h1>
      <p className="mt-3 max-w-2xl text-graphite">
        Registro de cada decisión humana: quién, qué, cuándo y el estado antes y después. Solo se puede leer: nadie
        puede editarlo ni borrarlo.
      </p>

      {error && (
        <div role="alert" className="mt-8 max-w-xl border border-block p-6">
          <p className="font-medium text-block">{error}</p>
          <button type="button" onClick={load} className={`mt-4 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}>
            Reintentar conexión
          </button>
        </div>
      )}
      {!error && !entries && <p role="status" className="mt-8 text-graphite">Cargando la auditoría…</p>}
      {entries && entries.length === 0 && (
        <p className="mt-8 border-y border-line py-6 text-graphite">
          Todavía no hay acciones registradas en este lote. Aparecerán aquí cuando aceptes o rechaces un mapeo, o
          cambies una disposición.
        </p>
      )}
      {entries && entries.length > 0 && (
        <ol className="mt-8 border-t border-line" aria-label="Acciones registradas, de la más reciente a la más antigua">
          {[...entries].reverse().map((entry) => (
            <AuditEntryItem key={entry.id} entry={entry} />
          ))}
        </ol>
      )}
    </div>
  );
}
