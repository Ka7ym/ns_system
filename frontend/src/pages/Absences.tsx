import React, { useEffect, useState } from 'react';
import { createAbsence, deleteAbsence, getAbsenceEmployeeOptions, getAbsences, updateAbsence } from '../api/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { AbsenceEmployeeOption, AbsenceType, EmployeeAbsence } from '../types';
import './Absences.css';
import './Employees.css';

const TYPE_LABELS: Record<AbsenceType, string> = {
  vacation: 'Отпуск',
  absence: 'Отсутствие',
  sick_leave: 'Больничный',
};

interface AbsenceForm {
  employee_id: string;
  type: AbsenceType;
  start_date: string;
  end_date: string;
  note: string;
}

const EMPTY_FORM: AbsenceForm = {
  employee_id: '',
  type: 'vacation',
  start_date: '',
  end_date: '',
  note: '',
};

export const Absences: React.FC = () => {
  const toast = useToast();
  const { hasPermission } = useAuth();
  const [records, setRecords] = useState<EmployeeAbsence[]>([]);
  const [employees, setEmployees] = useState<AbsenceEmployeeOption[]>([]);
  const [form, setForm] = useState<AbsenceForm>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const canManage = hasPermission('absences.manage');

  const load = async () => {
    setLoading(true);
    try {
      const [absenceRecords, employeeOptions] = await Promise.all([
        getAbsences(),
        canManage ? getAbsenceEmployeeOptions() : Promise.resolve([]),
      ]);
      setRecords(absenceRecords);
      setEmployees(employeeOptions);
    } catch {
      toast('Не удалось загрузить отпуска и отсутствия.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const setField = <K extends keyof AbsenceForm>(key: K, value: AbsenceForm[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const startEditing = (record: EmployeeAbsence) => {
    setEditingId(record.id);
    setForm({
      employee_id: String(record.employee_id),
      type: record.type,
      start_date: record.start_date,
      end_date: record.end_date,
      note: record.note || '',
    });
  };

  const cancelEditing = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (form.end_date < form.start_date) {
      toast('Дата окончания не может быть раньше даты начала.', 'error');
      return;
    }
    try {
      if (editingId) {
        await updateAbsence(editingId, {
          type: form.type,
          start_date: form.start_date,
          end_date: form.end_date,
          note: form.note,
        });
        toast('Запись обновлена.', 'success');
      } else {
        await createAbsence({
          employee_id: Number(form.employee_id),
          type: form.type,
          start_date: form.start_date,
          end_date: form.end_date,
          note: form.note,
        });
        toast('Запись добавлена.', 'success');
      }
      cancelEditing();
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : 'Не удалось сохранить запись.', 'error');
    }
  };

  const remove = async (record: EmployeeAbsence) => {
    if (!window.confirm(`Удалить запись «${TYPE_LABELS[record.type]}» для ${record.employee_name}?`)) return;
    try {
      await deleteAbsence(record.id);
      toast('Запись удалена.', 'success');
      await load();
    } catch (error) {
      toast(error instanceof Error ? error.message : 'Не удалось удалить запись.', 'error');
    }
  };

  return (
    <div className="absences-page">
      {canManage && (
        <form className="detail-section absence-form" onSubmit={save}>
          <h3>{editingId ? 'Изменить запись' : 'Добавить отпуск или отсутствие'}</h3>
          <div className="fields-grid">
            <label className="detail-field">
              Сотрудник
              <select
                value={form.employee_id}
                onChange={(event) => setField('employee_id', event.target.value)}
                required
                disabled={Boolean(editingId)}
              >
                <option value="">Выберите сотрудника</option>
                {employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>{employee.full_name}</option>
                ))}
              </select>
            </label>
            <label className="detail-field">
              Тип
              <select value={form.type} onChange={(event) => setField('type', event.target.value as AbsenceType)}>
                {Object.entries(TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label className="detail-field">
              Дата начала
              <input type="date" value={form.start_date} onChange={(event) => setField('start_date', event.target.value)} required />
            </label>
            <label className="detail-field">
              Дата окончания
              <input type="date" value={form.end_date} onChange={(event) => setField('end_date', event.target.value)} min={form.start_date || undefined} required />
            </label>
            <label className="detail-field absence-note">
              Примечание
              <input value={form.note} onChange={(event) => setField('note', event.target.value)} maxLength={2000} />
            </label>
          </div>
          <div className="dashboard-actions absence-actions">
            {editingId && <button className="btn-outline" type="button" onClick={cancelEditing}>Отмена</button>}
            <button className="btn-primary" type="submit">{editingId ? 'Сохранить' : 'Добавить запись'}</button>
          </div>
        </form>
      )}

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr><th>Сотрудник</th><th>Тип</th><th>С даты</th><th>По дату</th><th>Примечание</th><th>Внёс</th>{canManage && <th></th>}</tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td>{record.employee_name || `ID: ${record.employee_id}`}</td>
                <td>{TYPE_LABELS[record.type]}</td>
                <td>{record.start_date}</td>
                <td>{record.end_date}</td>
                <td>{record.note || '-'}</td>
                <td>{record.created_by_name || '-'}</td>
                {canManage && <td className="absence-row-actions">
                  <button className="btn-outline" onClick={() => startEditing(record)}>Изменить</button>
                  <button className="btn-danger" onClick={() => void remove(record)}>Удалить</button>
                </td>}
              </tr>
            ))}
            {!loading && records.length === 0 && (
              <tr><td colSpan={canManage ? 7 : 6} className="empty-state">Записей пока нет</td></tr>
            )}
            {loading && <tr><td colSpan={canManage ? 7 : 6} className="empty-state">Загрузка...</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
};