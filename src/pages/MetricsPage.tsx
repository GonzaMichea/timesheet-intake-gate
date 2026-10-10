import { useCallback, useEffect, useState } from "react";
import MetricsByCode from "../components/MetricsByCode";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatPct } from "../lib/format";
import { getContract, getMetrics } from "../services/api";
import type { Evaluation } from "../types/api";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

export default function MetricsPage() {
  useDocumentTitle("Métricas");
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [descriptions, setDescriptions] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const [metrics, contract] = await Promise.all([getMetrics(), getContract()]);
    setEvaluation(metrics.data);
    setError(metrics.error);
    if (contract.data) setDescriptions(contract.data.code_descriptions);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return (
      <div className="max-w-xl border-l-4 border-ink bg-surface p-6">
        <h1 className="font-display text-xl font-bold">Métricas</h1>
        <p className="mt-3" role="alert">{error}</p>
        <button type="button" onClick={load} className={`mt-4 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}>
          Reintentar conexión
        </button>
      </div>
    );
  }
  if (!evaluation) return <p role="status" className="text-graphite">Cargando las métricas…</p>;

  const { summary } = evaluation;
  const ai = summary.ai;
  const headline = [
    { label: "Detección global", value: formatPct(summary.detection), note: `${summary.units.detected} de ${summary.units.expected} defectos sembrados` },
    { label: "Falsos positivos", value: formatPct(summary.false_positive_rate), note: "hallazgos que no estaban sembrados" },
    { label: "Exactitud de disposición", value: formatPct(summary.disposition_accuracy), note: `${summary.wrong_dispositions} disposiciones incorrectas` },
    { label: "Candidatas D05 correctas", value: formatPct(summary.d05_precision), note: "columnas renombradas bien identificadas" },
    { label: "Mapeos sugeridos por IA", value: ai ? formatPct(ai.precision) : "N/A", note: ai ? `${ai.correct} de ${ai.suggestions} sugerencias` : "se mide con evaluate.py --with-ai" },
  ];

  return (
    <div>
      <p className="text-sm font-medium uppercase tracking-widest text-graphite">Evaluación sobre lotes sintéticos</p>
      <h1 className="mt-2 font-display text-2xl font-extrabold">Métricas</h1>
      <p className="mt-3 max-w-2xl text-graphite">
        El motor se mide contra el ground truth: lo que se sembró a propósito en cada lote. Ejecutado el{" "}
        {new Date(evaluation.generated_at).toLocaleString("es-CL", { dateStyle: "long", timeStyle: "short" })}.
      </p>

      <dl className="mt-10 grid gap-x-10 gap-y-6 border-y border-line py-6 sm:grid-cols-2 lg:grid-cols-5">
        {headline.map((item) => (
          <div key={item.label}>
            <dt className="text-sm text-graphite">{item.label}</dt>
            <dd className="mt-1 font-display text-xl font-bold tabular-nums">{item.value}</dd>
            <dd className="mt-1 text-sm text-graphite">{item.note}</dd>
          </div>
        ))}
      </dl>

      <section aria-labelledby="by-code" className="mt-12">
        <h2 id="by-code" className="border-b border-ink pb-2 font-display text-lg font-bold">Detección por tipo de defecto</h2>
        <div className="mt-4"><MetricsByCode byCode={summary.by_code} descriptions={descriptions} /></div>
      </section>

      <section aria-labelledby="timing" className="mt-12">
        <h2 id="timing" className="border-b border-ink pb-2 font-display text-lg font-bold">Tiempo por lote</h2>
        <ul className="mt-2">
          {evaluation.batches.map((b) => (
            <li key={b.batch} className="flex flex-wrap justify-between gap-2 border-b border-line py-2 text-sm tabular-nums">
              <span>{b.batch}</span>
              <span className="text-graphite">{b.files} archivos · {b.ms} ms</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="repro" className="mt-12">
        <h2 id="repro" className="border-b border-ink pb-2 font-display text-lg font-bold">Cómo reproducirlo</h2>
        <p className="mt-3 text-sm text-graphite">Con la misma semilla (42) los lotes salen idénticos, así que el resultado se puede repetir:</p>
        <pre className="mt-2 overflow-x-auto bg-ink p-4 text-sm text-paper"><code>python scripts/generate_dataset.py{"\n"}python scripts/evaluate.py</code></pre>
      </section>
    </div>
  );
}
