import React, { useEffect, useState } from 'react';
import { activateTemplate, archiveTemplate, getTemplates, uploadTemplate } from '../api/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { DocumentTemplate } from '../types';
import './Employees.css';

const TYPES = [
  { id: 'contract', label: 'Трудовой договор' },
  { id: 'order', label: 'Приказ о приёме' },
  { id: 'material_responsibility', label: 'Договор материальной ответственности' },
  { id: 'application', label: 'Заявление о приёме' },
  { id: 'material_responsibility', label: 'Договор материальной ответственности' },
  { id: 'consent', label: 'Согласие на обработку ПДн' },
  { id: 'termination_application', label: 'Заявление на увольнение' },
  { id: 'other', label: 'Другой документ' },
];

export const Templates: React.FC = () => {
  const toast = useToast();
  const { hasPermission } = useAuth();
  const [items, setItems] = useState<DocumentTemplate[]>([]);
  const [name, setName] = useState('');
  const [type, setType] = useState('contract');
  const [version, setVersion] = useState('v1');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const load = () => getTemplates().then(setItems).catch(() => toast('Не удалось загрузить шаблоны.', 'error'));

  useEffect(() => { load(); }, []);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append('name', name);
    form.append('type', type);
    form.append('version', version);
    form.append('description', description);
    form.append('is_active', 'true');
    form.append('file', file);
    try {
      await uploadTemplate(form);
      toast('Шаблон загружен.', 'success');
      setName('');
      setDescription('');
      setFile(null);
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось загрузить шаблон.', 'error');
    }
  };

  return (
    <div className="employees-page">
      {hasPermission('templates.manage') && <form className="detail-section" onSubmit={submit}>
        <h3>+ Загрузить шаблон</h3>
        <div className="fields-grid">
          <label className="detail-field">Название<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
          <label className="detail-field">Тип
            <select value={type} onChange={(e) => setType(e.target.value)}>
              {TYPES.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </label>
          <label className="detail-field">Версия<input value={version} onChange={(e) => setVersion(e.target.value)} /></label>
          <label className="detail-field">Описание<input value={description} onChange={(e) => setDescription(e.target.value)} /></label>
          <label className="detail-field">Файл DOCX<input type="file" accept=".docx" onChange={(e) => setFile(e.target.files?.[0] || null)} required /></label>
        </div>
        <div className="dashboard-actions" style={{ marginTop: 16 }}>
          <button className="btn-primary" type="submit">Загрузить шаблон</button>
        </div>
      </form>}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Название</th>
              <th>Тип</th>
              <th>Версия</th>
              <th>Статус</th>
              <th>Автор</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{TYPES.find((t) => t.id === item.type)?.label || item.type}</td>
                <td>{item.version}</td>
                <td>{item.is_active ? 'Активный шаблон' : 'Архив версии'}</td>
                <td>{item.created_by_name || '-'}</td>
                <td>
                  {!item.is_active && (
                    <>
                      {hasPermission('templates.manage') && <button className="btn-outline" onClick={async () => { await activateTemplate(item.id); load(); }}>Сделать активным</button>}
                      {hasPermission('templates.archive') && <button className="btn-danger" onClick={async () => {
                        if (!window.confirm('Архивировать эту версию шаблона?')) return;
                        try { await archiveTemplate(item.id); toast('Версия шаблона архивирована.', 'success'); load(); }
                        catch (err) { toast(err instanceof Error ? err.message : 'Не удалось архивировать шаблон.', 'error'); }
                      }}>Архивировать</button>}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
