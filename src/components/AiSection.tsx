import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { useAiResult } from "../hooks/useAiResult";
import type { AiRemediation, AiStatement, FileDetail } from "../types/api";
import AiBlock, { ReviewBadge } from "./AiBlock";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

function Refs({ refs }: { refs: string[] }) {
  return refs.length ? (
    <span className="text-sm tabular-nums text-graphite"> Respaldo: {refs.join(", ")}</span>
  ) : (
    <span className="text-sm font-medium text-warn"> Sin respaldo en hallazgos</span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
  };
  return (
    <div className="mt-3 flex items-center gap-3">
      <button type="button" onClick={copy} className={`inline-flex items-center gap-2 border border-ink px-3 py-1.5 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}>
        {state === "copied" ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
        Copiar mensaje
      </button>
      <span role="status" className="text-sm text-graphite">
        {state === "copied" && "Copiado. Revísalo antes de enviarlo: la app no envía nada."}
        {state === "failed" && "No se pudo copiar. Selecciona el texto y cópialo a mano."}
      </span>
    </div>
  );
}

export default function AiSection({ file }: { file: FileDetail }) {
  // La IA solo explica hallazgos: sin hallazgos abiertos no hay nada que pedirle
  const enabled = file.kind === "site_file" && file.defects.length > 0;
  const cause = useAiResult(file.id, "cause", file.ai.cause, enabled);
  const remediation = useAiResult(file.id, "remediation", file.ai.remediation, enabled);

  return (
    <section aria-labelledby="ai-title" className="mt-14">
      <h2 id="ai-title" className="border-b border-ink pb-2 font-display text-lg font-bold">
        Asistencia de IA
      </h2>
      {!enabled ? (
        <p className="mt-4 text-sm text-graphite">No hay hallazgos que explicar en este archivo.</p>
      ) : (
        <div className="mt-4 grid gap-x-12 gap-y-8 md:grid-cols-2">
          <AiBlock title="Causa probable" hint="Qué pudo pasar en la sede, con los hallazgos que lo respaldan." {...cause}
            onRetry={cause.retry}>
            {(payload) => (
              <ul className="space-y-3">
                {(payload.statements as AiStatement[]).map((s) => (
                  <li key={s.text} className="text-sm">
                    {s.text}
                    <Refs refs={s.finding_refs} />
                    {s.needs_review && <p className="mt-1"><ReviewBadge /></p>}
                  </li>
                ))}
              </ul>
            )}
          </AiBlock>
          <AiBlock title="Borrador de mensaje a la sede" hint="Texto en español con los hallazgos concretos. No se envía solo." {...remediation}
            onRetry={remediation.retry}>
            {(payload) => {
              const draft = payload as unknown as AiRemediation;
              const text = `Asunto: ${draft.subject}\n\n${draft.body}`;
              return (
                <div>
                  {draft.needs_review && <p className="mb-2"><ReviewBadge /></p>}
                  <p className="text-sm font-semibold">{draft.subject}</p>
                  <p className="mt-2 whitespace-pre-wrap border-l-2 border-graphite pl-3 text-sm">{draft.body}</p>
                  <Refs refs={draft.finding_refs} />
                  <CopyButton text={text} />
                </div>
              );
            }}
          </AiBlock>
        </div>
      )}
    </section>
  );
}
