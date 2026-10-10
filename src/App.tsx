import { Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import BatchSummaryPage from "./pages/BatchSummaryPage";
import NewBatchPage from "./pages/NewBatchPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<NewBatchPage />} />
        <Route path="lotes/:batchId" element={<BatchSummaryPage />} />
        <Route path="*" element={<NewBatchPage />} />
      </Route>
    </Routes>
  );
}
