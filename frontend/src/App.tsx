import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { OverviewDashboard } from './pages/OverviewDashboard';
import { QueryPlayground } from './pages/QueryPlayground';
import { CacheExplorer } from './pages/CacheExplorer';
import { MLModels } from './pages/MLModels';
import { DatasetTraining } from './pages/DatasetTraining';
import { ThresholdSafety } from './pages/ThresholdSafety';
import { QueryClusters } from './pages/QueryClusters';
import { AuditLogs } from './pages/AuditLogs';
import { Settings } from './pages/Settings';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<OverviewDashboard />} />
          <Route path="playground" element={<QueryPlayground />} />
          <Route path="cache" element={<CacheExplorer />} />
          <Route path="models" element={<MLModels />} />
          <Route path="training" element={<DatasetTraining />} />
          <Route path="thresholds" element={<ThresholdSafety />} />
          <Route path="clusters" element={<QueryClusters />} />
          <Route path="logs" element={<AuditLogs />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
