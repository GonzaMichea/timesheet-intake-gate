import { Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import AuditPage from "./pages/AuditPage";
import BatchSummaryPage from "./pages/BatchSummaryPage";
import FileDetailPage from "./pages/FileDetailPage";
import HistoryPage from "./pages/HistoryPage";
import MetricsPage from "./pages/MetricsPage";
import NewBatchPage from "./pages/NewBatchPage";
import ReviewPage from "./pages/ReviewPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<NewBatchPage />} />
        <Route path="metricas" element={<MetricsPage />} />
        <Route path="lotes" element={<HistoryPage />} />
        <Route path="lotes/:batchId" element={<BatchSummaryPage />} />
        <Route path="lotes/:batchId/revision" element={<ReviewPage />} />
        <Route path="lotes/:batchId/auditoria" element={<AuditPage />} />
        <Route path="lotes/:batchId/archivos/:fileId" element={<FileDetailPage />} />
        <Route path="*" element={<NewBatchPage />} />
      </Route>
    </Routes>
  );
}
