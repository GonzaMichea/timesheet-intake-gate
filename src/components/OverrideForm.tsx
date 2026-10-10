import { useState, type FormEvent } from "react";
import { DISPOSITIONS, RANK } from "../lib/disposition";
import type { Disposition, FileSummary } from "../types/api";

const MIN_JUSTIFICATION = 20;
const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

type Props = {
  file: FileSummary;
  mode: "set" | "withdraw";
  onSubmit: (disposition: Disposition | null, justification: string) => Promise<string | null>;
  onCancel: () => void;
};

export default function OverrideForm({ file, mode, onSubmit, onCancel }: Props) {
  const options = (Object.keys(DISPOSITIONS) as Disposition[]).filter((d) => d !== file.final_disposition);
  const [disposition, setDisposition] = useState<Disposition>(options[0]);
  const [justification, setJustification] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const length = justification.trim().length;
  const relaxes = mode === "set" && RANK[disposition] < RANK[file.computed_disposition];
  const id = `justification-${file.id}`;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(await onSubmit(mode === "set" ? disposition : null, justification.trim()));
    setSaving(false);
  };

  return (
    <form onSubmit={submit} className="mt-4 max-w-xl border-l-4 border-ink bg-surface p-4">
      {mode === "set" ? (
        <div>
          <label htmlFor={`disposition-${file.id}`} className="block text-sm font-medium">
            Nueva disposición
          </label>
          <select
            id={`disposition-${file.id}`}
            value={disposition}
            onChange={(event) => setDisposition(event.target.value as Disposition)}
            disabled={saving}
            className={`mt-1 border border-graphite bg-surface px-2 py-2 text-sm ${focus}`}
          >
            {options.map((value) => (
              <option key={value} value={value}>
                {DISPOSITIONS[value].label}
              </option>
            ))}
          </select>
          {relaxes && (
            <p className="mt-2 text-sm font-medium text-warn">
              Estás relajando lo que calculó el código: quedará marcado como «Override permisivo» en el resumen y en el
              reporte.
            </p>
          )}
        </div>
      ) : (
        <p className="text-sm font-medium">El archivo volverá a la disposición que calcula el código.</p>
      )}
      <label htmlFor={id} className="mt-4 block text-sm font-medium">
        Justificación (obligatoria)
      </label>
      <textarea
        id={id}
        value={justification}
        onChange={(event) => setJustification(event.target.value)}
        rows={3}
        disabled={saving}
        className={`mt-1 w-full border border-graphite bg-surface px-3 py-2 text-sm ${focus}`}
      />
      <p className={`mt-1 text-sm tabular-nums ${length >= MIN_JUSTIFICATION ? "text-load" : "text-graphite"}`}>
        {length}/{MIN_JUSTIFICATION} caracteres como mínimo
      </p>
      {error && (
        <p role="alert" className="mt-3 text-sm font-medium text-block">
          {error}
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={saving || length < MIN_JUSTIFICATION}
          className={`bg-stamp px-4 py-2 text-sm font-semibold text-white hover:bg-ink disabled:cursor-not-allowed disabled:bg-line disabled:text-graphite ${focus}`}
        >
          {mode === "set" ? "Guardar override" : "Retirar override"}
        </button>
        <button type="button" onClick={onCancel} disabled={saving} className={`px-4 py-2 text-sm font-semibold text-graphite hover:text-ink ${focus}`}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
