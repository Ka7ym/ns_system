import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { Employees } from './pages/Employees';
import { EmployeeDetail } from './pages/EmployeeDetail';
import { NewEmployee } from './pages/NewEmployee';
import { Documents } from './pages/Documents';
import { ErrorLog } from './pages/ErrorLog';
import { Templates } from './pages/Templates';
import { AuditLog } from './pages/AuditLog';
import { Users } from './pages/Users';
import { Settings } from './pages/Settings';
import { Integration1C } from './pages/Integration1C';
import { Enbek } from './pages/Enbek';
import { References } from './pages/References';
import { Login } from './pages/Login';
import { Absences } from './pages/Absences';
import './App.css';

const LoginRoute: React.FC = () => {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-page">Загрузка...</div>;
  if (user) return <Navigate to="/" replace />;
  return <Login />;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginRoute />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<Layout />}>
                <Route element={<ProtectedRoute permission="dashboard.view" />}><Route index element={<Dashboard />} /></Route>
                <Route element={<ProtectedRoute permission="employees.view" />}>
                  <Route path="employees" element={<Employees />} />
                  <Route path="employees/:id" element={<EmployeeDetail />} />
                </Route>
                <Route element={<ProtectedRoute permission="employees.create" />}><Route path="new-employee" element={<NewEmployee />} /></Route>
                <Route element={<ProtectedRoute permission="documents.view" />}><Route path="documents" element={<Documents />} /></Route>
                <Route element={<ProtectedRoute permission="absences.view" />}><Route path="absences" element={<Absences />} /></Route>
                <Route element={<ProtectedRoute permission="templates.view" />}><Route path="templates" element={<Templates />} /></Route>
                <Route element={<ProtectedRoute permission="audit.view" />}><Route path="audit" element={<AuditLog />} /></Route>
                <Route element={<ProtectedRoute permission="enbek.view" />}><Route path="enbek" element={<Enbek />} /></Route>
                <Route element={<ProtectedRoute permission="users.manage" />}><Route path="users" element={<Users />} /></Route>
                <Route element={<ProtectedRoute permission="settings.manage" />}>
                  <Route path="settings" element={<Settings />} />
                  <Route path="onec" element={<Integration1C />} />
                </Route>
                <Route element={<ProtectedRoute permission="references.manage" />}><Route path="references" element={<References />} /></Route>
                <Route element={<ProtectedRoute permission="errors.view" />}><Route path="errors" element={<ErrorLog />} /></Route>
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;
