import type { ApiResult, BatchSummary, ContractInfo } from "../types/api";

const NETWORK_ERROR = "No se pudo conectar con el servicio de validación. Revisa tu conexión e inténtalo de nuevo.";

// Único lugar que llama a fetch: cada función devuelve { data, error }
async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`/api${path}`, init);
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      // El backend responde { error: { code, message } } con el mensaje ya en español
      const message = body?.error?.message ?? `El servicio respondió con un error (${response.status}).`;
      return { data: null, error: message };
    }
    return { data: body as T, error: null };
  } catch {
    return { data: null, error: NETWORK_ERROR };
  }
}

export function getContract() {
  return request<ContractInfo>("/contract");
}

export function getBatch(batchId: string) {
  return request<BatchSummary>(`/batches/${encodeURIComponent(batchId)}`);
}

export function createBatch(period: string, actor: string, files: File[]) {
  const form = new FormData();
  form.append("period", period);
  form.append("actor", actor);
  files.forEach((file) => form.append("files", file));
  return request<BatchSummary>("/batches", { method: "POST", body: form });
}
