import React from 'react';
import { useLocation } from 'react-router-dom';
import './Header.css';

const TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/employees': 'Сотрудники',
  '/new-employee': 'Новый сотрудник',
  '/documents': 'Документы',
  '/templates': 'Шаблоны документов',
  '/audit': 'Журнал действий',
  '/users': 'Пользователи',
  '/onec': '1С',
  '/settings': 'Настройки',
};

export const Header: React.FC = () => {
  const location = useLocation();
  const title =
    TITLES[location.pathname] ||
    (location.pathname.startsWith('/employees/') ? 'Карточка сотрудника' : 'Панель управления');

  return (
    <header className="header">
      <h1 className="header-title">{title}</h1>
      <div className="header-badge">Кадровая система</div>
    </header>
  );
};
