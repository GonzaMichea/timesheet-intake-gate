import { useEffect } from "react";

// Cada pantalla pone su propio título en la pestaña (R13.11)
export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · Timesheet Intake Gate`;
  }, [title]);
}
