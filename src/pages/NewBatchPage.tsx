import { LoaderCircle, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import DispositionLegend from "../components/DispositionLegend";
import FileDropzone from "../components/FileDropzone";
import SiteChecklist from "../components/SiteChecklist";
import { useAnalyst } from "../context/AnalystContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { isValidPeriod, previousMonth } from "../lib/format";
import { createBatch, getContract } from "../services/api";
import type { ContractInfo } from "../types/api";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

function Step({ number, title }: { number: string; title: string }) {
  return (
    <h2 className="flex items-baseline gap-3 border-b border-ink pb-2 font-display text-lg font-bold">
      <span className="tabular-nums text-graphite">{number}</span>
      {title}
    </h2>
  );
}

export default function NewBatchPage() {
  useDocumentTitle("Nuevo lote");
  const navigate = useNavigate();
  const { analyst, openDialog } = useAnalyst();
  const [contract, setContract] = useState<ContractInfo | null>(null);
  const [contractError, setContractError] = useState<string | null>(null);
  const [period, setPeriod] = useState(previousMonth);
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadContract = useCallback(async () => {
    setContractError(null);
    const { data, error } = await getContract();
    setContract(data);
    setContractError(error);
  }, []);

  useEffect(() => {
    loadContract();
  }, [loadContract]);

  const addFiles = (incoming: File[]) =>
    setFiles((current) => [
      ...current,
      ...incoming.filter((f) => !current.some((c) => c.name === f.name && c.size === f.size)),
    ]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!analyst) return openDialog();
    const maxMb = contract?.max_upload_mb ?? 4;
    if (files.reduce((sum, f) => sum + f.size, 0) > maxMb * 1024 * 1024) {
      return setError(`Los archivos superan el máximo de ${maxMb} MB por lote. Quita alguno o divide el envío.`);
    }
    setSubmitting(true);
    const { data, error: apiError } = await createBatch(period, analyst, files);
    setSubmitting(false);
    if (data) navigate(`/lotes/${data.id}`);
    else setError(apiError);
  };

  const canSubmit = isValidPeriod(period) && files.length > 0 && !submitting;

  return (
    <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-16">
      <form onSubmit={submit} noValidate>
        <p className="text-sm font-medium uppercase tracking-widest text-graphite">Hojas de tiempo mensuales</p>
        <h1 className="mt-2 font-display text-2xl font-extrabold">Nuevo lote</h1>
        <p className="mt-4 max-w-xl text-base text-graphite">
          Revisa los archivos de horas de las cuatro sedes antes de que lleguen a nómina. Aquí solo se validan: nada se
          carga.
        </p>

        <section className="mt-10">
          <Step number="1" title="Período" />
          <label htmlFor="period" className="mt-4 block text-sm font-medium">
            Mes que se va a cargar
          </label>
          <input
            id="period"
            type="month"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            pattern="\d{4}-\d{2}"
            placeholder="AAAA-MM"
            disabled={submitting}
            aria-invalid={!isValidPeriod(period)}
            className={`mt-1 w-full max-w-[220px] border border-graphite bg-surface px-3 py-2 text-base tabular-nums ${focus}`}
          />
          {!isValidPeriod(period) && (
            <p role="alert" className="mt-2 text-sm font-medium text-block">
              Elige un mes válido, con el formato AAAA-MM.
            </p>
          )}
        </section>

        <section className="mt-10">
          <Step number="2" title="Archivos de las sedes" />
          <div className="mt-4">
            <FileDropzone
              files={files}
              disabled={submitting}
              onAdd={addFiles}
              onRemove={(index) => setFiles((current) => current.filter((_, i) => i !== index))}
            />
          </div>
          <div className="mt-6">
            {contract && isValidPeriod(period) && (
              <SiteChecklist sites={contract.sites} period={period} fileNames={files.map((f) => f.name)} />
            )}
            {!contract && !contractError && (
              <p className="text-sm text-graphite" role="status">
                Cargando las sedes esperadas…
              </p>
            )}
            {contractError && (
              <div role="alert" className="border border-block p-4">
                <p className="text-sm font-medium text-block">{contractError}</p>
                <button
                  type="button"
                  onClick={loadContract}
                  className={`mt-3 border border-ink px-3 py-1.5 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}
                >
                  Reintentar conexión
                </button>
              </div>
            )}
          </div>
        </section>

        {error && (
          <p role="alert" className="mt-8 border-l-4 border-block bg-surface p-4 text-sm font-medium text-block">
            {error}
          </p>
        )}

        <div className="mt-10 flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={!canSubmit}
            className={`inline-flex items-center gap-2 bg-stamp px-6 py-3 text-base font-semibold text-white hover:bg-ink disabled:cursor-not-allowed disabled:bg-line disabled:text-graphite ${focus}`}
          >
            {submitting ? (
              <LoaderCircle size={18} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
            ) : (
              <ShieldCheck size={18} aria-hidden="true" />
            )}
            {submitting ? "Validando lote…" : "Validar lote"}
          </button>
          {files.length === 0 && <span className="text-sm text-graphite">Sube al menos un archivo para validar.</span>}
        </div>
      </form>

      <div className="lg:border-l lg:border-line lg:pl-10">
        <DispositionLegend quarantinePct={contract?.quarantine_error_row_pct ?? null} />
      </div>
    </div>
  );
}
