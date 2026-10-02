import React, { useEffect, useState } from 'react';
import { getErrors } from '../api/api';
import { useToast } from '../context/ToastContext';
import './Employees.css';

export const ErrorLog: React.FC = () => {
  const toast = useToast();
  const [items, setItems] = useState<Array<{ id: number; message: string }>>([]);
  useEffect(() => {
    getErrors().then(setItems).catch(() => toast('Не удалось загрузить журнал ошибок.', 'error'));
  }, []);
  return (
    <div className="employees-page">
      <section className="detail-section">
        <h2>Журнал ошибок системы</h2>
        <p className="info-text">Последние ошибки backend, доступные только администратору.</p>
        <div className="history-list">
          {items.map((item) => <div className="history-row" key={item.id}><span>{item.message}</span></div>)}
          {items.length === 0 && <div className="empty-state">Ошибок пока нет</div>}
        </div>
      </section>
    </div>
  );
};
