import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StatsCard } from '../components/StatsCard';
import { getDashboardStats, DashboardStats } from '../api/api';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => setError('Не удалось загрузить актуальную статистику.'));
  }, []);

  return (
    <div className="dashboard">
      <div className="stats-grid">
        <StatsCard label="Сотрудники" value={stats?.employees ?? 0} colorClass="blue" />
        <StatsCard label="Новые" value={stats?.new ?? 0} colorClass="green" />
        <StatsCard label="Документы" value={stats?.documents ?? 0} colorClass="purple" />
        <StatsCard label="На проверке" value={stats?.review ?? 0} colorClass="orange" />
        <StatsCard label="Уволенные" value={stats?.terminated ?? 0} colorClass="red" />
        <StatsCard label="Истекают документы" value={stats?.expiring_documents ?? 0} colorClass="orange" />
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="dashboard-actions">
        <button className="btn-primary" onClick={() => navigate('/new-employee')}>
          + Новый сотрудник
        </button>
      </div>

      <div className="recent-actions">
        <h3>Последние действия</h3>
        <ul className="action-list">
          {stats?.recent_actions.map((item) => (
            <li key={item.id}>
              <span className="action-icon">•</span>
              <div className="action-content">
                <strong>{item.employee_name}</strong> — {item.description || item.action}
                <span className="action-time">
                  {item.created_at ? new Date(item.created_at).toLocaleString('ru-RU') : '-'}
                </span>
              </div>
            </li>
          ))}
          {stats && stats.recent_actions.length === 0 && <li>История действий пока пуста</li>}
        </ul>
      </div>
    </div>
  );
};
