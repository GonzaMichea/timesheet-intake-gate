import { useState } from "react";
import type { MappingReview } from "../types/api";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

type Props = {
  review: MappingReview;
  busy: boolean;
  onAccept: (target: string) => void;
  onReject: () => void;
};

export default function MappingReviewItem({ review, busy, onAccept, onReject }: Props) {
  const options = review.missing_columns;
  const [target, setTarget] = useState(
    review.candidate_column && options.includes(review.candidate_column) ? review.candidate_column : "",
  );
  const selectId = `target-${review.id}`;

  return (
    <li className="grid gap-x-8 gap-y-4 border-b border-line py-6 md:grid-cols-[1fr_auto]">
      <div className="min-w-0">
        <p className="font-semibold">
          Columna <span className="tabular-nums">«{review.source_column}»</span>
        </p>
        <p className="mt-1 text-sm text-graphite">
          {review.candidate_column
            ? `El sistema la considera equivalente a ${review.candidate_column} (puntaje ${(review.candidate_score ?? 0)
                .toFixed(2)
                .replace(".", ",")}).`
            : "El sistema no encontró una columna requerida parecida."}
        </p>
        <p className="mt-1 text-sm text-graphite">
          {options.length
            ? `Faltan en el archivo: ${options.join(", ")}.`
            : "El archivo ya tiene todas las columnas requeridas: esta columna solo puede rechazarse."}
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor={selectId} className="block text-sm font-medium">
            Usar como
          </label>
          <select
            id={selectId}
            value={target}
            disabled={busy || options.length === 0}
            onChange={(event) => setTarget(event.target.value)}
            className={`mt-1 min-w-[180px] border border-graphite bg-surface px-2 py-2 text-sm disabled:border-line disabled:text-graphite ${focus}`}
          >
            <option value="">Elige una columna</option>
            {options.map((column) => (
              <option key={column} value={column}>
                {column}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          disabled={busy || target === ""}
          onClick={() => onAccept(target)}
          className={`bg-stamp px-4 py-2 text-sm font-semibold text-white hover:bg-ink disabled:cursor-not-allowed disabled:bg-line disabled:text-graphite ${focus}`}
        >
          Aceptar mapeo
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onReject}
          className={`border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper disabled:cursor-not-allowed disabled:border-line disabled:text-graphite disabled:hover:bg-transparent ${focus}`}
        >
          Rechazar
        </button>
      </div>
    </li>
  );
}
