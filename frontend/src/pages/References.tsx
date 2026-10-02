import React, { useEffect, useState } from 'react';
import { getReferences, ReferenceSettings, updateReferences } from '../api/api';
import { useToast } from '../context/ToastContext';
import './Employees.css';

const EMPTY: ReferenceSettings = { positions: [], departments: [], contract_types: [] };

export const References: React.FC = () => {
  const toast = useToast();
  const [data, setData] = useState(EMPTY);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getReferences().then(setData).catch(() => toast('Не удалось загрузить справочники.', 'error')).finally(() => setLoading(false));
  }, []);

  const update = (key: keyof ReferenceSettings, value: string) => {
    setData((current) => ({ ...current, [key]: value.split('\n') }));
  };

  const save = async () => {
    try {
      setData(await updateReferences(data));
      toast('Справочники сохранены.', 'success');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось сохранить справочники.', 'error');
    }
  };

  if (loading) return <div className="employees-page">Загрузка справочников...</div>;
  return (
    <div className="employees-page">
      <section className="detail-section">
        <h2>Справочники</h2>
        <p className="info-text">Каждое значение вводится с новой строки.</p>
        <div className="fields-grid">
          <label className="detail-field"><span>Должности</span><textarea rows={8} value={data.positions.join('\n')} onChange={(e) => update('positions', e.target.value)} /></label>
          <label className="detail-field"><span>Подразделения и отделы</span><textarea rows={8} value={data.departments.join('\n')} onChange={(e) => update('departments', e.target.value)} /></label>
          <label className="detail-field"><span>Типы договоров</span><textarea rows={8} value={data.contract_types.join('\n')} onChange={(e) => update('contract_types', e.target.value)} /></label>
        </div>
        <div className="dashboard-actions" style={{ marginTop: 16 }}><button className="btn-primary" onClick={save}>Сохранить справочники</button></div>
      </section>
    </div>
  );
};
