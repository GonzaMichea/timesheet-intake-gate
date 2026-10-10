// Elemento firma: la cinta de filas. Cada segmento toma el color de la peor severidad de esa fila,
// así se ve de un vistazo si los problemas están concentrados (exportación rota) o dispersos (digitación).
const COLORS: Record<string, string> = {
  B: "bg-block",
  E: "bg-quarantine",
  W: "bg-warn",
  ".": "bg-line",
};

type Run = { char: string; length: number };

function toRuns(ribbon: string): Run[] {
  const runs: Run[] = [];
  for (const char of ribbon) {
    const last = runs[runs.length - 1];
    if (last && last.char === char) last.length += 1;
    else runs.push({ char, length: 1 });
  }
  return runs;
}

function describe(ribbon: string): string {
  const count = (c: string) => [...ribbon].filter((x) => x === c).length;
  const parts = [
    [count("B"), "con hallazgos bloqueantes"],
    [count("E"), "con errores"],
    [count("W"), "con advertencias"],
  ].filter(([n]) => n !== 0);
  const detail = parts.length ? parts.map(([n, text]) => `${n} ${text}`).join(", ") : "ninguna con hallazgos";
  return `Cinta de ${ribbon.length} filas: ${detail}.`;
}

// Fila marcada más cercana al punto donde se hizo clic (con tolerancia de unos 8 px)
function nearestFlagged(ribbon: string, clickX: number, width: number): number | null {
  const center = Math.min(ribbon.length - 1, Math.max(0, Math.floor((clickX / width) * ribbon.length)));
  const reach = Math.ceil(8 / (width / ribbon.length));
  for (let distance = 0; distance <= reach; distance++) {
    for (const index of [center - distance, center + distance]) {
      if (index >= 0 && index < ribbon.length && ribbon[index] !== ".") return index;
    }
  }
  return null;
}

type Props = { ribbon: string; onPick?: (row: number) => void };

export default function RowRibbon({ ribbon, onPick }: Props) {
  if (ribbon === "") {
    return (
      <div className="flex items-center gap-3">
        <div className="h-3 flex-1 border border-dashed border-graphite" aria-hidden="true" />
        <span className="text-sm text-graphite">Sin filas que revisar</span>
      </div>
    );
  }
  return (
    <div
      role="img"
      aria-label={describe(ribbon)}
      onClick={(event) => {
        if (!onPick) return;
        const box = event.currentTarget.getBoundingClientRect();
        const index = nearestFlagged(ribbon, event.clientX - box.left, box.width);
        if (index !== null) onPick(index + 2);
      }}
      className={`flex h-3 w-full animate-ribbon motion-reduce:animate-none ${onPick ? "cursor-pointer" : ""}`}
    >
      {toRuns(ribbon).map((run, index) => (
        <span
          key={index}
          className={COLORS[run.char]}
          // Las filas con hallazgos tienen un ancho mínimo para que una sola fila siga siendo visible
          style={{ flexGrow: run.length, flexBasis: 0, minWidth: run.char === "." ? 0 : 3 }}
        />
      ))}
    </div>
  );
}
