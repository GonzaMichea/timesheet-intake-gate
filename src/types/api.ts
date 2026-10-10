// Espejo manual de los modelos pydantic del backend (design D-12)

export type Health = {
  status: string;
  db: "ok" | "no_configurada" | "error";
  python: string;
  pandas: string;
  openpyxl: string;
};

export type ApiResult<T> =
  | { data: T; error: null }
  | { data: null; error: string };
