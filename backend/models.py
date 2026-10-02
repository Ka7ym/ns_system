import datetime

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


EMPLOYEE_STATUS_NEW = "Новый"
EMPLOYEE_STATUS_ACTIVE = "Работает"
EMPLOYEE_STATUS_REVIEW = "На проверке"
EMPLOYEE_STATUS_TERMINATED = "Уволен"
EMPLOYEE_STATUS_ARCHIVED = "Архив"

DOCUMENT_STATUS_READY = "Готов"

ROLE_ADMIN = "Admin"
ROLE_HR = "HR"

TEMPLATE_CONTRACT = "contract"
TEMPLATE_ORDER = "order"
TEMPLATE_CONSENT = "consent"
TEMPLATE_APPLICATION = "application"
TEMPLATE_MATERIAL_RESPONSIBILITY = "material_responsibility"
TEMPLATE_TERMINATION = "termination_application"
TEMPLATE_OTHER = "other"
TEMPLATE_TYPES = (
    TEMPLATE_CONTRACT,
    TEMPLATE_ORDER,
    TEMPLATE_CONSENT,
    TEMPLATE_APPLICATION,
    TEMPLATE_MATERIAL_RESPONSIBILITY,
    TEMPLATE_TERMINATION,
    TEMPLATE_OTHER,
)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String, nullable=False, index=True)
    iin = Column(String(12), nullable=False, index=True)
    birth_date = Column(Integer)
    birth_date_full = Column(String, nullable=True)
    position = Column(String)
    salary = Column(Float)
    start_date = Column(String)
    department = Column(String)

    status = Column(String, default=EMPLOYEE_STATUS_NEW, index=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    contract_type = Column(String, nullable=True)
    work_schedule = Column(String, nullable=True)
    termination_date = Column(String, nullable=True)
    termination_reason = Column(String, nullable=True)
    document_number = Column(String, nullable=True)
    document_issue_date = Column(String, nullable=True)
    document_expiry_date = Column(String, nullable=True)
    identity_file_path = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(String, default=lambda: datetime.datetime.now().isoformat())
    updated_at = Column(
        String,
        default=lambda: datetime.datetime.now().isoformat(),
        onupdate=lambda: datetime.datetime.now().isoformat(),
    )

    documents = relationship("Document", back_populates="employee")
    history = relationship("EmployeeHistory", back_populates="employee")

    @property
    def birth_year(self):
        return self.birth_date

    @birth_year.setter
    def birth_year(self, value):
        self.birth_date = value


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    permissions = Column(Text, nullable=True)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(String, default=lambda: datetime.datetime.now().isoformat())

    role = relationship("Role", back_populates="users")


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    version = Column(String, default="v1")
    is_active = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: datetime.datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.datetime.now().isoformat())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    documents = relationship("Document", back_populates="template")
    creator = relationship("User")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    template_id = Column(Integer, ForeignKey("document_templates.id"), nullable=True)
    type = Column(String)
    file_name = Column(String)
    file_path = Column(String)
    status = Column(String, default=DOCUMENT_STATUS_READY)
    version = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.datetime.now().isoformat())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    employee = relationship("Employee", back_populates="documents")
    template = relationship("DocumentTemplate", back_populates="documents")
    creator = relationship("User")


class EmployeeHistory(Base):
    __tablename__ = "employee_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    action = Column(String, nullable=False)
    description = Column(String, nullable=True)
    field_key = Column(String, nullable=True)
    field_label = Column(String, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.datetime.now().isoformat())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    employee = relationship("Employee", back_populates="history")
    creator = relationship("User")


class EmployeeAbsence(Base):
    __tablename__ = "employee_absences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    start_date = Column(String, nullable=False, index=True)
    end_date = Column(String, nullable=False, index=True)
    note = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.datetime.now().isoformat())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    employee = relationship("Employee")
    creator = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    object_type = Column(String, nullable=True)
    object_id = Column(Integer, nullable=True)
    ip_address = Column(String, nullable=True)
    result = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.datetime.now().isoformat())

    user = relationship("User")


class Backup(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(String, default=lambda: datetime.datetime.now().isoformat())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    creator = relationship("User")
