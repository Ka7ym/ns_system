import { Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { Layout } from './components/Layout';

export const ProtectedLayout: React.FC = () => {
  const { user, loading } = useAuth();
  if (loading) return <div className="boot-screen">Загрузка NS SYSTEM…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout />;
};
