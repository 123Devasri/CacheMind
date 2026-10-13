import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AuthPage } from './pages/AuthPage';
import { UserPortal } from './pages/UserPortal';
import { AdminPortal } from './pages/AdminPortal';

// Route guard for authenticated users and role-based access control
const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  requiredRole?: 'ADMIN' | 'USER';
}> = ({ children, requiredRole }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-500 font-medium">Verifying authorization...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole === 'ADMIN' && user.role !== 'ADMIN') {
    return <Navigate to="/app" replace />;
  }

  return <>{children}</>;
};

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Authentication Route */}
          <Route path="/login" element={<AuthPage />} />

          {/* User Portal Route (Authenticated) */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <UserPortal />
              </ProtectedRoute>
            }
          />
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <UserPortal />
              </ProtectedRoute>
            }
          />

          {/* Admin Governance Portal Route (Strict ADMIN Role Required) */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute requiredRole="ADMIN">
                <AdminPortal />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/*"
            element={
              <ProtectedRoute requiredRole="ADMIN">
                <AdminPortal />
              </ProtectedRoute>
            }
          />

          {/* Legacy redirects */}
          <Route path="/playground" element={<Navigate to="/" replace />} />
          <Route path="/user" element={<Navigate to="/app" replace />} />
          <Route path="/cache" element={<Navigate to="/admin" replace />} />
          <Route path="/models" element={<Navigate to="/admin" replace />} />
          <Route path="/training" element={<Navigate to="/admin" replace />} />
          <Route path="/thresholds" element={<Navigate to="/admin" replace />} />
          <Route path="/clusters" element={<Navigate to="/admin" replace />} />
          <Route path="/logs" element={<Navigate to="/admin" replace />} />
          <Route path="/settings" element={<Navigate to="/admin" replace />} />

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
