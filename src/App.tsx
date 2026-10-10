import { useCallback, useEffect, useState } from "react";
import { getHealth } from "./services/api";
import type { Health } from "./types/api";

// Pantalla temporal del incremento 0: confirma que frontend y API conversan en Vercel
export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const check = useCallback(async () => {
    setLoading(true);
    const { data, error } = await getHealth();
    setHealth(data);
    setError(error);
    setLoading(false);
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  return (
    <main className="mx-auto max-w-3xl px-4 py-16 sm:px-8">
      <p className="text-sm font-medium uppercase tracking-widest text-graphite">Incremento 0 · base verificada</p>
      <h1 className="mt-2 font-display text-2xl font-extrabold sm:text-display">Timesheet Intake Gate</h1>
      <p className="mt-4 max-w-xl text-lg text-graphite">
        Valida las hojas de tiempo de SCL, VAP, CCP y ANF antes de cargarlas a nómina.
      </p>

      <section className="mt-12 border-t border-line pt-8" aria-live="polite">
        <h2 className="font-display text-lg font-bold">Estado del servicio de validación</h2>
        {loading && <p className="mt-4 text-graphite">Consultando el servicio…</p>}
        {!loading && error && (
          <div className="mt-4">
            <p className="font-medium text-block">{error}</p>
            <button
              type="button"
              onClick={check}
              className="mt-4 rounded border border-ink px-4 py-2 text-sm font-medium hover:bg-ink hover:text-paper focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp"
            >
              Reintentar conexión
            </button>
          </div>
        )}
        {!loading && health && (
          <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm tabular-nums sm:max-w-sm">
            <dt className="text-graphite">Estado</dt>
            <dd className="font-medium text-load">{health.status}</dd>
            <dt className="text-graphite">Python</dt>
            <dd>{health.python}</dd>
            <dt className="text-graphite">pandas</dt>
            <dd>{health.pandas}</dd>
            <dt className="text-graphite">openpyxl</dt>
            <dd>{health.openpyxl}</dd>
          </dl>
        )}
      </section>
    </main>
  );
}
