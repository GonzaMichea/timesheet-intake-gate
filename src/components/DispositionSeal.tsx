import { DISPOSITIONS } from "../lib/disposition";
import type { FileSummary } from "../types/api";

// Sello de disposición: color + ícono + texto, nunca solo color (R13.2)
export default function DispositionSeal({ entry }: { entry: FileSummary }) {
  const final = DISPOSITIONS[entry.final_disposition];
  const computed = DISPOSITIONS[entry.computed_disposition];

  return (
    <div className="flex flex-col items-start sm:items-end">
      <p
        className={`inline-flex items-center gap-2 border-2 px-3 py-1 font-display text-sm font-bold uppercase tracking-wide ${final.text} ${final.border}`}
      >
        <final.Icon size={16} aria-hidden="true" />
        {final.label}
      </p>
      {entry.override_active && (
        <p className="mt-2 text-sm text-graphite sm:text-right">
          <span className="font-semibold text-ink">
            {entry.permissive_override ? "Override permisivo" : "Override"}
          </span>
          {" · el código calculó "}
          <span className={`font-semibold ${computed.text}`}>{computed.label}</span>
        </p>
      )}
      {entry.calculated_changed_after_override && (
        <p className="mt-1 text-sm font-medium text-warn">La disposición calculada cambió después del override</p>
      )}
    </div>
  );
}
