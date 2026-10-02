import React, { useEffect, useState } from 'react';
import { clearDocuments, downloadAuthorized, getDocumentDownloadUrl, getDocuments, getDocumentsExcelUrl } from '../api/api';
import { ConfirmModal } from '../components/ConfirmModal';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Document } from '../types';
import './Documents.css';
import './Employees.css';

const TYPE_LABELS: Record<string, string> = {
  identity: 'Удостоверение личности',
  contract: 'Договор',
  order: 'Приказ',
  material_responsibility: 'Договор материальной ответственности',
  application: 'Заявление о приёме',
  consent: 'Согласие',
  termination_application: 'Увольнение',
};

export const Documents: React.FC = () => {
  const toast = useToast();
  const { hasPermission } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [error, setError] = useState('');
  const [zoom, setZoom] = useState(85);
  const [confirmClear, setConfirmClear] = useState(false);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    getDocuments().then(setDocuments).catch(() => setError('Не удалось загрузить документы.'));
  }, []);

  const handleClearDocuments = async () => {
    setClearing(true);
    try {
      const result = await clearDocuments();
      setDocuments([]);
      setConfirmClear(false);
      toast(`Удалено документов: ${result.deleted}.`, 'success');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось очистить документы.', 'error');
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="documents-page">
      {error && <div className="error-banner">{error}</div>}
      <div className="dashboard-actions documents-toolbar">
        <div className="dashboard-actions">
          {hasPermission('documents.export') && <button className="btn-outline" onClick={() => downloadAuthorized(getDocumentsExcelUrl(), 'documents.xlsx')}>Экспорт Excel</button>}
          {hasPermission('documents.clear') && (
            <button className="btn-danger" type="button" onClick={() => setConfirmClear(true)} disabled={!documents.length || clearing}>
              Очистить документы
            </button>
          )}
        </div>
        <label className="documents-zoom">
          <span>Масштаб</span>
          <input
            type="range"
            min={80}
            max={140}
            step={5}
            value={zoom}
            onChange={(event) => setZoom(Number(event.target.value))}
          />
          <strong>{zoom}%</strong>
        </label>
      </div>
      <div className="table-container" style={{ zoom: zoom / 100 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Документ</th>
              <th>Сотрудник</th>
              <th>Тип</th>
              <th>Дата</th>
              <th>Кто создал</th>
              <th>Версия</th>
              <th>Статус</th>
              {hasPermission('documents.download') && <th></th>}
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>{doc.file_name}</td>
                <td>{doc.employee_name || `ID: ${doc.employee_id}`}</td>
                <td>{TYPE_LABELS[doc.type] || doc.type}</td>
                <td>{doc.created_at ? new Date(doc.created_at).toLocaleDateString('ru-RU') : ''}</td>
                <td>{doc.created_by_name || '-'}</td>
                <td>{doc.version || '-'}</td>
                <td><span className="status-badge">{doc.status || 'Готов'}</span></td>
                {hasPermission('documents.download') && <td>
                  <button className="btn-text" onClick={() => downloadAuthorized(getDocumentDownloadUrl(doc.id), doc.file_name)}>Скачать</button>
                </td>}
              </tr>
            ))}
            {documents.length === 0 && (
              <tr><td colSpan={hasPermission('documents.download') ? 8 : 7} className="empty-state">Документы не найдены</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {confirmClear && (
        <ConfirmModal
          title="Очистить документы?"
          body={`Будут удалены все ${documents.length} записей документов. Шаблоны и удостоверения, используемые в карточках сотрудников, сохранятся.`}
          confirmLabel={clearing ? 'Очистка...' : 'Очистить'}
          danger
          onCancel={() => setConfirmClear(false)}
          onConfirm={handleClearDocuments}
        />
      )}
    </div>
  );
};
