import { Ban, CircleCheck, ShieldAlert, TriangleAlert } from "lucide-react";
import type { Disposition } from "../types/api";

// El color nunca es el único indicador: cada disposición lleva texto e ícono (R13.2)
export const DISPOSITIONS: Record<
  Disposition,
  { label: string; Icon: typeof Ban; text: string; border: string }
> = {
  LOAD: {
    label: "Cargar",
    Icon: CircleCheck,
    text: "text-load",
    border: "border-load",
  },
  LOAD_WITH_WARNINGS: {
    label: "Cargar con advertencias",
    Icon: TriangleAlert,
    text: "text-warn",
    border: "border-warn",
  },
  QUARANTINE: {
    label: "Cuarentena",
    Icon: ShieldAlert,
    text: "text-quarantine",
    border: "border-quarantine",
  },
  BLOCK: {
    label: "Bloqueado",
    Icon: Ban,
    text: "text-block",
    border: "border-block",
  },
};

// Orden de restricción: un override que baja en este orden "relaja" la disposición calculada (R9.4)
export const RANK: Record<Disposition, number> = { LOAD: 0, LOAD_WITH_WARNINGS: 1, QUARANTINE: 2, BLOCK: 3 };
