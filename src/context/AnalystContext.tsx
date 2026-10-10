import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

const STORAGE_KEY = "tig.analyst";

type AnalystContextValue = {
  analyst: string;
  dialogOpen: boolean;
  openDialog: () => void;
  closeDialog: () => void;
  saveAnalyst: (name: string) => void;
};

const AnalystContext = createContext<AnalystContextValue | null>(null);

// localStorage puede fallar (ventana privada, datos bloqueados): la app sigue funcionando sin él
function readStored(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

// MIENTRAS no exista autenticación, el nombre del analista se pide una vez (R10.3)
export function AnalystProvider({ children }: { children: ReactNode }) {
  const [analyst, setAnalyst] = useState(readStored);
  const [dialogOpen, setDialogOpen] = useState(() => readStored() === "");

  const saveAnalyst = useCallback((name: string) => {
    const clean = name.trim();
    if (!clean) return;
    setAnalyst(clean);
    setDialogOpen(false);
    try {
      localStorage.setItem(STORAGE_KEY, clean);
    } catch {
      // sin almacenamiento: el nombre dura solo mientras la pestaña esté abierta
    }
  }, []);

  const value = useMemo(
    () => ({
      analyst,
      dialogOpen,
      openDialog: () => setDialogOpen(true),
      closeDialog: () => setDialogOpen(false),
      saveAnalyst,
    }),
    [analyst, dialogOpen, saveAnalyst],
  );

  return <AnalystContext.Provider value={value}>{children}</AnalystContext.Provider>;
}

export function useAnalyst() {
  const context = useContext(AnalystContext);
  if (!context) throw new Error("useAnalyst debe usarse dentro de AnalystProvider");
  return context;
}
