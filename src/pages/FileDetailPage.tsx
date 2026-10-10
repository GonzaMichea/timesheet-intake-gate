import { ArrowLeft } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AiPlaceholder from "../components/AiPlaceholder";
import DispositionSeal from "../components/DispositionSeal";
import FindingItem from "../components/FindingItem";
import FindingsFilters from "../components/FindingsFilters";
import RowRibbon from "../components/RowRibbon";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { filterFindings, NO_FILTERS, type Filters } from "../lib/findings";
import { getFile } from "../services/api";
import type { FileDetail } from "../types/api";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

export default function FileDetailPage() {
  const { batchId = "", fileId = "" } = useParams();
  const [file, setFile] = useState<FileDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  useDocumentTitle(file ? `Detalle de ${file.site ?? file.filename}` : "Detalle de archivo");

  const load = useCallback(async () => {
    setError(null);
    const { data, error } = await getFile(fileId);
    setFile(data);
    setError(error);
  }, [fileId]);

  useEffect(() => {
    load();
  }, [load]);

  const visible = useMemo(() => (file ? filterFindings(file.findings, filters) : []), [file, filters]);
  const toggle = (id: string) =>
    setExpanded((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  const back = (
    <Link to={`/lotes/${batchId}`} className={`inline-flex items-center gap-2 text-sm font-semibold underline underline-offset-4 ${focus}`}>
      <ArrowLeft size={16} aria-hidden="true" />
      Volver al resumen del lote
    </Link>
  );

  if (error) {
    return (
      <div>
        {back}
        <div role="alert" className="mt-6 max-w-xl border border-block p-6">
          <p className="font-medium text-block">{error}</p>
          <button type="button" onClick={load} className={`mt-4 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}>
            Reintentar conexión
          </button>
        </div>
      </div>
    );
  }
  if (!file) return <p role="status" className="text-graphite">Cargando el detalle del archivo…</p>;

  return (
    <div>
      {back}
      <header className="mt-6 flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <p className="text-sm font-medium uppercase tracking-widest text-graphite">Detalle de archivo · período {file.period}</p>
          <h1 className="mt-2 font-display text-2xl font-extrabold">{file.site ?? "Fuera de patrón"}</h1>
          <p className="mt-1 break-all text-sm tabular-nums text-graphite">
            {file.filename ?? "Archivo no recibido"}
            {file.row_count > 0 && ` · ${file.row_count.toLocaleString("es-CL")} filas`}
          </p>
        </div>
        <DispositionSeal entry={file} />
      </header>

      <p className="mt-6 max-w-2xl text-sm">
        <span className="font-semibold">Por qué: </span>
        <span className="text-graphite">
          {file.disposition_explanation}
          {file.disposition_rule && ` (regla ${file.disposition_rule})`}
        </span>
      </p>

      <div className="mt-6">
        <RowRibbon ribbon={file.ribbon} onPick={(row) => setFilters({ ...NO_FILTERS, row: String(row) })} />
        {/[WEB]/.test(file.ribbon) && (
          <p className="mt-2 text-sm text-graphite">Haz clic en una marca de la cinta para ver los hallazgos de esa fila.</p>
        )}
      </div>

      <section aria-labelledby="findings-title" className="mt-12">
        <h2 id="findings-title" className="border-b border-ink pb-2 font-display text-lg font-bold">
          Hallazgos
        </h2>
        {file.findings.length === 0 ? (
          <p className="mt-4 text-graphite">Este archivo no tiene hallazgos: cumple el contrato.</p>
        ) : (
          <>
            <div className="mt-4">
              <FindingsFilters findings={file.findings} filters={filters} onChange={setFilters} />
            </div>
            <p className="mt-3 text-sm text-graphite" role="status">
              Mostrando {visible.length} de {file.findings.length} hallazgos
            </p>
            {visible.length === 0 ? (
              <p className="mt-4 text-sm font-medium">Ningún hallazgo coincide con los filtros. Prueba con otra fila o limpia los filtros.</p>
            ) : (
              <ul className="mt-2 border-t border-line">
                {visible.map((finding) => (
                  <FindingItem key={finding.id} finding={finding} expanded={expanded.has(finding.id)} onToggle={() => toggle(finding.id)} />
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <AiPlaceholder />
    </div>
  );
}
