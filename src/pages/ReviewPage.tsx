import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import BatchTabs from "../components/BatchTabs";
import FileOverrideRow from "../components/FileOverrideRow";
import MappingReviewItem from "../components/MappingReviewItem";
import { useAnalyst } from "../context/AnalystContext";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { DISPOSITIONS } from "../lib/disposition";
import { acceptMapping, createOverride, getReviewQueue, rejectMapping, withdrawOverride } from "../services/api";
import type { ApiResult, Disposition, FileDetail, FileSummary, MappingReview, ReviewQueue } from "../types/api";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

function groupBySite(reviews: MappingReview[]): [string, MappingReview[]][] {
  const groups = new Map<string, MappingReview[]>();
  for (const review of reviews) {
    const key = review.site ?? review.filename ?? "Sin sede";
    groups.set(key, [...(groups.get(key) ?? []), review]);
  }
  return [...groups.entries()];
}

export default function ReviewPage() {
  useDocumentTitle("Cola de revisión");
  const { batchId = "" } = useParams();
  const { analyst, openDialog } = useAnalyst();
  const [queue, setQueue] = useState<ReviewQueue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { data, error } = await getReviewQueue(batchId);
    setQueue(data);
    setError(error);
  }, [batchId]);

  useEffect(() => {
    load();
  }, [load]);

  const label = (value: Disposition) => DISPOSITIONS[value].label;
  const transition = (before: FileSummary | undefined, after: FileDetail) =>
    before && before.final_disposition !== after.final_disposition
      ? `${after.site ?? after.filename} pasó de ${label(before.final_disposition)} a ${label(after.final_disposition)}.`
      : `${after.site ?? after.filename} sigue en ${label(after.final_disposition)}.`;

  // Ejecuta una acción humana; devuelve el mensaje de error o null si salió bien
  const run = async (id: string, action: () => Promise<ApiResult<FileDetail>>, message: (d: FileDetail) => string) => {
    if (!analyst) {
      openDialog();
      return "Ingresa tu nombre de analista para registrar la acción.";
    }
    setBusyId(id);
    setNotice(null);
    const result = await action();
    setBusyId(null);
    if (result.error !== null) return result.error;
    setNotice(message(result.data));
    await load();
    return null;
  };

  const fileOf = (fileId: string) => queue?.files.find((f) => f.id === fileId);

  const accept = (review: MappingReview, target: string) =>
    run(review.id, () => acceptMapping(review.id, analyst, target), (d) =>
      `Mapeo aceptado: «${review.source_column}» → ${target}. ${transition(fileOf(review.file_id), d)}`)
      .then((message) => message && setError(message));

  const reject = (review: MappingReview) =>
    run(review.id, () => rejectMapping(review.id, analyst), () => `Mapeo rechazado: «${review.source_column}» se mantiene como hallazgo.`)
      .then((message) => message && setError(message));

  const changeOverride = (file: FileSummary, disposition: Disposition | null, justification: string) =>
    run(file.id,
      () => (disposition ? createOverride(file.id, analyst, disposition, justification) : withdrawOverride(file.id, analyst, justification)),
      (d) => (disposition ? `Override guardado. ${transition(file, d)}` : `Override retirado. ${transition(file, d)}`));

  if (!queue) {
    return error ? (
      <div role="alert" className="max-w-xl border border-block p-6">
        <p className="font-medium text-block">{error}</p>
        <button type="button" onClick={load} className={`mt-4 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}>
          Reintentar conexión
        </button>
      </div>
    ) : (
      <p role="status" className="text-graphite">Cargando la cola de revisión…</p>
    );
  }

  return (
    <div>
      <BatchTabs batchId={batchId} pendingReviews={queue.pending.length} />
      <h1 className="font-display text-2xl font-extrabold">Cola de revisión</h1>
      <p className="mt-3 max-w-2xl text-graphite">
        Nada se aplica solo: aquí decides qué columnas renombradas se aceptan y si alguna disposición necesita una
        excepción. Cada acción queda en la auditoría con tu nombre.
      </p>
      <div role="status" aria-live="polite">
        {notice && <p className="mt-6 border-l-4 border-load bg-surface p-4 text-sm font-medium">{notice}</p>}
      </div>
      {error && <p role="alert" className="mt-6 border-l-4 border-block bg-surface p-4 text-sm font-medium text-block">{error}</p>}

      <section aria-labelledby="mappings-title" className="mt-12">
        <h2 id="mappings-title" className="border-b border-ink pb-2 font-display text-lg font-bold">
          Columnas por revisar <span className="ml-2 tabular-nums text-graphite">{queue.pending.length}</span>
        </h2>
        {queue.pending.length === 0 ? (
          <p className="mt-4 text-graphite">No quedan columnas pendientes: todas fueron aceptadas o rechazadas.</p>
        ) : (
          groupBySite(queue.pending).map(([site, reviews]) => (
            <div key={site} className="mt-6">
              <h3 className="font-display text-lg font-bold">{site}</h3>
              <ul>
                {reviews.map((review) => (
                  <MappingReviewItem key={review.id} review={review} busy={busyId === review.id}
                    onAccept={(target) => accept(review, target)} onReject={() => reject(review)} />
                ))}
              </ul>
            </div>
          ))
        )}
      </section>

      <section aria-labelledby="override-title" className="mt-14">
        <h2 id="override-title" className="border-b border-ink pb-2 font-display text-lg font-bold">
          Disposición final por archivo
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-graphite">
          Puedes fijar otra disposición si tienes contexto que el sistema no tiene. La justificación es obligatoria y
          el código siempre conserva lo que calculó.
        </p>
        <ul>
          {queue.files.map((file) => (
            <FileOverrideRow key={file.id} file={file} onChange={changeOverride} />
          ))}
        </ul>
      </section>
    </div>
  );
}
