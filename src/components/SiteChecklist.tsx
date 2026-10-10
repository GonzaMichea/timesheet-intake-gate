import { CircleCheck, CircleDashed } from "lucide-react";
import { expectedFileName } from "../lib/format";

type Props = { sites: string[]; period: string; fileNames: string[] };

// Avisa antes de validar qué sedes ya tienen archivo. El motor decide después; esto es solo una guía
export default function SiteChecklist({ sites, period, fileNames }: Props) {
  const hasZip = fileNames.some((name) => /\.zip$/i.test(name));
  // El patrón del contrato distingue mayúsculas en el prefijo y no en la extensión
  const normalized = fileNames.map((name) => name.replace(/\.[^.]+$/, (ext) => ext.toLowerCase()));

  return (
    <ul className="grid grid-cols-1 border-t border-line sm:grid-cols-2" aria-label="Sedes esperadas">
      {sites.map((site) => {
        const base = expectedFileName(site, period);
        const received = normalized.some((name) => name === `${base}.csv` || name === `${base}.xlsx`);
        const Icon = received ? CircleCheck : CircleDashed;
        return (
          <li key={site} className="flex items-center gap-3 border-b border-line py-3 sm:odd:pr-4 sm:even:pl-4">
            <Icon size={18} aria-hidden="true" className={received ? "text-load" : "text-graphite"} />
            <span className="font-display text-lg font-bold">{site}</span>
            <span className="min-w-0 flex-1 truncate text-sm tabular-nums text-graphite">{base}.csv|.xlsx</span>
            <span className={`text-sm font-medium ${received ? "text-load" : "text-graphite"}`}>
              {received ? "Recibido" : hasZip ? "En el .zip" : "Falta"}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
