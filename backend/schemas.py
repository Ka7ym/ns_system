from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from models import (
    EMPLOYEE_STATUS_ACTIVE,
    EMPLOYEE_STATUS_ARCHIVED,
    EMPLOYEE_STATUS_NEW,
    EMPLOYEE_STATUS_REVIEW,
    EMPLOYEE_STATUS_TERMINATED,
)

EMPLOYEE_STATUSES = (
    EMPLOYEE_STATUS_NEW,
    EMPLOYEE_STATUS_ACTIVE,
    EMPLOYEE_STATUS_REVIEW,
    EMPLOYEE_STATUS_TERMINATED,
    EMPLOYEE_STATUS_ARCHIVED,
)

FIELD_LABELS = {
    "full_name": "ФИО",
    "iin": "ИИН",
    "birth_date": "Год рождения",
    "birth_date_full": "Дата рождения",
    "position": "Должность",
    "salary": "Оклад",
    "start_date": "Дата приёма",
    "department": "Отдел",
    "status": "Статус",
    "phone": "Телефон",
    "email": "Email",
    "address": "Адрес",
    "contract_type": "Тип договора",
    "work_schedule": "График работы",
    "termination_date": "Дата увольнения",
    "termination_reason": "Причина увольнения",
    "document_number": "Номер документа",
    "document_issue_date": "Дата выдачи",
    "document_expiry_date": "Срок действия",
}


class EmployeeBase(BaseModel):
    full_name: str = Field(..., min_length=1)
    iin: str = Field(..., min_length=12, max_length=12, pattern=r"^\d{12}$")
    birth_year: Optional[int] = None
    birth_date_full: Optional[str] = None
    position: str = Field(..., min_length=1)
    salary: float = Field(..., gt=0)
    start_date: str
    department: Optional[str] = ""
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    contract_type: Optional[str] = None
    work_schedule: Optional[str] = None
    document_number: Optional[str] = None
    document_issue_date: Optional[str] = None
    document_expiry_date: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    status: str = EMPLOYEE_STATUS_ACTIVE
    identity_file_name: Optional[str] = None


class EmployeeRehire(EmployeeBase):
    identity_file_name: Optional[str] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    iin: Optional[str] = Field(None, min_length=12, max_length=12, pattern=r"^\d{12}$")
    birth_year: Optional[int] = None
    birth_date_full: Optional[str] = None
    position: Optional[str] = Field(None, min_length=1)
    salary: Optional[float] = Field(None, gt=0)
    start_date: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    contract_type: Optional[str] = None
    work_schedule: Optional[str] = None
    termination_date: Optional[str] = None
    termination_reason: Optional[str] = None
    document_number: Optional[str] = None
    document_issue_date: Optional[str] = None
    document_expiry_date: Optional[str] = None


class EmployeeTerminate(BaseModel):
    termination_date: str
    termination_reason: Optional[str] = None
    create_application: bool = True


class DocumentGenerateRequest(BaseModel):
    types: List[str] = Field(default_factory=lambda: ["contract", "order"])


class Employee(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    termination_date: Optional[str] = None
    termination_reason: Optional[str] = None
    is_deleted: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EmployeeListResponse(BaseModel):
    items: List[Employee]
    total: int
    page: int
    page_size: int
    counts: dict


class DocumentBase(BaseModel):
    type: str
    file_name: str
    file_path: str


class DocumentCreate(DocumentBase):
    employee_id: int


class Document(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    status: Optional[str] = None
    version: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[int] = None
    template_id: Optional[int] = None
    created_by_name: Optional[str] = None
    employee_name: Optional[str] = None


class DocumentWithEmployee(Document):
    pass


class EmployeeHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    action: str
    description: Optional[str] = None
    field_key: Optional[str] = None
    field_label: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None


class EmployeeAbsenceCreate(BaseModel):
    employee_id: int = Field(..., gt=0)
    type: str = Field(..., pattern=r"^(vacation|absence|sick_leave)$")
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: Optional[str] = Field(None, max_length=2000)


class EmployeeAbsenceUpdate(BaseModel):
    type: Optional[str] = Field(None, pattern=r"^(vacation|absence|sick_leave)$")
    start_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: Optional[str] = Field(None, max_length=2000)


class EmployeeAbsenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    type: str
    start_date: str
    end_date: str
    note: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[int] = None
    employee_name: Optional[str] = None
    created_by_name: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    permissions: List[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=80)
    permissions: Optional[List[str]] = None


class RoleOut(BaseModel):
    id: int
    name: str
    permissions: List[str]
    is_system: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    role: str
    is_active: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    role: Optional[str] = None
    is_active: Optional[bool] = None


class SettingsUpdate(BaseModel):
    max_upload_mb: Optional[int] = Field(None, ge=1, le=100)
    tesseract_cmd: Optional[str] = None
    company_name: Optional[str] = Field(None, max_length=200)
    company_bin: Optional[str] = Field(None, max_length=12, pattern=r"^$|^\d{12}$")
    company_address: Optional[str] = Field(None, max_length=500)
    company_director: Optional[str] = Field(None, max_length=200)


class SettingsOut(BaseModel):
    max_upload_mb: int
    tesseract_cmd: str
    ocr_configured: bool
    ocr_message: str
    https_ready: bool
    company_name: str
    company_bin: str
    company_address: str
    company_director: str


class ReferenceSettings(BaseModel):
    positions: List[str] = Field(default_factory=list)
    departments: List[str] = Field(default_factory=list)
    contract_types: List[str] = Field(default_factory=list)


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    description: Optional[str] = None
    version: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None


class AuditOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    object_type: Optional[str] = None
    object_id: Optional[int] = None
    result: Optional[str] = None
    details: Optional[str] = None
    created_at: Optional[str] = None


class BackupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    created_at: Optional[str] = None
    created_by: Optional[int] = None
