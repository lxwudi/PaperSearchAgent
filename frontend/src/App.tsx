import type { ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from './components/Layout';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { WorkspaceProvider } from './contexts/WorkspaceContext';
import { AuthPage } from './pages/AuthPage';
import { ExportsPage } from './pages/ExportsPage';
import { FavoritesPage } from './pages/FavoritesPage';
import { HistoryPage } from './pages/HistoryPage';
import { TeamPage } from './pages/TeamPage';
import { WorkspacePage } from './pages/WorkspacePage';

function RequireAuth({ children }: { children: ReactNode }) {
  const { tokens, loading } = useAuth();
  if (loading) {
    return <div className="empty">加载中...</div>;
  }
  if (!tokens?.accessToken) {
    return <Navigate to="/auth" replace />;
  }
  return <>{children}</>;
}

export function App() {
  return (
    <AuthProvider>
      <WorkspaceProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route
              path="/*"
              element={
                <RequireAuth>
                  <AppLayout>
                    <Routes>
                      <Route path="/workspace" element={<WorkspacePage />} />
                      <Route path="/history" element={<HistoryPage />} />
                      <Route path="/favorites" element={<FavoritesPage />} />
                      <Route path="/exports" element={<ExportsPage />} />
                      <Route path="/team" element={<TeamPage />} />
                      <Route path="*" element={<Navigate to="/workspace" replace />} />
                    </Routes>
                  </AppLayout>
                </RequireAuth>
              }
            />
          </Routes>
        </BrowserRouter>
      </WorkspaceProvider>
    </AuthProvider>
  );
}

