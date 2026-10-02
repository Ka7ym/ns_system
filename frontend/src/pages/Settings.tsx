import React, { useEffect, useState } from 'react';
import { createBackup, downloadAuthorized, getBackupDownloadUrl, getBackups, getSettings, updateSettings } from '../api/api';
import { useToast } from '../context/ToastContext';
import { AppSettings, BackupItem } from '../types';
import './Employees.css';

export const Settings: React.FC = () => {
  const toast = useToast();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [maxUploadMb, setMaxUploadMb] = useState('10');
  const [tesseractCmd, setTesseractCmd] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [companyBin, setCompanyBin] = useState('');
  const [companyAddress, setCompanyAddress] = useState('');
  const [companyDirector, setCompanyDirector] = useState('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const loaded = await getSettings();
    setSettings(loaded);
    setMaxUploadMb(String(loaded.max_upload_mb));
    setTesseractCmd(loaded.tesseract_cmd);
    setCompanyName(loaded.company_name);
    setCompanyBin(loaded.company_bin);
    setCompanyAddress(loaded.company_address);
    setCompanyDirector(loaded.company_director);
    setBackups(await getBackups());
  };

  useEffect(() => {
    load().catch(() => toast('Не удалось загрузить настройки.', 'error'));
  }, []);

  const makeBackup = async () => {
    try {
      await createBackup();
      toast('Резервная копия создана.', 'success');
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось создать backup.', 'error');
    }
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const saved = await updateSettings({
        max_upload_mb: Number(maxUploadMb),
        tesseract_cmd: tesseractCmd.trim(),
        company_name: companyName.trim(),
        company_bin: companyBin.trim(),
        company_address: companyAddress.trim(),
        company_director: companyDirector.trim(),
      });
      setSettings(saved);
      setMaxUploadMb(String(saved.max_upload_mb));
      setTesseractCmd(saved.tesseract_cmd);
      setCompanyName(saved.company_name);
      setCompanyBin(saved.company_bin);
      setCompanyAddress(saved.company_address);
      setCompanyDirector(saved.company_director);
      toast('Настройки сохранены. Перезапустите backend для применения лимита загрузки.', 'success');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось сохранить настройки.', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="employees-page">
      <form className="detail-section" onSubmit={save}>
        <h3>Параметры системы</h3>
        <div className="fields-grid">
          <label className="detail-field"><span>Название компании</span><input value={companyName} onChange={(event) => setCompanyName(event.target.value)} required /></label>
          <label className="detail-field"><span>БИН</span><input inputMode="numeric" maxLength={12} value={companyBin} onChange={(event) => setCompanyBin(event.target.value.replace(/\D/g, ''))} placeholder="12 цифр" /></label>
          <label className="detail-field"><span>Адрес</span><input value={companyAddress} onChange={(event) => setCompanyAddress(event.target.value)} /></label>
          <label className="detail-field"><span>Руководитель</span><input value={companyDirector} onChange={(event) => setCompanyDirector(event.target.value)} /></label>
          <label className="detail-field">
            <span>Максимальный размер файла, МБ</span>
            <input type="number" min="1" max="100" value={maxUploadMb} onChange={(event) => setMaxUploadMb(event.target.value)} />
          </label>
          <label className="detail-field">
            <span>Путь к Tesseract OCR</span>
            <input placeholder="C:\\Program Files\\Tesseract-OCR\\tesseract.exe" value={tesseractCmd} onChange={(event) => setTesseractCmd(event.target.value)} />
          </label>
        </div>
        <div className="dashboard-actions" style={{ marginTop: 16 }}>
          <button className="btn-primary" type="submit" disabled={saving}>{saving ? 'Сохранение...' : 'Сохранить настройки'}</button>
        </div>
      </form>
      <section className="detail-section">
        <h3>OCR</h3>
        <p><strong>Статус:</strong> {settings?.ocr_configured ? 'Готов к работе' : 'Требуется настройка'}</p>
        <p>{settings?.ocr_message || 'Проверка статуса...'}</p>
      </section>
      <section className="detail-section">
        <h3>Безопасность</h3>
        <p><strong>HTTPS:</strong> {settings?.https_ready ? 'Подготовлен' : 'Не настроен для development-среды'}</p>
        <p>Персональные данные обрабатываются локально и не отправляются во внешние AI-сервисы.</p>
      </section>
      <section className="detail-section">
        <h3>Резервное копирование</h3>
        <button className="btn-primary" onClick={makeBackup}>Создать backup</button>
        <div className="document-list" style={{ marginTop: 16 }}>
          {backups.map((item) => (
            <div key={item.id} className="document-row">
              <div>
                <strong>{item.file_name}</strong>
                <span>{item.created_at ? new Date(item.created_at).toLocaleString('ru-RU') : ''}</span>
              </div>
              <button className="btn-outline" onClick={() => downloadAuthorized(getBackupDownloadUrl(item.id), item.file_name)}>Скачать</button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
