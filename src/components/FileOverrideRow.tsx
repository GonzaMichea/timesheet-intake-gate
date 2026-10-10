import { useState } from "react";
import { DISPOSITIONS } from "../lib/disposition";
import type { Disposition, FileSummary } from "../types/api";
import DispositionSeal from "./DispositionSeal";
import OverrideForm from "./OverrideForm";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

type Props = {
  file: FileSummary;
  onChange: (file: FileSummary, disposition: Disposition | null, justification: string) => Promise<string | null>;
};

export default function FileOverrideRow({ file, onChange }: Props) {
  const [mode, setMode] = useState<"set" | "withdraw" | null>(null);
  const computed = DISPOSITIONS[file.computed_disposition];

  return (
    <li className="border-b border-line py-6">
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h3 className="font-display text-lg font-bold">{file.site ?? file.filename}</h3>
          <p className="mt-1 text-sm text-graphite">
            Calculada por el código:{" "}
            <span className={`font-semibold ${computed.text}`}>{computed.label}</span>
          </p>
        </div>
        <DispositionSeal entry={file} />
      </div>

      {mode === null ? (
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setMode("set")}
            className={`border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper ${focus}`}
          >
            Cambiar disposición
          </button>
          {file.override_active && (
            <button type="button" onClick={() => setMode("withdraw")} className={`px-4 py-2 text-sm font-semibold underline underline-offset-4 ${focus}`}>
              Retirar override
            </button>
          )}
        </div>
      ) : (
        <OverrideForm
          file={file}
          mode={mode}
          onCancel={() => setMode(null)}
          onSubmit={async (disposition, justification) => {
            const error = await onChange(file, disposition, justification);
            if (!error) setMode(null);
            return error;
          }}
        />
      )}
    </li>
  );
}
