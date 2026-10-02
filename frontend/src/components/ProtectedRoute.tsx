import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute: React.FC<{ adminOnly?: boolean; permission?: string }> = ({ adminOnly, permission }) => {
  const { user, loading, isAdmin, hasPermission } = useAuth();
  if (loading) return <div className="loading-page">Загрузка...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />;
  if (permission && !hasPermission(permission)) {
    const fallback = [
      ['employees.view', '/employees'],
      ['documents.view', '/documents'],
      ['absences.view', '/absences'],
      ['users.manage', '/users'],
      ['dashboard.view', '/'],
    ].find(([required]) => hasPermission(required));
    if (!fallback) return <div className="loading-page">Для этой учётной записи нет доступных разделов.</div>;
    if (fallback[1] === window.location.pathname) return <div className="loading-page">Нет доступа к этому разделу.</div>;
    return <Navigate to={fallback[1]} replace />;
  }
  return <Outlet />;
};
