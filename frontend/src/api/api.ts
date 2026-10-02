import {
  AuditItem,
  AbsenceEmployeeOption,
  AbsenceType,
  AppSettings,
  AuthUser,
  BackupItem,
  Document,
  DocumentTemplate,
  Employee,
  EmployeeAbsence,
  EmployeeHistory,
  EmployeeListResponse,
  EmployeeStatus,
  OcrResult,
  PermissionCatalog,
  RoleItem,
} from '../types';

const API_BASE_URL = 'http://localhost:8000';
const TOKEN_KEY = 'ns_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail || data.message || 'Не удалось выполнить операцию.';
  } catch {
    return 'Не удалось выполнить операцию.';
  }
}

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init?.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(url, { ...init, headers });
  if (response.status === 401) {
    setToken(null);
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
  }
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function login(username: string, password: string): Promise<{ access_token: string; user: AuthUser }> {
  return request(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function getMe(): Promise<AuthUser> {
  return request(`${API_BASE_URL}/api/auth/me`);
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await request(`${API_BASE_URL}/api/auth/change-password`, {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export interface DashboardStats {
  employees: number;
  new: number;
  review: number;
  terminated: number;
  documents: number;
  expiring_documents: number;
  recent_actions: Array<{
    id: number;
    employee_name: string;
    action: string;
    description?: string;
    created_at?: string;
  }>;
}

export async function recognizeDocument(file: File): Promise<OcrResult> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await request<{
    status?: string;
    message?: string;
    fields?: Record<string, { value?: string | number | null; recognized?: boolean }>;
    raw_text?: string;
    identity_file_name?: string;
    identity_file_path?: string;
  }>(`${API_BASE_URL}/api/ocr`, { method: 'POST', body: formData });
  const fields = response.fields || {};
  const value = (key: string) => fields[key]?.value ?? '';
  const birthDate = String(value('birth_date') || '');
  const birthYear = birthDate.match(/(?:^|\D)(19\d{2}|20\d{2})(?:\D|$)/)?.[1];
  return {
    full_name: String(value('full_name')),
    iin: String(value('iin')),
    birth_date: birthDate,
    birth_year: birthYear ? Number(birthYear) : undefined,
    document_number: String(value('document_number') || ''),
    document_issue_date: String(value('document_issue_date') || ''),
    document_expiry_date: String(value('document_expiry_date') || ''),
    confidence: 0,
    status: response.status,
    message: response.message,
    recognized: Object.fromEntries(
      Object.entries(fields).map(([key, field]) => [key, Boolean(field.recognized)]),
    ),
    identity_file_name: response.identity_file_name,
    identity_file_path: response.identity_file_path,
  };
}

export async function getOcrStatus() {
  return request<{ configured: boolean; message: string; provider: string }>(`${API_BASE_URL}/api/ocr/status`);
}

export async function createEmployee(data: Partial<Employee>): Promise<Employee> {
  return request<Employee>(`${API_BASE_URL}/api/employees`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function rehireEmployee(id: number, data: Partial<Employee>): Promise<Employee> {
  return request<Employee>(`${API_BASE_URL}/api/employees/${id}/rehire`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export interface ExistingEmployeeMatch {
  id: number;
  full_name: string;
  status: EmployeeStatus;
  is_deleted: boolean;
}

export async function checkEmployeeIin(iin: string): Promise<{ exists: boolean; employee: ExistingEmployeeMatch | null }> {
  const query = new URLSearchParams({ iin });
  return request(`${API_BASE_URL}/api/employees/check-iin?${query.toString()}`);
}

export async function getEmployees(params?: {
  search?: string;
  department?: string;
  position?: string;
  status?: EmployeeStatus | 'Все';
  page?: number;
  pageSize?: number;
  includeArchived?: boolean;
  sort?: string;
  order?: 'asc' | 'desc';
}): Promise<EmployeeListResponse> {
  const query = new URLSearchParams();
  if (params?.search) query.set('search', params.search);
  if (params?.department) query.set('department', params.department);
  if (params?.position) query.set('position', params.position);
  if (params?.status && params.status !== 'Все') query.set('status', params.status);
  if (params?.page) query.set('page', String(params.page));
  if (params?.pageSize) query.set('page_size', String(params.pageSize));
  if (params?.includeArchived || params?.status === 'Архив') query.set('include_archived', 'true');
  if (params?.sort) query.set('sort', params.sort);
  if (params?.order) query.set('order', params.order);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request<EmployeeListResponse>(`${API_BASE_URL}/api/employees${suffix}`);
}

export function getEmployeesExportUrl(params?: { search?: string; department?: string; position?: string; status?: EmployeeStatus | 'Все' }): string {
  const query = new URLSearchParams();
  if (params?.search) query.set('search', params.search);
  if (params?.department) query.set('department', params.department);
  if (params?.position) query.set('position', params.position);
  if (params?.status && params.status !== 'Все') query.set('status', params.status);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return `${API_BASE_URL}/api/employees/export.csv${suffix}`;
}

export function getEmployeesExcelUrl(): string {
  return `${API_BASE_URL}/api/employees/export.xlsx`;
}

export function getDocumentsExcelUrl(): string {
  return `${API_BASE_URL}/api/documents/export.xlsx`;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>(`${API_BASE_URL}/api/employees/stats`);
}

export async function getEmployee(id: number): Promise<Employee> {
  return request<Employee>(`${API_BASE_URL}/api/employees/${id}?include_archived=true`);
}

export async function updateEmployee(id: number, data: Partial<Employee>): Promise<Employee> {
  return request<Employee>(`${API_BASE_URL}/api/employees/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function archiveEmployee(id: number): Promise<Employee> {
  return request<Employee>(`${API_BASE_URL}/api/employees/${id}`, { method: 'DELETE' });
}

export async function restoreEmployee(id: number): Promise<Employee> {
  return request<Employee>(`${API_BASE_URL}/api/employees/${id}/restore`, { method: 'POST' });
}

export async function terminateEmployee(
  id: number,
  data: { termination_date: string; termination_reason?: string; create_application?: boolean },
): Promise<Employee> {
  return request<Employee>(`${API_BASE_URL}/api/employees/${id}/terminate`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function generateDocuments(employeeId: number, types?: string[]): Promise<Document[]> {
  return request<Document[]>(`${API_BASE_URL}/api/employees/${employeeId}/documents`, {
    method: 'POST',
    body: JSON.stringify({ types: types || ['contract', 'order'] }),
  });
}

export async function getEmployeeDocuments(employeeId: number): Promise<Document[]> {
  return request<Document[]>(`${API_BASE_URL}/api/employees/${employeeId}/documents`);
}

export async function getEmployeeHistory(employeeId: number): Promise<EmployeeHistory[]> {
  return request<EmployeeHistory[]>(`${API_BASE_URL}/api/employees/${employeeId}/history`);
}

export async function getDocuments(): Promise<Document[]> {
  return request<Document[]>(`${API_BASE_URL}/api/documents`);
}

export async function clearDocuments(): Promise<{ deleted: number; files_deleted: number }> {
  return request(`${API_BASE_URL}/api/documents`, { method: 'DELETE' });
}

export function getDocumentDownloadUrl(id: number): string {
  return `${API_BASE_URL}/api/documents/${id}/download`;
}

export async function downloadAuthorized(url: string, filename: string) {
  const token = getToken();
  const response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) throw new Error('Не удалось скачать файл');
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
}

export async function getTemplates(): Promise<DocumentTemplate[]> {
  return request(`${API_BASE_URL}/api/templates`);
}

export async function uploadTemplate(form: FormData): Promise<DocumentTemplate> {
  return request(`${API_BASE_URL}/api/templates`, { method: 'POST', body: form });
}

export async function activateTemplate(id: number): Promise<DocumentTemplate> {
  return request(`${API_BASE_URL}/api/templates/${id}/activate`, { method: 'POST' });
}

export async function archiveTemplate(id: number): Promise<void> {
  await request(`${API_BASE_URL}/api/templates/${id}`, { method: 'DELETE' });
}

export async function getUsers(): Promise<AuthUser[]> {
  return request(`${API_BASE_URL}/api/users`);
}

export async function createUser(data: { username: string; password: string; role: string; is_active?: boolean }): Promise<AuthUser> {
  return request(`${API_BASE_URL}/api/users`, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateUser(id: number, data: Partial<{ username: string; password: string; role: string; is_active: boolean }>): Promise<AuthUser> {
  return request(`${API_BASE_URL}/api/users/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export async function deleteUser(id: number): Promise<void> {
  await request(`${API_BASE_URL}/api/users/${id}`, { method: 'DELETE' });
}

export async function getRoles(): Promise<RoleItem[]> {
  return request(`${API_BASE_URL}/api/users/roles`);
}

export async function getAssignableRoles(): Promise<RoleItem[]> {
  return request(`${API_BASE_URL}/api/users/assignable-roles`);
}

export async function getPermissionCatalog(): Promise<PermissionCatalog> {
  return request(`${API_BASE_URL}/api/users/permission-catalog`);
}

export async function createRole(data: { name: string; permissions: string[] }): Promise<RoleItem> {
  return request(`${API_BASE_URL}/api/users/roles`, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateRole(id: number, data: { name?: string; permissions?: string[] }): Promise<RoleItem> {
  return request(`${API_BASE_URL}/api/users/roles/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export async function deleteRole(id: number): Promise<void> {
  await request(`${API_BASE_URL}/api/users/roles/${id}`, { method: 'DELETE' });
}

export async function getAbsences(employeeId?: number): Promise<EmployeeAbsence[]> {
  const query = employeeId ? `?employee_id=${employeeId}` : '';
  return request(`${API_BASE_URL}/api/absences${query}`);
}

export async function getAbsenceEmployeeOptions(): Promise<AbsenceEmployeeOption[]> {
  return request(`${API_BASE_URL}/api/absences/employees`);
}

export async function createAbsence(data: {
  employee_id: number;
  type: AbsenceType;
  start_date: string;
  end_date: string;
  note?: string;
}): Promise<EmployeeAbsence> {
  return request(`${API_BASE_URL}/api/absences`, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateAbsence(id: number, data: Partial<{
  type: AbsenceType;
  start_date: string;
  end_date: string;
  note: string;
}>): Promise<EmployeeAbsence> {
  return request(`${API_BASE_URL}/api/absences/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export async function deleteAbsence(id: number): Promise<void> {
  await request(`${API_BASE_URL}/api/absences/${id}`, { method: 'DELETE' });
}

export async function getAudit(): Promise<AuditItem[]> {
  const response = await request<{ items: AuditItem[] }>(`${API_BASE_URL}/api/audit`);
  return response.items || [];
}

export async function getSettings(): Promise<AppSettings> {
  return request<AppSettings>(`${API_BASE_URL}/api/settings`);
}

export interface ReferenceSettings {
  positions: string[];
  departments: string[];
  contract_types: string[];
}

export async function getReferences(): Promise<ReferenceSettings> {
  return request(`${API_BASE_URL}/api/references`);
}

export async function updateReferences(data: ReferenceSettings): Promise<ReferenceSettings> {
  return request(`${API_BASE_URL}/api/references`, { method: 'PUT', body: JSON.stringify(data) });
}

export async function getErrors(): Promise<Array<{ id: number; message: string }>> {
  const response = await request<{ items: Array<{ id: number; message: string }> }>(`${API_BASE_URL}/api/errors`);
  return response.items || [];
}

export async function updateSettings(data: {
  max_upload_mb: number;
  tesseract_cmd: string;
  company_name: string;
  company_bin: string;
  company_address: string;
  company_director: string;
}): Promise<AppSettings> {
  return request<AppSettings>(`${API_BASE_URL}/api/settings`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function getBackups(): Promise<BackupItem[]> {
  return request(`${API_BASE_URL}/api/backups`);
}

export async function createBackup(): Promise<BackupItem> {
  return request(`${API_BASE_URL}/api/backups`, { method: 'POST' });
}

export function getBackupDownloadUrl(id: number): string {
  return `${API_BASE_URL}/api/backups/${id}/download`;
}
