import type { ApiResult, Health } from "../types/api";

const NETWORK_ERROR = "No se pudo conectar con el servicio de validación.";

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`/api${path}`, init);
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      // El backend responde { error: { code, message } } con el mensaje ya en español
      const message = body?.error?.message ?? `El servicio respondió con error ${response.status}.`;
      return { data: null, error: message };
    }
    return { data: body as T, error: null };
  } catch {
    return { data: null, error: NETWORK_ERROR };
  }
}

export function getHealth() {
  return request<Health>("/health");
}
