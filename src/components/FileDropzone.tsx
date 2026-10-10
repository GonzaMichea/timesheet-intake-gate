import { FileSpreadsheet, FileText, FolderArchive, Upload, X } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";
import { formatBytes } from "../lib/format";

const ACCEPTED = /\.(csv|xlsx|zip)$/i;
const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

type Props = {
  files: File[];
  disabled: boolean;
  onAdd: (files: File[]) => void;
  onRemove: (index: number) => void;
};

function FileIcon({ name }: { name: string }) {
  if (/\.zip$/i.test(name)) return <FolderArchive size={18} aria-hidden="true" />;
  if (/\.xlsx$/i.test(name)) return <FileSpreadsheet size={18} aria-hidden="true" />;
  return <FileText size={18} aria-hidden="true" />;
}

export default function FileDropzone({ files, disabled, onAdd, onRemove }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [rejected, setRejected] = useState<string[]>([]);

  const receive = (incoming: File[]) => {
    setRejected(incoming.filter((f) => !ACCEPTED.test(f.name)).map((f) => f.name));
    onAdd(incoming.filter((f) => ACCEPTED.test(f.name)));
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    if (!disabled) receive(Array.from(event.dataTransfer.files));
  };

  return (
    <div>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-start gap-3 border-2 border-dashed p-6 sm:flex-row sm:items-center sm:justify-between ${
          dragging ? "border-stamp bg-stamp/5" : "border-graphite bg-surface"
        }`}
      >
        <div>
          <p className="font-medium">Arrastra aquí los archivos de las sedes</p>
          <p className="mt-1 text-sm text-graphite">Acepta .csv, .xlsx o un .zip con todos los archivos del mes.</p>
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className={`inline-flex shrink-0 items-center gap-2 border border-ink px-4 py-2 text-sm font-semibold hover:bg-ink hover:text-paper disabled:cursor-not-allowed disabled:border-line disabled:text-graphite disabled:hover:bg-transparent ${focus}`}
        >
          <Upload size={16} aria-hidden="true" />
          Elegir archivos
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".csv,.xlsx,.zip"
          className="sr-only"
          tabIndex={-1}
          onChange={(event) => {
            receive(Array.from(event.target.files ?? []));
            event.target.value = "";
          }}
        />
      </div>

      {rejected.length > 0 && (
        <p role="alert" className="mt-3 text-sm font-medium text-block">
          No se agregó {rejected.join(", ")}: solo se aceptan archivos .csv, .xlsx o .zip.
        </p>
      )}

      {files.length > 0 && (
        <ul className="mt-4 divide-y divide-line border-y border-line" aria-label="Archivos seleccionados">
          {files.map((file, index) => (
            <li key={`${file.name}-${file.size}`} className="flex items-center gap-3 py-2">
              <FileIcon name={file.name} />
              <span className="min-w-0 flex-1 truncate text-sm font-medium tabular-nums">{file.name}</span>
              <span className="text-sm tabular-nums text-graphite">{formatBytes(file.size)}</span>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onRemove(index)}
                aria-label={`Quitar ${file.name}`}
                className={`p-1 text-graphite hover:text-block disabled:cursor-not-allowed disabled:opacity-40 ${focus}`}
              >
                <X size={18} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
