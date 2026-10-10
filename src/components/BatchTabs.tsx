import { NavLink } from "react-router-dom";

type Props = { batchId: string; pendingReviews?: number };

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

// Navegación entre las vistas de un mismo lote
export default function BatchTabs({ batchId, pendingReviews }: Props) {
  const tab = ({ isActive }: { isActive: boolean }) =>
    `inline-flex items-center gap-2 border-b-2 px-1 py-2 text-sm font-semibold ${focus} ${
      isActive ? "border-ink" : "border-transparent text-graphite hover:text-ink"
    }`;

  return (
    <nav aria-label="Vistas del lote" className="mb-8 flex gap-6 border-b border-line">
      <NavLink to={`/lotes/${batchId}`} end className={tab}>
        Resumen
      </NavLink>
      <NavLink to={`/lotes/${batchId}/revision`} className={tab}>
        Revisión
        {pendingReviews ? (
          <span className="bg-ink px-1.5 text-xs tabular-nums text-paper" aria-label={`${pendingReviews} pendientes`}>
            {pendingReviews}
          </span>
        ) : null}
      </NavLink>
      <NavLink to={`/lotes/${batchId}/auditoria`} className={tab}>
        Auditoría
      </NavLink>
    </nav>
  );
}
