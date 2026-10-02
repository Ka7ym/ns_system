import React from 'react';
import './StatsCard.css';

interface StatsCardProps {
  label: string;
  value: string | number;
  colorClass?: string;
}

export const StatsCard: React.FC<StatsCardProps> = ({ label, value, colorClass = 'blue' }) => {
  return (
    <div className={`stats-card ${colorClass}`}>
      <div className="stats-info">
        <div className="stats-label">{label}</div>
        <div className="stats-value">{value}</div>
      </div>
    </div>
  );
};
