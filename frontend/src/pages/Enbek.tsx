import React from 'react';
import './Employees.css';

export const Enbek: React.FC = () => {
  return (
    <div className="detail-section">
      <h2>Интеграция с Enbek</h2>
      <p className="info-text">Статус интеграции: в разработке.</p>
      <p>
        Идут доработки. Подключение к Enbek будет реализовано на следующем этапе
        после согласования технических требований и мер защиты персональных данных.
      </p>
      <p style={{ marginTop: 16 }}>
        <span className="status-badge">В разработке</span>
      </p>
    </div>
  );
};
