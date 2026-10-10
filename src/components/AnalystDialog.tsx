import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAnalyst } from "../context/AnalystContext";

export default function AnalystDialog() {
  const { analyst, dialogOpen, closeDialog, saveAnalyst } = useAnalyst();
  const [name, setName] = useState(analyst);
  const inputRef = useRef<HTMLInputElement>(null);
  const canClose = analyst !== "";

  useEffect(() => {
    if (!dialogOpen) return;
    setName(analyst);
    inputRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && canClose) closeDialog();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dialogOpen, analyst, canClose, closeDialog]);

  if (!dialogOpen) return null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    saveAnalyst(name);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/60 p-4 sm:items-center">
      <form
        onSubmit={submit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="analyst-title"
        className="w-full max-w-md border border-line bg-surface p-6 sm:p-8"
      >
        <h2 id="analyst-title" className="font-display text-xl font-bold">
          ¿Quién valida este lote?
        </h2>
        <p className="mt-2 text-sm text-graphite">
          Tu nombre queda en la auditoría de cada decisión: mapeos aceptados y cambios de disposición. Se guarda solo
          en este navegador.
        </p>
        <label htmlFor="analyst-name" className="mt-6 block text-sm font-medium">
          Nombre del analista
        </label>
        <input
          ref={inputRef}
          id="analyst-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          autoComplete="name"
          maxLength={80}
          className="mt-1 w-full border border-graphite bg-surface px-3 py-2 text-base focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp"
        />
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          {canClose && (
            <button
              type="button"
              onClick={closeDialog}
              className="px-4 py-2 text-sm font-medium text-graphite hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp"
            >
              Cancelar
            </button>
          )}
          <button
            type="submit"
            disabled={name.trim() === ""}
            className="bg-stamp px-4 py-2 text-sm font-semibold text-white hover:bg-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp disabled:cursor-not-allowed disabled:bg-line disabled:text-graphite"
          >
            Guardar nombre
          </button>
        </div>
      </form>
    </div>
  );
}
