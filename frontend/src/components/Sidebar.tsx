import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Sidebar.css';

export const Sidebar: React.FC = () => {
  const { user, hasPermission, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h2>NS SYSTEM</h2>
        <span>Кадровая система</span>
      </div>
      <nav className="sidebar-nav">
        {hasPermission('dashboard.view') && <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
          Dashboard
        </NavLink>}
        {hasPermission('employees.view') && <NavLink to="/employees" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
          Сотрудники
        </NavLink>}
        {hasPermission('documents.view') && <NavLink to="/documents" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
          Документы
        </NavLink>}
        {hasPermission('absences.view') && <NavLink to="/absences" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
          Отпуска и больничные
        </NavLink>}
        {hasPermission('templates.view') && <NavLink to="/templates" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
          Шаблоны документов
        </NavLink>}
        {hasPermission('audit.view') && <NavLink to="/audit" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
          Журнал действий
        </NavLink>}
        {hasPermission('enbek.view') && <NavLink to="/enbek" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
          Enbek
        </NavLink>}
        {hasPermission('users.manage') && <NavLink to="/users" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
          Пользователи
        </NavLink>}
        {hasPermission('settings.manage') && (
          <>
            <NavLink to="/onec" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              1С
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              Настройки
            </NavLink>
          </>
        )}
        {hasPermission('references.manage') && <NavLink to="/references" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              Справочники
        </NavLink>}
        {hasPermission('errors.view') && <NavLink to="/errors" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
              Ошибки системы
        </NavLink>}
      </nav>
      <div className="sidebar-user">
        <strong>{user?.username}</strong>
        <span>{user?.role}</span>
        <button className="btn-text" onClick={logout}>Выйти</button>
      </div>
      <div className="sidebar-footer">НС Система © 2026</div>
    </aside>
  );
};
