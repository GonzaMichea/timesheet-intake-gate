import { DISPOSITIONS } from "../lib/disposition";
import type { Disposition } from "../types/api";

const ORDER: Disposition[] = ["LOAD", "LOAD_WITH_WARNINGS", "QUARANTINE", "BLOCK"];

type Props = { quarantinePct: number | null };

export default function DispositionLegend({ quarantinePct }: Props) {
  const threshold = quarantinePct === null ? "el umbral" : `${String(quarantinePct * 100).replace(".", ",")} %`;
  const hints: Record<Disposition, string> = {
    LOAD: "Sin hallazgos.",
    LOAD_WITH_WARNINGS: `Solo advertencias, o errores en ${threshold} de las filas o menos.`,
    QUARANTINE: `Errores en más de ${threshold} de las filas.`,
    BLOCK: "Hay un hallazgo bloqueante: falta una sede o una columna de horas ilegible.",
  };

  return (
    <aside aria-labelledby="legend-title">
      <h2 id="legend-title" className="font-display text-lg font-bold">
        Qué recibe cada archivo
      </h2>
      <p className="mt-2 text-sm text-graphite">
        Al validar, cada sede queda con una de estas decisiones. La calcula el código con las reglas del contrato; la
        IA nunca decide.
      </p>
      <ol className="mt-6 space-y-5">
        {ORDER.map((value, index) => {
          const { label, Icon, text } = DISPOSITIONS[value];
          return (
            <li key={value} className="flex gap-3">
              <span className="w-4 pt-0.5 text-sm tabular-nums text-graphite">{index + 1}</span>
              <div>
                <p className={`inline-flex items-center gap-2 font-semibold ${text}`}>
                  <Icon size={18} aria-hidden="true" />
                  {label}
                </p>
                <p className="mt-1 text-sm text-graphite">{hints[value]}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
