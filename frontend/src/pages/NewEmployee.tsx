import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { checkEmployeeIin, createEmployee, ExistingEmployeeMatch, generateDocuments, getDocumentDownloadUrl, downloadAuthorized, recognizeDocument, rehireEmployee } from '../api/api';
import { useToast } from '../context/ToastContext';
import { Document, OcrResult } from '../types';
import './NewEmployee.css';

const STEPS = ['Удостоверение', 'Распознавание', 'Проверка', 'Работа', 'Документы', 'Подтверждение', 'Завершение'];
const ALLOWED = ['image/jpeg', 'image/png', 'application/pdf'];
const MAX_SIZE = 10 * 1024 * 1024;

const emptyOcr = (): OcrResult => ({
  full_name: '',
  iin: '',
  birth_date: '',
  birth_year: undefined,
  document_number: '',
  document_issue_date: '',
  document_expiry_date: '',
  confidence: 0,
  status: '',
  message: '',
  recognized: {},
});

export const NewEmployee: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [step, setStep] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [fileError, setFileError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('');
  const [ocrData, setOcrData] = useState<OcrResult>(emptyOcr());
  const [empData, setEmpData] = useState({
    position: '',
    salary: '',
    start_date: '',
    department: '',
    contract_type: 'Трудовой договор',
    work_schedule: '5/2',
    phone: '',
    email: '',
  });
  const [docTypes, setDocTypes] = useState<Record<string, boolean>>({
    contract: true,
    order: true,
    material_responsibility: true,
    consent: false,
    application: true,
  });
  const [generatedDocs, setGeneratedDocs] = useState<Document[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [duplicateEmployee, setDuplicateEmployee] = useState<ExistingEmployeeMatch | null>(null);
  const [rehireEmployeeId, setRehireEmployeeId] = useState<number | null>(null);
  const [createError, setCreateError] = useState('');

  const getBirthYear = (date?: string) => {
    if (!date) return undefined;
    const match = date.match(/^(?:\d{1,2}[./]\d{1,2}[./]|\d{4}-\d{2}-\d{2})(\d{4})?$/);
    if (match?.[1]) return Number(match[1]);
    const year = date.match(/(?:^|\D)(19\d{2}|20\d{2})(?:\D|$)/)?.[1];
    return year ? Number(year) : undefined;
  };

  const handleFileSelect = (selectedFile: File) => {
    const ext = selectedFile.name.split('.').pop()?.toLowerCase();
    if (!['jpg', 'jpeg', 'png', 'pdf'].includes(ext || '') || (!ALLOWED.includes(selectedFile.type) && selectedFile.type !== '')) {
      setFileError('Разрешены только JPG, JPEG, PNG и PDF.');
      return;
    }
    if (selectedFile.size > MAX_SIZE) {
      setFileError('Файл больше 10 МБ.');
      return;
    }
    setFileError('');
    setFile(selectedFile);
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null);
    }
  };

  const runOcr = async () => {
    if (!file) return;
    setLoading(true);
    setLoadingText('Распознавание документа...');
    try {
      const res = await recognizeDocument(file);
      setOcrData(res);
      setStep(2);
      if (res.status === 'ocr_not_configured') {
        toast(res.message || 'OCR требует настройки', 'warning');
      } else if (res.status === 'empty' || res.status === 'error') {
        toast(res.message || 'Данные требуют проверки.', 'warning');
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Ошибка распознавания', 'error');
    }
    setLoading(false);
    setLoadingText('');
  };

  const fieldStatus = (key: keyof OcrResult) => {
    const value = ocrData[key];
    const recognized = ocrData.recognized?.[key as string];
    if (recognized && value) return 'Распознано';
    return 'Поле не распознано';
  };

  const validateOcr = () => {
    const next: Record<string, string> = {};
    if (!ocrData.full_name.trim()) next.full_name = 'ФИО обязательно';
    if (!/^\d{12}$/.test(ocrData.iin)) next.iin = 'ИИН должен содержать 12 цифр';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const continueAfterIinCheck = async () => {
    if (!validateOcr()) return;
    setLoading(true);
    setLoadingText('Проверка ИИН...');
    setDuplicateEmployee(null);
    setRehireEmployeeId(null);
    try {
      const result = await checkEmployeeIin(ocrData.iin);
      if (result.exists && result.employee) {
        setDuplicateEmployee(result.employee);
        return;
      }
      setStep(4);
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Не удалось проверить ИИН.', 'error');
    } finally {
      setLoading(false);
      setLoadingText('');
    }
  };

  const validateEmp = () => {
    const next: Record<string, string> = {};
    if (!empData.position.trim()) next.position = 'Должность обязательна';
    if (!empData.department.trim()) next.department = 'Отдел обязателен';
    if (!empData.salary || Number(empData.salary) <= 0) next.salary = 'Оклад должен быть больше 0';
    if (!empData.start_date) next.start_date = 'Дата начала работы обязательна';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleCreate = async () => {
    setLoading(true);
    setLoadingText(rehireEmployeeId ? 'Повторное оформление и создание документов...' : 'Создание сотрудника и документов...');
    setCreateError('');
    try {
      const employeePayload = {
        full_name: ocrData.full_name,
        iin: ocrData.iin,
        birth_year: getBirthYear(ocrData.birth_date),
        birth_date_full: ocrData.birth_date,
        document_number: ocrData.document_number,
        document_issue_date: ocrData.document_issue_date,
        document_expiry_date: ocrData.document_expiry_date,
        identity_file_name: ocrData.identity_file_name,
        position: empData.position,
        salary: Number(empData.salary),
        start_date: empData.start_date,
        department: empData.department,
        contract_type: empData.contract_type,
        work_schedule: empData.work_schedule,
        phone: empData.phone,
        email: empData.email,
        status: 'Работает' as const,
      };
      const emp = rehireEmployeeId
        ? await rehireEmployee(rehireEmployeeId, employeePayload)
        : await createEmployee(employeePayload);
      const selected = [...new Set([
        'contract',
        'order',
        'material_responsibility',
        ...Object.entries(docTypes).filter(([, on]) => on).map(([key]) => key),
      ])];
      if (selected.length) {
        const docs = await generateDocuments(emp.id, selected);
        setGeneratedDocs(docs);
      }
      toast(rehireEmployeeId ? 'Сотрудник повторно принят. История и прежние документы сохранены.' : 'Сотрудник успешно создан.', 'success');
      setStep(7);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Не удалось создать сотрудника.';
      setCreateError(message);
      toast(message, 'error');
    }
    setLoading(false);
    setLoadingText('');
  };

  const ocrInput = (label: string, key: keyof OcrResult) => (
    <div className="form-group">
      <label>{label}</label>
      <div className="input-with-check">
        <input
          value={(ocrData[key] as string | number | undefined) ?? ''}
          onChange={(e) => {
            const value = key === 'iin' ? e.target.value.replace(/\D/g, '').slice(0, 12) : e.target.value;
            setOcrData({ ...ocrData, [key]: key === 'birth_year' ? Number(value) : value });
            if (key === 'iin') {
              setDuplicateEmployee(null);
              setRehireEmployeeId(null);
            }
          }}
        />
        <span className={`check-icon ${ocrData.recognized?.[key as string] ? '' : 'unrecognized'}`}>{fieldStatus(key)}</span>
      </div>
      {errors[key as string] && <span className="error-text">{errors[key as string]}</span>}
    </div>
  );

  if (loading) {
    return (
      <div className="new-employee-page">
        <div className="loading-overlay">
          <div className="spinner large" />
          <p className="loading-text">{loadingText}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="new-employee-page">
      <div className="step-indicator">
        {STEPS.map((_, i) => {
          const s = i + 1;
          return (
            <React.Fragment key={s}>
              <div className={`step-dot ${step >= s ? 'active' : ''} ${step > s ? 'completed' : ''}`}>{step > s ? '✓' : s}</div>
              {s < STEPS.length && <div className={`step-line ${step > s ? 'active' : ''}`} />}
            </React.Fragment>
          );
        })}
      </div>
      <div className="step-labels">
        {STEPS.map((label, i) => (
          <span key={label} className={step === i + 1 ? 'current-label' : ''}>{label}</span>
        ))}
      </div>

      <div className="step-content">
        {step === 1 && (
          <div className="step-card">
            <h3>Загрузите удостоверение личности</h3>
            <div
              className={`drop-zone ${file ? 'has-file' : ''}`}
              onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('drag-over'); }}
              onDragLeave={(e) => e.currentTarget.classList.remove('drag-over')}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove('drag-over');
                if (e.dataTransfer.files[0]) handleFileSelect(e.dataTransfer.files[0]);
              }}
            >
              {preview ? <img src={preview} alt="Удостоверение" className="file-preview" /> : (
                <>
                  <h3>Перетащите файл сюда</h3>
                  <p>JPG, JPEG, PNG или PDF</p>
                </>
              )}
              <input type="file" id="file-upload" accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf" style={{ display: 'none' }} onChange={(e) => e.target.files && handleFileSelect(e.target.files[0])} />
              <label htmlFor="file-upload" className="btn-secondary">Выбрать файл</label>
              {file && <p className="file-name">{file.name}</p>}
            </div>
            {fileError && <div className="error-banner">{fileError}</div>}
            <div className="step-actions">
              <button className="btn-primary" onClick={runOcr} disabled={!file}>Распознать данные</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="step-card">
            <h3>Распознавание</h3>
            <p className="info-text">{ocrData.message || 'Проверьте результат локального OCR.'}</p>
            {ocrData.status === 'ocr_not_configured' && <div className="error-banner">OCR требует настройки. Заполните поля вручную на следующем шаге.</div>}
            <div className="step-actions">
              <button className="btn-outline" onClick={() => setStep(1)}>Назад</button>
              <button className="btn-primary" onClick={() => setStep(3)}>К проверке данных</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="step-card">
            <h3>Результат распознавания</h3>
            <div className="form-grid">
              {ocrInput('ФИО', 'full_name')}
              {ocrInput('ИИН', 'iin')}
              {ocrInput('Дата рождения', 'birth_date')}
              {ocrInput('Номер документа', 'document_number')}
              {ocrInput('Дата выдачи', 'document_issue_date')}
              {ocrInput('Срок действия', 'document_expiry_date')}
            </div>
            {duplicateEmployee && (
              <div className="warning-banner">
                ИИН уже связан с сотрудником {duplicateEmployee.full_name} (ID {duplicateEmployee.id}, статус: {duplicateEmployee.is_deleted ? 'Архив' : duplicateEmployee.status}). Проверьте ИИН или откройте существующую карточку.
                <div className="step-actions">
                  <button className="btn-outline" onClick={() => navigate(`/employees/${duplicateEmployee.id}`)}>Открыть карточку</button>
                  {(duplicateEmployee.is_deleted || duplicateEmployee.status === 'Уволен' || duplicateEmployee.status === 'Архив') && (
                    <button className="btn-primary" onClick={() => {
                      setRehireEmployeeId(duplicateEmployee.id);
                      setDuplicateEmployee(null);
                      setStep(4);
                    }}>
                      Повторно принять этого сотрудника
                    </button>
                  )}
                </div>
              </div>
            )}
            <div className="step-actions">
              <button className="btn-outline" onClick={() => setStep(2)}>Назад</button>
              <button className="btn-primary" onClick={continueAfterIinCheck}>Подтвердить данные</button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="step-card">
            <h3>Рабочие данные</h3>
            <div className="form-grid">
              <div className="form-group"><label>Должность *</label><input value={empData.position} onChange={(e) => setEmpData({ ...empData, position: e.target.value })} /></div>
              <div className="form-group"><label>Отдел *</label><input value={empData.department} onChange={(e) => setEmpData({ ...empData, department: e.target.value })} /></div>
              <div className="form-group"><label>Оклад *</label><input type="number" value={empData.salary} onChange={(e) => setEmpData({ ...empData, salary: e.target.value })} /></div>
              <div className="form-group"><label>Дата начала работы *</label><input type="date" value={empData.start_date} onChange={(e) => setEmpData({ ...empData, start_date: e.target.value })} /></div>
              <div className="form-group"><label>Тип договора</label><input value={empData.contract_type} onChange={(e) => setEmpData({ ...empData, contract_type: e.target.value })} /></div>
              <div className="form-group"><label>График работы</label><input value={empData.work_schedule} onChange={(e) => setEmpData({ ...empData, work_schedule: e.target.value })} /></div>
              {Object.keys(errors).map((key) => <span key={key} className="error-text">{errors[key]}</span>)}
            </div>
            <div className="step-actions">
              <button className="btn-outline" onClick={() => setStep(3)}>Назад</button>
              <button className="btn-primary" onClick={() => validateEmp() && setStep(5)}>Продолжить</button>
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="step-card">
            <h3>Создание документов</h3>
            {Object.entries({ contract: 'Трудовой договор', order: 'Приказ о приёме на работу', material_responsibility: 'Договор материальной ответственности', application: 'Заявление о приёме на работу', consent: 'Согласие на обработку персональных данных' }).map(([key, label]) => (
              <label key={key} className="checkbox-row">
                <input
                  type="checkbox"
                  checked={docTypes[key]}
                  disabled={['contract', 'order', 'material_responsibility'].includes(key)}
                  onChange={(e) => setDocTypes({ ...docTypes, [key]: e.target.checked })}
                />
                {label}
              </label>
            ))}
            <div className="step-actions">
              <button className="btn-outline" onClick={() => setStep(4)}>Назад</button>
              <button className="btn-primary" onClick={() => setStep(6)}>К подтверждению</button>
            </div>
          </div>
        )}

        {step === 6 && (
          <div className="step-card">
            <h3>Подтверждение</h3>
            {createError && <div className="error-banner">{createError}</div>}
            <div className="review-card">
              <div className="review-section">
                <h4>Личные данные</h4>
                <div className="review-row"><span className="review-label">ФИО</span><span className="review-value">{ocrData.full_name}</span></div>
                <div className="review-row"><span className="review-label">ИИН</span><span className="review-value">{ocrData.iin}</span></div>
              </div>
              <div className="review-section">
                <h4>Работа</h4>
                <div className="review-row"><span className="review-label">Должность</span><span className="review-value">{empData.position}</span></div>
                <div className="review-row"><span className="review-label">Оклад</span><span className="review-value">{Number(empData.salary).toLocaleString('ru-RU')} ₸</span></div>
              </div>
            </div>
            <div className="step-actions">
              <button className="btn-outline" onClick={() => setStep(5)}>Назад</button>
              <button className="btn-primary" onClick={handleCreate}>
                {rehireEmployeeId ? 'Повторно оформить и сформировать документы' : 'Оформить и сформировать документы'}
              </button>
            </div>
          </div>
        )}

        {step === 7 && (
          <div className="step-card success-step">
            <h3>Сотрудник создан</h3>
            <div className="doc-cards">
              {generatedDocs.map((doc) => (
                <div key={doc.id} className="doc-card">
                  <div>
                    <strong>{doc.file_name}</strong>
                    <span className="status-badge">{doc.status || 'Готов'}</span>
                  </div>
                  <button className="btn-outline" onClick={() => downloadAuthorized(getDocumentDownloadUrl(doc.id), doc.file_name)}>Скачать</button>
                </div>
              ))}
            </div>
            <div className="step-actions center">
              <button className="btn-outline" onClick={() => navigate('/documents')}>К документам</button>
              <button className="btn-primary" onClick={() => navigate('/employees')}>К списку сотрудников</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
