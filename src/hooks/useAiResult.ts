import { useCallback, useEffect, useRef, useState } from "react";
import { generateAi } from "../services/api";
import type { AiResult } from "../types/api";

// Pide la asistencia de IA solo si todavía no existe un resultado guardado; los hallazgos ya se muestran sin esperarla (R11.2)
export function useAiResult(fileId: string, kind: AiResult["kind"], stored: AiResult | undefined, enabled: boolean) {
  const [result, setResult] = useState<AiResult | undefined>(stored);
  const [loading, setLoading] = useState(false);
  const requested = useRef(false);

  const request = useCallback(async () => {
    setLoading(true);
    const { data } = await generateAi(fileId, kind);
    setLoading(false);
    // Si ni siquiera hubo respuesta del servicio, la sección queda como "No disponible"
    setResult(data ?? undefined);
  }, [fileId, kind]);

  useEffect(() => {
    if (enabled && !stored && !requested.current) {
      requested.current = true;
      request();
    }
  }, [enabled, stored, request]);

  return { result, loading, retry: request };
}
