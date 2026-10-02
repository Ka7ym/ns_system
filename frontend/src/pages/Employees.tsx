import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { downloadAuthorized, getEmployees, getEmployeesExcelUrl, getEmployeesExportUrl } from '../api/api';
import { useAuth } from '../context/AuthContext';
import { Employee, EmployeeStatus } from '../types';
import './Employees.css';

const STATUS_FILTERS: Array<EmployeeStatus | 'Все'> = [
  'Все',
  'Новый',
  'Работает',
  'На проверке',
  'Уволен',
  'Архив',
];

export const Employees: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [position, setPosition] = useState('');
  const [status, setStatus] = useState<EmployeeStatus | 'Все'>('Все');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [sort, setSort] = useState('id');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const pageSize = 20;

  useEffect(() => {
    setPage(1);
  }, [search, department, position, status, sort, order]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      fetchEmployees();
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search, status, page, sort, order]);

  const fetchEmployees = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getEmployees({
        search,
        department,
        position,
        status,
        page,
        pageSize,
        includeArchived: status === 'Архив',
        sort,
        order,
      });
      setEmployees(data.items);
      setTotal(data.total);
      setCounts(data.counts || {});
    } catch {
      setError('Не удалось загрузить сотрудников. Проверьте, что backend запущен.');
      setEmployees([]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSort = (field: string) => {
    if (sort === field) setOrder(order === 'asc' ? 'desc' : 'asc');
    else {
      setSort(field);
      setOrder('asc');
    }
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return '-';
    const datePart = dateString.includes('T') ? dateString.split('T')[0] : dateString;
    const [year, month, day] = datePart.split('-');
    if (!year || !month || !day) return dateString;
    return `${day}.${month}.${year}`;
  };

  const formatSalary = (salary?: number) => {
    if (salary === undefined || salary === null) return '-';
    return `${salary.toLocaleString('ru-RU')} ₸`;
  };

  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="employees-page">
      <div className="employee-summary">
        <div>
          <span className="summary-label">Все</span>
          <strong>{counts['Все'] ?? 0}</strong>
        </div>
        <div>
          <span className="summary-label">Работают</span>
          <strong>{counts['Работает'] ?? 0}</strong>
        </div>
        <div>
          <span className="summary-label">На проверке</span>
          <strong>{counts['На проверке'] ?? 0}</strong>
        </div>
        <div>
          <span className="summary-label">Уволены</span>
          <strong>{counts['Уволен'] ?? 0}</strong>
        </div>
      </div>

      <div className="page-header">
        <div className="search-bar">
          <span className="search-icon">Поиск</span>
          <input
            type="text"
            placeholder="Поиск по ФИО или ИИН"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <input
          className="filter-input"
          placeholder="Подразделение"
          value={department}
          onChange={(event) => setDepartment(event.target.value)}
        />
        <input
          className="filter-input"
          placeholder="Должность"
          value={position}
          onChange={(event) => setPosition(event.target.value)}
        />
        {hasPermission('employees.create') && <button className="btn-primary" onClick={() => navigate('/new-employee')}>
          + Новый сотрудник
        </button>}
        {hasPermission('employees.export') && <button className="btn-outline" onClick={() => downloadAuthorized(
          getEmployeesExportUrl({ search, department, position, status }),
          'employees.csv',
        )}>
          Экспорт CSV
        </button>}
        {hasPermission('employees.export') && <button className="btn-outline" onClick={() => downloadAuthorized(getEmployeesExcelUrl(), 'employees.xlsx')}>
          Экспорт Excel
        </button>}
      </div>

      <div className="filter-row">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter}
            className={`filter-chip ${status === filter ? 'active' : ''}`}
            onClick={() => setStatus(filter)}
          >
            {filter}
          </button>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => toggleSort('full_name')}>ФИО</th>
              <th>ИИН</th>
              <th>Должность</th>
              <th>Отдел</th>
              <th>Оклад</th>
              <th onClick={() => toggleSort('start_date')}>Дата приема</th>
              <th onClick={() => toggleSort('status')}>Статус</th>
            </tr>
          </thead>
          <tbody>
            {employees.map((employee) => (
              <tr key={employee.id} onClick={() => navigate(`/employees/${employee.id}`)}>
                <td>
                  <strong>{employee.full_name}</strong>
                </td>
                <td>{employee.iin}</td>
                <td>{employee.position}</td>
                <td>{employee.department || '-'}</td>
                <td>{formatSalary(employee.salary)}</td>
                <td>{formatDate(employee.start_date)}</td>
                <td>
                  <span className={`status-badge status-${employee.status.replace(/\s+/g, '-')}`}>
                    {employee.status}
                  </span>
                </td>
              </tr>
            ))}
            {!loading && employees.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-state">
                  Сотрудники не найдены
                </td>
              </tr>
            )}
            {loading && (
              <tr>
                <td colSpan={7} className="empty-state">
                  Загрузка сотрудников...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <button className="btn-outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Назад
        </button>
        <span>
          Страница {page} из {pages}
        </span>
        <button className="btn-outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>
          Далее
        </button>
      </div>
    </div>
  );
};
