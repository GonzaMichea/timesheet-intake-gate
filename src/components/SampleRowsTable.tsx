// Hasta 5 filas reales del archivo, con su número de fila tal como se ve en Excel
export default function SampleRowsTable({ rows, highlight }: { rows: Record<string, unknown>[]; highlight: string | null }) {
  if (rows.length === 0) return null;
  const columns = Object.keys(rows[0]).filter((key) => key !== "row");

  return (
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Filas de ejemplo">
      <table className="min-w-full border-collapse text-left text-sm tabular-nums">
        <thead>
          <tr className="border-b border-ink">
            <th scope="col" className="py-1.5 pr-4 font-semibold">Fila</th>
            {columns.map((column) => (
              <th key={column} scope="col" className={`whitespace-nowrap py-1.5 pr-4 font-semibold ${column === highlight ? "text-block" : ""}`}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row.row)} className="border-b border-line">
              <th scope="row" className="py-1.5 pr-4 font-semibold">{String(row.row)}</th>
              {columns.map((column) => (
                <td key={column} className={`whitespace-nowrap py-1.5 pr-4 ${column === highlight ? "font-semibold text-block" : ""}`}>
                  {String(row[column] ?? "") || <span className="text-graphite">(vacío)</span>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
