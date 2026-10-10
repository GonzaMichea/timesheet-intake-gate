import type { AiResult, ApiResult, AuditEntry, BatchListItem, BatchSummary, ContractInfo, Disposition, FileDetail, ReviewQueue } from "../types/api";

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

export function getFile(fileId: string) {
  return request<FileDetail>(`/files/${encodeURIComponent(fileId)}`);
}

export function createBatch(period: string, actor: string, files: File[]) {
  const form = new FormData();
  form.append("period", period);
  form.append("actor", actor);
  files.forEach((file) => form.append("files", file));
  return request<BatchSummary>("/batches", { method: "POST", body: form });
}

export function getReviewQueue(batchId: string) {
  return request<ReviewQueue>(`/batches/${encodeURIComponent(batchId)}/review`);
}

function post<T>(path: string, body: unknown) {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function acceptMapping(reviewId: string, actor: string, targetColumn: string) {
  return post<FileDetail>(`/mappings/${reviewId}/accept`, { actor, target_column: targetColumn });
}

export function rejectMapping(reviewId: string, actor: string) {
  return post<FileDetail>(`/mappings/${reviewId}/reject`, { actor });
}

export function createOverride(fileId: string, actor: string, disposition: Disposition, justification: string) {
  return post<FileDetail>(`/files/${fileId}/override`, { actor, disposition, justification });
}

export function withdrawOverride(fileId: string, actor: string, justification: string) {
  return post<FileDetail>(`/files/${fileId}/override/withdraw`, { actor, justification });
}

export function getBatches() {
  return request<BatchListItem[]>("/batches");
}

export function getAudit(batchId: string) {
  return request<AuditEntry[]>(`/batches/${encodeURIComponent(batchId)}/audit`);
}

export function generateAi(fileId: string, kind: AiResult["kind"]) {
  return request<AiResult>(`/files/${encodeURIComponent(fileId)}/ai/${kind}`, { method: "POST" });
}
