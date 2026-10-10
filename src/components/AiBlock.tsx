import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import type { AiResult } from "../types/api";

type Props = {
  title: string;
  hint: string;
  result: AiResult | undefined;
  loading: boolean;
  onRetry: () => void;
  children: (payload: Record<string, unknown>) => ReactNode;
};

export function ReviewBadge() {
  return (
    <span className="inline-flex items-center gap-1 text-sm font-semibold text-warn">
      <TriangleAlert size={14} aria-hidden="true" />
      Requiere revisión humana
    </span>
  );
}

// Un bloque de IA: siempre rotulado como no vinculante y con "No disponible" cuando la IA no responde (R11.9, R12.1)
export default function AiBlock({ title, hint, result, loading, onRetry, children }: Props) {
  return (
    <div>
      <h3 className="font-semibold">
        {title} <span className="ml-1 text-sm font-medium text-graphite">IA – no vinculante</span>
      </h3>
      <p className="mt-1 text-sm text-graphite">{hint}</p>
      <div className="mt-4" aria-live="polite">
        {loading ? (
          <p role="status" className="text-sm text-graphite">Generando…</p>
        ) : result?.status === "ok" && result.payload ? (
          children(result.payload)
        ) : (
          <div>
            <p className="text-sm font-medium">No disponible</p>
            <p className="text-sm text-graphite">
              {result?.reason ?? "No se pudo contactar con el servicio de validación."}
            </p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 text-sm font-semibold underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp"
            >
              Reintentar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
