import { FilePlus2, History, UserRound } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAnalyst } from "../context/AnalystContext";
import AnalystDialog from "./AnalystDialog";

const focus =
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stamp";

export default function AppShell() {
  const { analyst, openDialog } = useAnalyst();

  return (
    <div className="min-h-screen">
      <header className="border-b border-ink bg-ink text-paper">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-8">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-1">
            <NavLink to="/" className={`font-display text-base font-extrabold tracking-wide ${focus} focus-visible:outline-paper`}>
              Timesheet Intake Gate
            </NavLink>
            <nav aria-label="Principal" className="flex gap-6">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 border-b-2 py-1 text-sm font-medium ${focus} focus-visible:outline-paper ${
                    isActive ? "border-paper" : "border-transparent text-paper/80 hover:text-paper"
                  }`
                }
              >
                <FilePlus2 size={16} aria-hidden="true" />
                Nuevo lote
              </NavLink>
              <NavLink
                to="/lotes"
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 border-b-2 py-1 text-sm font-medium ${focus} focus-visible:outline-paper ${
                    isActive ? "border-paper" : "border-transparent text-paper/80 hover:text-paper"
                  }`
                }
              >
                <History size={16} aria-hidden="true" />
                Historial
              </NavLink>
            </nav>
          </div>
          <button
            type="button"
            onClick={openDialog}
            className={`inline-flex items-center gap-2 py-1 text-sm text-paper/80 hover:text-paper ${focus} focus-visible:outline-paper`}
            aria-label={analyst ? `Analista: ${analyst}. Cambiar nombre` : "Ingresar nombre del analista"}
          >
            <UserRound size={16} aria-hidden="true" />
            <span>{analyst || "Ingresa tu nombre"}</span>
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-8 sm:py-14">
        <Outlet />
      </main>
      <AnalystDialog />
    </div>
  );
}
