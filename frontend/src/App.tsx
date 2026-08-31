import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { AuditPage } from "./pages/AuditPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DatasetsPage } from "./pages/DatasetsPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { WorkflowPage } from "./pages/WorkflowPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/workflow" element={<WorkflowPage />} />
        <Route path="/datasets" element={<DatasetsPage />} />
        <Route path="/review" element={<ReviewQueuePage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
