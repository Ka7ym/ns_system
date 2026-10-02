import React from 'react';
import './Employees.css';

export const Integration1C: React.FC = () => {
  return (
    <div className="detail-section">
      <h2>Интеграция с 1С</h2>
      <p className="info-text">Статус интеграции: в разработке.</p>
      <p>Идут доработки. Интеграция с 1С будет реализована на следующем этапе после согласования технических требований.</p>
      <p style={{ marginTop: 16 }}><span className="status-badge">В разработке</span></p>
    </div>
  );
};
