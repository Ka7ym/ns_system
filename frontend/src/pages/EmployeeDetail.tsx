import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import {
  archiveEmployee,
  downloadAuthorized,
  generateDocuments,
  getDocumentDownloadUrl,
  getEmployee,
  getEmployeeDocuments,
  getEmployeeHistory,
  restoreEmployee,
  terminateEmployee,
  updateEmployee,
} from '../api/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Document, Employee, EmployeeHistory, EmployeeStatus } from '../types';
import './EmployeeDetail.css';

type Tab = 'details' | 'documents' | 'history';

const EMPTY_EMPLOYEE: Partial<Employee> = {
  full_name: '',
  iin: '',
  birth_year: undefined,
  birth_date_full: '',
  phone: '',
  email: '',
  address: '',
  position: '',
  department: '',
  start_date: '',
  contract_type: '',
  work_schedule: '',
  salary: 0,
  status: 'Новый',
};

const STATUSES: EmployeeStatus[] = ['Новый', 'Работает', 'На проверке', 'Уволен', 'Архив'];
const TYPE_LABELS: Record<string, string> = {
  identity: 'Удостоверение личности',
  contract: 'Трудовой договор',
  order: 'Приказ о приёме',
  material_responsibility: 'Договор материальной ответственности',
  application: 'Заявление о приёме',
  consent: 'Согласие на обработку ПДн',
  termination_application: 'Заявление на увольнение',
  other: 'Другой документ',
};

export const EmployeeDetail: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const toast = useToast();
  const employeeId = Number(id);

  const [employee, setEmployee] = useState<Employee | null>(null);
  const [form, setForm] = useState<Partial<Employee>>(EMPTY_EMPLOYEE);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [history, setHistory] = useState<EmployeeHistory[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('details');
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [showTerminate, setShowTerminate] = useState(false);
  const [terminateDate, setTerminateDate] = useState('');
  const [terminateReason, setTerminateReason] = useState('');
  const [createApplication, setCreateApplication] = useState(true);

  useEffect(() => {
    loadEmployee();
  }, [employeeId, hasPermission]);

  const canTerminate = useMemo(() => {
    return employee && employee.status !== 'Уволен' && employee.status !== 'Архив';
  }, [employee]);

  const loadEmployee = async () => {
    if (!employeeId) return;
    setLoading(true);
    setError('');
    try {
      const [employeeData, documentData, historyData] = await Promise.all([
        getEmployee(employeeId),
        hasPermission('documents.view') ? getEmployeeDocuments(employeeId) : Promise.resolve([]),
        getEmployeeHistory(employeeId),
      ]);
      setEmployee(employeeData);
      setForm(employeeData);
      setDocuments(documentData);
      setHistory(historyData);
    } catch {
      setError('Не удалось загрузить карточку сотрудника.');
    } finally {
      setLoading(false);
    }
  };

  const updateForm = (key: keyof Employee, value: string | number) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const saveEmployee = async () => {
    if (!employee) return;
    setSaving(true);
    setError('');
    try {
      const saved = await updateEmployee(employee.id, {
        ...form,
        salary: Number(form.salary || 0),
        birth_year: form.birth_year ? Number(form.birth_year) : undefined,
      });
      setEmployee(saved);
      setForm(saved);
      setEditing(false);
      toast('Сотрудник успешно сохранён.', 'success');
      await loadEmployee();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Не удалось сохранить изменения.';
      setError(message);
      toast(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const archiveCurrentEmployee = async () => {
    if (!employee) return;
    setSaving(true);
    try {
      const archived = await archiveEmployee(employee.id);
      setEmployee(archived);
      setForm(archived);
      setConfirmArchive(false);
      toast('Сотрудник перенесён в архив.', 'warning');
      await loadEmployee();
    } catch {
      setError('Не удалось перенести сотрудника в архив.');
      toast('Не удалось удалить сотрудника.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const restoreCurrentEmployee = async () => {
    if (!employee) return;
    setSaving(true);
    try {
      await restoreEmployee(employee.id);
      toast('Сотрудник восстановлен.', 'success');
      await loadEmployee();
    } catch {
      toast('Не удалось восстановить сотрудника из архива.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const terminateCurrentEmployee = async () => {
    if (!employee || !terminateDate) return;
    setSaving(true);
    try {
      await terminateEmployee(employee.id, {
        termination_date: terminateDate,
        termination_reason: terminateReason,
        create_application: createApplication,
      });
      setShowTerminate(false);
      toast('Увольнение оформлено.', 'success');
      await loadEmployee();
      setActiveTab('documents');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Не удалось оформить увольнение.';
      setError(message);
      toast(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const generateEmployeeDocuments = async () => {
    if (!employee) return;
    setSaving(true);
    try {
      await generateDocuments(employee.id, ['contract', 'order']);
      toast('Документы сформированы.', 'success');
      await loadEmployee();
      setActiveTab('documents');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось сформировать документы.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (value?: string | null) => {
    if (!value) return '-';
    const datePart = value.includes('T') ? value.split('T')[0] : value;
    const [year, month, day] = datePart.split('-');
    if (!year || !month || !day) return value;
    return `${day}.${month}.${year}`;
  };

  const formatSalary = (salary?: number) => {
    if (salary === undefined || salary === null) return '-';
    return `${salary.toLocaleString('ru-RU')} ₸`;
  };

  const identityExpiryNotice = (() => {
    if (!employee?.document_expiry_date) return null;
    const expiry = new Date(employee.document_expiry_date);
    if (Number.isNaN(expiry.getTime())) return null;
    const days = Math.ceil((expiry.getTime() - Date.now()) / 86400000);
    if (days < 0) return 'Срок действия удостоверения истёк.';
    if (days <= 30) return `Срок действия удостоверения истекает через ${days} дн.`;
    return null;
  })();

  const field = (
    label: string,
    key: keyof Employee,
    type: 'text' | 'number' | 'date' | 'email' = 'text',
  ) => (
    <label className="detail-field">
      <span>{label}</span>
      {editing ? (
        <input
          type={type}
          value={(form[key] as string | number | undefined) ?? ''}
          onChange={(event) => updateForm(key, type === 'number' ? Number(event.target.value) : event.target.value)}
        />
      ) : (
        <strong>
          {key === 'salary'
            ? formatSalary(employee?.salary)
            : key === 'start_date' || key === 'created_at' || key === 'updated_at' || key === 'document_issue_date' || key === 'document_expiry_date'
              ? formatDate(employee?.[key] as string)
              : (employee?.[key] as string | number | null) || '-'}
        </strong>
      )}
    </label>
  );

  if (loading) return <div className="employee-detail-page">Загрузка карточки...</div>;
  if (error && !employee) {
    return (
      <div className="employee-detail-page">
        <div className="error-banner">{error}</div>
        <button className="btn-outline" onClick={() => navigate('/employees')}>Назад к списку</button>
      </div>
    );
  }
  if (!employee) return null;

  return (
    <div className="employee-detail-page">
      <div className="detail-header">
        <button className="btn-outline" onClick={() => navigate('/employees')}>Назад</button>
        <div className="detail-title">
          <h2>{employee.full_name}</h2>
          <span className={`status-badge status-${employee.status.replace(/\s+/g, '-')}`}>{employee.status}</span>
        </div>
        <div className="detail-actions">
          {editing ? (
            <>
              <button className="btn-outline" onClick={() => { setEditing(false); setForm(employee); }}>Отмена</button>
              <button className="btn-primary" disabled={saving} onClick={saveEmployee}>Сохранить</button>
            </>
          ) : (
            <>
              {hasPermission('employees.edit') && <button className="btn-outline" onClick={() => setEditing(true)}>Редактировать</button>}
              {hasPermission('documents.view') && <button className="btn-outline" onClick={() => setActiveTab('documents')}>Документы</button>}
              {hasPermission('employees.view') && <button className="btn-outline" onClick={() => setActiveTab('history')}>История</button>}
              {canTerminate && hasPermission('employees.archive') && (
                <button className="btn-danger" onClick={() => setShowTerminate(true)}>Уволить</button>
              )}
              {hasPermission('employees.archive') && (employee.is_deleted ? (
                <button className="btn-primary" disabled={saving} onClick={restoreCurrentEmployee}>Восстановить</button>
              ) : (
                <button className="btn-danger" disabled={saving} onClick={() => setConfirmArchive(true)}>Удалить</button>
              ))}
            </>
          )}
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {identityExpiryNotice && <div className="warning-banner">{identityExpiryNotice}</div>}

      <div className="detail-tabs">
        <button className={activeTab === 'details' ? 'active' : ''} onClick={() => setActiveTab('details')}>Основная информация</button>
        {hasPermission('documents.view') && <button className={activeTab === 'documents' ? 'active' : ''} onClick={() => setActiveTab('documents')}>Документы</button>}
        {hasPermission('employees.view') && <button className={activeTab === 'history' ? 'active' : ''} onClick={() => setActiveTab('history')}>История</button>}
      </div>

      {activeTab === 'details' && (
        <div className="detail-grid">
          <section className="detail-section">
            <h3>Личные данные</h3>
            <div className="fields-grid">
              {field('ФИО', 'full_name')}
              {field('ИИН', 'iin')}
              {field('Дата рождения', 'birth_date_full')}
              {field('Год рождения', 'birth_year', 'number')}
              {field('Телефон', 'phone')}
              {field('Email', 'email', 'email')}
              {field('Номер документа', 'document_number')}
              {field('Дата выдачи', 'document_issue_date')}
              {field('Срок действия', 'document_expiry_date')}
            </div>
          </section>
          <section className="detail-section">
            <h3>Рабочие данные</h3>
            <div className="fields-grid">
              {field('Должность', 'position')}
              {field('Отдел', 'department')}
              {field('Дата приема', 'start_date', 'date')}
              {field('Тип договора', 'contract_type')}
              {field('График работы', 'work_schedule')}
              {field('Оклад', 'salary', 'number')}
              <label className="detail-field">
                <span>Статус</span>
                {editing ? (
                  <select value={form.status || 'Новый'} onChange={(event) => updateForm('status', event.target.value)}>
                    {STATUSES.map((status) => (
                      <option key={status} value={status}>{status}</option>
                    ))}
                  </select>
                ) : (
                  <strong>{employee.status}</strong>
                )}
              </label>
            </div>
          </section>
          {(employee.termination_date || employee.termination_reason) && (
            <section className="detail-section">
              <h3>Увольнение</h3>
              <div className="fields-grid">
                <label className="detail-field"><span>Дата увольнения</span><strong>{formatDate(employee.termination_date)}</strong></label>
                <label className="detail-field"><span>Причина увольнения</span><strong>{employee.termination_reason || '-'}</strong></label>
              </div>
            </section>
          )}
        </div>
      )}

      {activeTab === 'documents' && (
        <section className="detail-section">
          <div className="section-toolbar">
            <h3>Документы сотрудника</h3>
            {hasPermission('documents.generate') && <button className="btn-primary" disabled={saving} onClick={generateEmployeeDocuments}>Сформировать документы</button>}
          </div>
          <div className="document-list">
            {documents.map((document) => (
              <div key={document.id} className="document-row">
                <div>
                  <strong>{TYPE_LABELS[document.type] || document.type}</strong>
                  <span>{document.file_name} · {document.status || 'Готов'} · {document.version || '-'} · {document.created_by_name || 'система'} · {formatDate(document.created_at)}</span>
                </div>
                {hasPermission('documents.download') && <button
                  className="btn-outline"
                  onClick={() => downloadAuthorized(getDocumentDownloadUrl(document.id), document.file_name)}
                >
                  Скачать
                </button>}
              </div>
            ))}
            {documents.length === 0 && <div className="empty-state">Документы пока не сформированы</div>}
          </div>
        </section>
      )}

      {activeTab === 'history' && (
        <section className="detail-section">
          <h3>История</h3>
          <div className="history-list">
            {history.map((item) => (
              <div key={item.id} className="history-row">
                <div>
                  <strong>{item.action}</strong>
                    <span>
                      {item.field_label
                        ? `${item.field_label}: ${item.old_value || '—'} → ${item.new_value || '—'}`
                        : item.description || '-'}
                    </span>
                </div>
                <time>{item.created_at ? new Date(item.created_at).toLocaleString('ru-RU') : '-'}</time>
              </div>
            ))}
            {history.length === 0 && <div className="empty-state">История пока пуста</div>}
          </div>
        </section>
      )}

      {confirmArchive && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <h3>Вы действительно хотите удалить сотрудника?</h3>
            <p>Это действие изменит статус записи и может повлиять на связанные данные. Документы и история сохранятся.</p>
            <div className="step-actions">
              <button className="btn-outline" onClick={() => setConfirmArchive(false)}>Отмена</button>
              <button className="btn-danger" disabled={saving} onClick={archiveCurrentEmployee}>Удалить</button>
            </div>
          </div>
        </div>
      )}

      {showTerminate && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <h3>Оформление увольнения</h3>
            <label className="detail-field">
              <span>Причина</span>
              <input value={terminateReason} onChange={(e) => setTerminateReason(e.target.value)} />
            </label>
            <label className="detail-field">
              <span>Дата увольнения</span>
              <input type="date" value={terminateDate} onChange={(e) => setTerminateDate(e.target.value)} />
            </label>
            <label className="checkbox-row">
              <input type="checkbox" checked={createApplication} onChange={(e) => setCreateApplication(e.target.checked)} />
              Создать заявление
            </label>
            <div className="step-actions">
              <button className="btn-outline" onClick={() => setShowTerminate(false)}>Отмена</button>
              <button className="btn-danger" disabled={!terminateDate || saving} onClick={terminateCurrentEmployee}>Оформить увольнение</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
