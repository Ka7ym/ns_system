export type EmployeeStatus = 'Новый' | 'Работает' | 'На проверке' | 'Уволен' | 'Архив';

export interface Employee {
  id: number;
  full_name: string;
  iin: string;
  birth_year?: number | null;
  birth_date_full?: string | null;
  position: string;
  salary: number;
  start_date: string;
  department?: string;
  status: EmployeeStatus;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  contract_type?: string | null;
  work_schedule?: string | null;
  termination_date?: string | null;
  termination_reason?: string | null;
  document_number?: string | null;
  document_issue_date?: string | null;
  document_expiry_date?: string | null;
  identity_file_name?: string;
  is_deleted?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface EmployeeListResponse {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
  counts: Record<string, number>;
}

export interface Document {
  id: number;
  employee_id: number;
  type: string;
  file_name: string;
  file_path: string;
  status?: string;
  version?: string;
  created_at?: string;
  created_by?: number;
  created_by_name?: string;
  employee_name?: string;
}

export interface EmployeeHistory {
  id: number;
  employee_id: number;
  action: string;
  description?: string;
  field_key?: string;
  field_label?: string;
  old_value?: string;
  new_value?: string;
  created_at?: string;
  created_by_name?: string;
}

export type AbsenceType = 'vacation' | 'absence' | 'sick_leave';

export interface EmployeeAbsence {
  id: number;
  employee_id: number;
  employee_name?: string;
  type: AbsenceType;
  start_date: string;
  end_date: string;
  note?: string | null;
  created_at?: string;
  created_by?: number;
  created_by_name?: string;
}

export interface AbsenceEmployeeOption {
  id: number;
  full_name: string;
}

export interface RoleItem {
  id: number;
  name: string;
  permissions: string[];
  is_system: boolean;
}

export type PermissionCatalog = Record<string, {
  label: string;
  permissions: Record<string, string>;
}>;

export interface OcrResult {
  full_name: string;
  iin: string;
  birth_date?: string;
  birth_year?: number | null;
  document_number?: string;
  document_issue_date?: string;
  document_expiry_date?: string;
  confidence: number;
  status?: string;
  message?: string;
  recognized?: Record<string, boolean>;
  identity_file_name?: string;
  identity_file_path?: string;
}

export interface AuthUser {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  permissions: string[];
}

export interface DocumentTemplate {
  id: number;
  name: string;
  type: string;
  description?: string;
  version: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  created_by_name?: string;
}

export interface AuditItem {
  id: number;
  user_id?: number;
  username?: string;
  action: string;
  object_type?: string;
  object_id?: number;
  result?: string;
  details?: string;
  created_at?: string;
}

export interface BackupItem {
  id: number;
  file_name: string;
  created_at?: string;
}

export interface AppSettings {
  max_upload_mb: number;
  tesseract_cmd: string;
  ocr_configured: boolean;
  ocr_message: string;
  https_ready: boolean;
  company_name: string;
  company_bin: string;
  company_address: string;
  company_director: string;
}
