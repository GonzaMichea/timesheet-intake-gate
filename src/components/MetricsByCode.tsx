import { formatPct } from "../lib/format";
import type { Evaluation } from "../types/api";

type Props = { byCode: Evaluation["summary"]["by_code"]; descriptions: Record<string, string> };

// Detección por tipo de defecto: la barra es solo apoyo visual, el número y el texto llevan la información
export default function MetricsByCode({ byCode, descriptions }: Props) {
  return (
    <div className="overflow-x-auto" role="region" aria-label="Detección por tipo de defecto" tabIndex={0}>
      <table className="w-full min-w-[560px] border-collapse text-left text-sm tabular-nums">
        <thead>
          <tr className="border-b border-ink">
            <th scope="col" className="py-2 pr-4 font-semibold">Defecto</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Sembrados</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Detectados</th>
            <th scope="col" className="w-40 py-2 pr-4 font-semibold">Detección</th>
            <th scope="col" className="py-2 text-right font-semibold">Falsos positivos</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(byCode).map(([code, c]) => {
            const rate = c.expected ? c.detected / c.expected : null;
            return (
              <tr key={code} className="border-b border-line">
                <th scope="row" className="py-2 pr-4 font-normal">
                  <span className="font-semibold">{code}</span> <span className="text-graphite">{descriptions[code] ?? ""}</span>
                </th>
                <td className="py-2 pr-4 text-right">{c.expected}</td>
                <td className="py-2 pr-4 text-right">{c.detected}</td>
                <td className="py-2 pr-4">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-20 bg-line" aria-hidden="true">
                      <span className="block h-2 bg-load" style={{ width: `${(rate ?? 0) * 100}%` }} />
                    </span>
                    {formatPct(rate)}
                  </span>
                </td>
                <td className="py-2 text-right">{c.false_positives}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
