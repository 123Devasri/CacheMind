import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { UserChat } from './pages/UserChat';
import { AdminPortal } from './pages/AdminPortal';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* User Route: Minimal ChatGPT-style interface */}
        <Route path="/" element={<UserChat />} />
        <Route path="/user" element={<UserChat />} />

        {/* Admin Route: Complete Governance & Policy Portal */}
        <Route path="/admin/*" element={<AdminPortal />} />

        {/* Legacy redirect to admin */}
        <Route path="/playground" element={<Navigate to="/" replace />} />
        <Route path="/cache" element={<Navigate to="/admin" replace />} />
        <Route path="/models" element={<Navigate to="/admin" replace />} />
        <Route path="/training" element={<Navigate to="/admin" replace />} />
        <Route path="/thresholds" element={<Navigate to="/admin" replace />} />
        <Route path="/clusters" element={<Navigate to="/admin" replace />} />
        <Route path="/logs" element={<Navigate to="/admin" replace />} />
        <Route path="/settings" element={<Navigate to="/admin" replace />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
