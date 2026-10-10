import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App.tsx";
import { AnalystProvider } from "./context/AnalystContext.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AnalystProvider>
        <App />
      </AnalystProvider>
    </BrowserRouter>
  </StrictMode>,
);
