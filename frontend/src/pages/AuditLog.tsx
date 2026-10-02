import React, { useEffect, useState } from 'react';
import { getAudit } from '../api/api';
import { AuditItem } from '../types';
import './Employees.css';

export const AuditLog: React.FC = () => {
  const [items, setItems] = useState<AuditItem[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    getAudit()
      .then(setItems)
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Не удалось загрузить журнал действий.');
      });
  }, []);

  return (
    <div className="documents-page">
      {error && <div className="error-banner">{error}</div>}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Дата/время</th>
              <th>Пользователь</th>
              <th>Действие</th>
              <th>Тип</th>
              <th>ID</th>
              <th>Результат</th>
              <th>Детали</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.created_at ? new Date(item.created_at).toLocaleString('ru-RU') : '-'}</td>
                <td>{item.username || '-'}</td>
                <td>{item.action}</td>
                <td>{item.object_type || '-'}</td>
                <td>{item.object_id || '-'}</td>
                <td>{item.result || '-'}</td>
                <td>{item.details || '-'}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={7} className="empty-state">Записей пока нет</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
};
