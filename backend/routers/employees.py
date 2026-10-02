import datetime
import csv
import io
import os
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from deps import require_permission
from models import (
    EMPLOYEE_STATUS_ACTIVE,
    EMPLOYEE_STATUS_ARCHIVED,
    EMPLOYEE_STATUS_TERMINATED,
    Document as DocumentModel,
    Employee as EmployeeModel,
    EmployeeHistory as EmployeeHistoryModel,
    User,
)
from schemas import (
    Document,
    DocumentGenerateRequest,
    Employee,
    EmployeeCreate,
    EmployeeRehire,
    EmployeeHistory,
    EmployeeListResponse,
    EmployeeTerminate,
    EmployeeUpdate,
    EMPLOYEE_STATUSES,
    FIELD_LABELS,
)
from services.audit_service import add_audit, add_history
from services.document_service import DocumentService, TEMPLATE_TERMINATION
from services.file_service import client_ip
from config import IDENTITY_DIR

router = APIRouter(prefix="/employees", tags=["Employees"])
ALLOWED_STATUSES = set(EMPLOYEE_STATUSES)
SORT_FIELDS = {
    "id": EmployeeModel.id,
    "full_name": EmployeeModel.full_name,
    "start_date": EmployeeModel.start_date,
    "status": EmployeeModel.status,
}


def _now() -> str:
    return datetime.datetime.now().isoformat()


def _user_id(user: Optional[User]) -> Optional[int]:
    return user.id if user else None


def _serialize_document(doc: DocumentModel) -> dict:
    return {
        "id": doc.id,
        "employee_id": doc.employee_id,
        "type": doc.type,
        "file_name": doc.file_name,
        "file_path": doc.file_path,
        "status": doc.status,
        "version": doc.version,
        "created_at": doc.created_at,
        "created_by": doc.created_by,
        "template_id": doc.template_id,
        "created_by_name": doc.creator.username if getattr(doc, "creator", None) else None,
        "employee_name": doc.employee.full_name if getattr(doc, "employee", None) else None,
    }


def _serialize_history(item: EmployeeHistoryModel) -> dict:
    return {
        "id": item.id,
        "employee_id": item.employee_id,
        "action": item.action,
        "description": item.description,
        "field_key": item.field_key,
        "field_label": item.field_label,
        "old_value": item.old_value,
        "new_value": item.new_value,
        "created_at": item.created_at,
        "created_by": item.created_by,
        "created_by_name": item.creator.username if getattr(item, "creator", None) else None,
    }


def _get_employee_or_404(
    db: Session,
    employee_id: int,
    include_archived: bool = False,
) -> EmployeeModel:
    query = db.query(EmployeeModel).filter(EmployeeModel.id == employee_id)
    if not include_archived:
        query = query.filter(EmployeeModel.is_deleted == False)  # noqa: E712
    employee = query.first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return employee


def _employee_payload(data: EmployeeCreate | EmployeeUpdate) -> dict:
    payload = data.model_dump(exclude_unset=True)
    if "birth_year" in payload:
        payload["birth_date"] = payload.pop("birth_year")
    birth_date_full = payload.get("birth_date_full")
    if birth_date_full:
        date_value = str(birth_date_full).strip()
        for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                payload["birth_date"] = datetime.datetime.strptime(date_value, date_format).year
                break
            except ValueError:
                continue
    return payload


def _ensure_unique_iin(db: Session, iin: str, employee_id: Optional[int] = None) -> None:
    query = db.query(EmployeeModel).filter(EmployeeModel.iin == iin)
    if employee_id is not None:
        query = query.filter(EmployeeModel.id != employee_id)
    existing = query.first()
    if existing:
        state = "в архиве" if existing.is_deleted else existing.status
        raise HTTPException(
            status_code=409,
            detail=f"ИИН уже зарегистрирован: {existing.full_name} (ID {existing.id}, статус: {state}). Проверьте распознанный ИИН или откройте существующую карточку.",
        )


def _status_counts(db: Session, search: Optional[str]) -> dict:
    base = db.query(EmployeeModel)
    if search:
        search_term = f"%{search.strip()}%"
        base = base.filter(
            or_(
                EmployeeModel.full_name.ilike(search_term),
                EmployeeModel.iin.ilike(search_term),
            )
        )
    rows = (
        base.with_entities(EmployeeModel.status, EmployeeModel.is_deleted, func.count(EmployeeModel.id))
        .group_by(EmployeeModel.status, EmployeeModel.is_deleted)
        .all()
    )
    counts = {
        "Все": 0,
        "Новый": 0,
        "Работает": 0,
        "На проверке": 0,
        "Уволен": 0,
        "Архив": 0,
    }
    for status, is_deleted, count in rows:
        if is_deleted:
            counts["Архив"] += count
        else:
            counts["Все"] += count
            if status in counts:
                counts[status] += count
    return counts


@router.post("", response_model=Employee)
def create_employee(
    employee: EmployeeCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.create")),
):
    payload = _employee_payload(employee)
    identity_file_name = payload.pop("identity_file_name", None)
    status = payload.get("status")
    if status and status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail="Неизвестный статус сотрудника")
    _ensure_unique_iin(db, payload["iin"])

    db_emp = EmployeeModel(**payload)
    db.add(db_emp)
    db.flush()
    if identity_file_name:
        identity_path = os.path.join(IDENTITY_DIR, os.path.basename(identity_file_name))
        if os.path.exists(identity_path):
            db_emp.identity_file_path = identity_path
            db.add(
                DocumentModel(
                    employee_id=db_emp.id,
                    type="identity",
                    file_name="Удостоверение личности" + os.path.splitext(identity_file_name)[1],
                    file_path=identity_path,
                    status="Сохранён",
                    created_by=_user_id(user),
                )
            )
    add_history(db, db_emp.id, "created", "Сотрудник создан", _user_id(user))
    add_audit(
        db,
        "Создан сотрудник",
        "employee",
        db_emp.id,
        details=db_emp.full_name,
        user_id=_user_id(user),
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(db_emp)
    return db_emp


@router.post("/{id}/rehire", response_model=Employee)
def rehire_employee(
    id: int,
    employee: EmployeeRehire,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.create")),
):
    db_emp = _get_employee_or_404(db, id, include_archived=True)
    if not db_emp.is_deleted and db_emp.status != EMPLOYEE_STATUS_TERMINATED:
        raise HTTPException(status_code=409, detail="Повторный приём доступен только для уволенного или архивного сотрудника")

    payload = _employee_payload(employee)
    identity_file_name = payload.pop("identity_file_name", None)
    _ensure_unique_iin(db, payload["iin"], employee_id=id)
    for key, value in payload.items():
        setattr(db_emp, key, value)
    db_emp.is_deleted = False
    db_emp.status = EMPLOYEE_STATUS_ACTIVE
    db_emp.termination_date = None
    db_emp.termination_reason = None
    db_emp.updated_at = _now()
    db.flush()

    if identity_file_name:
        identity_path = os.path.join(IDENTITY_DIR, os.path.basename(identity_file_name))
        if os.path.exists(identity_path):
            db_emp.identity_file_path = identity_path
            db.add(
                DocumentModel(
                    employee_id=db_emp.id,
                    type="identity",
                    file_name="Удостоверение личности" + os.path.splitext(identity_file_name)[1],
                    file_path=identity_path,
                    status="Сохранён",
                    created_by=_user_id(user),
                )
            )

    add_history(
        db,
        db_emp.id,
        "rehired",
        f"Сотрудник повторно принят на работу с {db_emp.start_date}",
        _user_id(user),
    )
    add_audit(
        db,
        "Повторно принят сотрудник",
        "employee",
        db_emp.id,
        details=db_emp.full_name,
        user_id=_user_id(user),
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(db_emp)
    return db_emp


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    search: Optional[str] = None,
    department: Optional[str] = None,
    position: Optional[str] = None,
    status: Optional[str] = None,
    include_archived: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("id"),
    order: str = Query("desc"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.view")),
):
    query = db.query(EmployeeModel)
    if status == "Архив" or include_archived and status == "Архив":
        query = query.filter(EmployeeModel.is_deleted == True)  # noqa: E712
    elif not include_archived:
        query = query.filter(EmployeeModel.is_deleted == False)  # noqa: E712

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                EmployeeModel.full_name.ilike(search_term),
                EmployeeModel.iin.ilike(search_term),
            )
        )

    if department:
        query = query.filter(EmployeeModel.department.ilike(f"%{department.strip()}%"))
    if position:
        query = query.filter(EmployeeModel.position.ilike(f"%{position.strip()}%"))

    if status and status not in ("Все", "Архив"):
        query = query.filter(EmployeeModel.status == status)

    total = query.count()
    sort_col = SORT_FIELDS.get(sort, EmployeeModel.id)
    query = query.order_by(sort_col.asc() if order == "asc" else sort_col.desc())
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "counts": _status_counts(db, search),
    }


@router.get("/export.csv")
def export_employees(
    search: Optional[str] = None,
    department: Optional[str] = None,
    position: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.export")),
):
    query = db.query(EmployeeModel).filter(EmployeeModel.is_deleted == False)  # noqa: E712
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(EmployeeModel.full_name.ilike(term), EmployeeModel.iin.ilike(term)))
    if department:
        query = query.filter(EmployeeModel.department.ilike(f"%{department.strip()}%"))
    if position:
        query = query.filter(EmployeeModel.position.ilike(f"%{position.strip()}%"))
    if status and status != "Все":
        query = query.filter(EmployeeModel.status == status)

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["ФИО", "ИИН", "Должность", "Подразделение", "Оклад", "Дата приёма", "Статус"])
    for employee in query.order_by(EmployeeModel.full_name.asc()).all():
        writer.writerow([
            employee.full_name,
            employee.iin,
            employee.position or "",
            employee.department or "",
            employee.salary or "",
            employee.start_date or "",
            employee.status or "",
        ])
    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@router.get("/export.xlsx")
def export_employees_xlsx(
    search: Optional[str] = None,
    department: Optional[str] = None,
    position: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.export")),
):
    from openpyxl import Workbook

    query = db.query(EmployeeModel).filter(EmployeeModel.is_deleted == False)  # noqa: E712
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(EmployeeModel.full_name.ilike(term), EmployeeModel.iin.ilike(term)))
    if department:
        query = query.filter(EmployeeModel.department.ilike(f"%{department.strip()}%"))
    if position:
        query = query.filter(EmployeeModel.position.ilike(f"%{position.strip()}%"))
    if status and status != "Все":
        query = query.filter(EmployeeModel.status == status)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Сотрудники"
    sheet.append(["ФИО", "ИИН", "Должность", "Подразделение", "Оклад", "Дата приёма", "Статус"])
    for employee in query.order_by(EmployeeModel.full_name.asc()).all():
        sheet.append([
            employee.full_name, employee.iin, employee.position or "", employee.department or "",
            employee.salary or "", employee.start_date or "", employee.status or "",
        ])
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=employees.xlsx"},
    )


@router.get("/stats")
def employee_stats(db: Session = Depends(get_db), user: User = Depends(require_permission("dashboard.view"))):
    today = datetime.date.today()
    expiry_limit = today + datetime.timedelta(days=30)
    expiring_count = 0
    for employee in db.query(EmployeeModel).filter(
        EmployeeModel.is_deleted == False,  # noqa: E712
        EmployeeModel.document_expiry_date.isnot(None),
    ).all():
        try:
            expiry = datetime.date.fromisoformat(employee.document_expiry_date[:10])
        except (TypeError, ValueError):
            continue
        if expiry <= expiry_limit:
            expiring_count += 1
    active = EmployeeModel.is_deleted == False  # noqa: E712
    history = (
        db.query(EmployeeHistoryModel, EmployeeModel.full_name)
        .join(EmployeeModel, EmployeeHistoryModel.employee_id == EmployeeModel.id)
        .order_by(EmployeeHistoryModel.id.desc())
        .limit(8)
        .all()
    )
    return {
        "employees": db.query(func.count(EmployeeModel.id)).filter(active).scalar() or 0,
        "new": db.query(func.count(EmployeeModel.id)).filter(active, EmployeeModel.status == "Новый").scalar() or 0,
        "review": db.query(func.count(EmployeeModel.id)).filter(active, EmployeeModel.status == "На проверке").scalar() or 0,
        "terminated": db.query(func.count(EmployeeModel.id)).filter(active, EmployeeModel.status == EMPLOYEE_STATUS_TERMINATED).scalar() or 0,
        "documents": db.query(func.count(DocumentModel.id)).scalar() or 0,
        "expiring_documents": expiring_count,
        "recent_actions": [
            {
                "id": item.id,
                "employee_name": full_name,
                "action": item.action,
                "description": item.description,
                "created_at": item.created_at,
            }
            for item, full_name in history
        ],
    }


@router.get("/check-iin")
def check_employee_iin(iin: str = Query(..., min_length=12, max_length=12, pattern=r"^\d{12}$"), db: Session = Depends(get_db), user: User = Depends(require_permission("employees.create"))):
    employee = db.query(EmployeeModel).filter(EmployeeModel.iin == iin).first()
    return {
        "exists": employee is not None,
        "employee": {
            "id": employee.id,
            "full_name": employee.full_name,
            "status": EMPLOYEE_STATUS_ARCHIVED if employee.is_deleted else employee.status,
            "is_deleted": bool(employee.is_deleted),
        } if employee else None,
    }


@router.get("/{id}", response_model=Employee)
def get_employee(
    id: int,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.view")),
):
    return _get_employee_or_404(db, id, include_archived=include_archived)


@router.put("/{id}", response_model=Employee)
def update_employee(
    id: int,
    employee: EmployeeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.edit")),
):
    db_emp = _get_employee_or_404(db, id, include_archived=True)
    payload = _employee_payload(employee)
    status = payload.get("status")
    if status and status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail="Неизвестный статус сотрудника")
    if "iin" in payload:
        _ensure_unique_iin(db, payload["iin"], employee_id=id)
    if db_emp.is_deleted and status != EMPLOYEE_STATUS_ARCHIVED:
        raise HTTPException(status_code=409, detail="Архивного сотрудника сначала нужно восстановить")

    diffs = []
    for key, value in payload.items():
        old = getattr(db_emp, key)
        if old != value:
            label = FIELD_LABELS.get(key, key)
            diffs.append(f"{label}: {old or '—'} → {value or '—'}")
            db.add(
                EmployeeHistoryModel(
                    employee_id=db_emp.id,
                    action="updated",
                    description=f"{label}: {old or '—'} → {value or '—'}",
                    field_key=key,
                    field_label=label,
                    old_value="" if old is None else str(old),
                    new_value="" if value is None else str(value),
                    created_by=_user_id(user),
                )
            )
        setattr(db_emp, key, value)
    db_emp.updated_at = _now()
    if diffs:
        description = "; ".join(diffs)
        add_audit(
            db,
            "Изменён сотрудник",
            "employee",
            db_emp.id,
            details=description,
            user_id=_user_id(user),
            ip_address=client_ip(request),
        )
    db.commit()
    db.refresh(db_emp)
    return db_emp


@router.delete("/{id}", response_model=Employee)
def archive_employee(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.archive")),
):
    db_emp = _get_employee_or_404(db, id, include_archived=True)
    if db_emp.is_deleted:
        raise HTTPException(status_code=409, detail="Сотрудник уже находится в архиве")
    db_emp.is_deleted = True
    db_emp.status = EMPLOYEE_STATUS_ARCHIVED
    db_emp.updated_at = _now()
    add_history(db, db_emp.id, "archived", "Сотрудник перенесен в архив", _user_id(user))
    add_audit(
        db,
        "Удалён сотрудник",
        "employee",
        db_emp.id,
        details="Архивирование",
        user_id=_user_id(user),
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(db_emp)
    return db_emp


@router.post("/{id}/restore", response_model=Employee)
def restore_employee(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.archive")),
):
    db_emp = _get_employee_or_404(db, id, include_archived=True)
    if not db_emp.is_deleted:
        raise HTTPException(status_code=409, detail="Сотрудник уже активен")
    db_emp.is_deleted = False
    db_emp.status = "Новый"
    db_emp.updated_at = _now()
    add_history(db, db_emp.id, "restored", "Сотрудник восстановлен из архива", _user_id(user))
    add_audit(db, "Изменён сотрудник", "employee", db_emp.id, details="Восстановление из архива", user_id=_user_id(user), ip_address=client_ip(request))
    db.commit()
    db.refresh(db_emp)
    return db_emp


@router.post("/{id}/terminate", response_model=Employee)
def terminate_employee(
    id: int,
    payload: EmployeeTerminate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employees.archive")),
):
    db_emp = _get_employee_or_404(db, id, include_archived=True)
    if db_emp.is_deleted:
        raise HTTPException(status_code=409, detail="Архивного сотрудника нельзя уволить")
    if db_emp.status == EMPLOYEE_STATUS_TERMINATED:
        raise HTTPException(status_code=409, detail="Сотрудник уже уволен")
    db_emp.status = EMPLOYEE_STATUS_TERMINATED
    db_emp.termination_date = payload.termination_date
    db_emp.termination_reason = payload.termination_reason
    db_emp.updated_at = _now()
    add_history(
        db,
        db_emp.id,
        "terminated",
        f"Увольнение: {payload.termination_date}. {payload.termination_reason or ''}".strip(),
        _user_id(user),
    )
    if payload.create_application:
        try:
            DocumentService.generate_documents(
                db,
                db_emp,
                types=[TEMPLATE_TERMINATION],
                user_id=_user_id(user),
                require_templates=True,
            )
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    add_audit(
        db,
        "Оформлено увольнение",
        "employee",
        db_emp.id,
        details=payload.termination_reason,
        user_id=_user_id(user),
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(db_emp)
    return db_emp


@router.get("/{id}/documents", response_model=List[Document])
def list_employee_documents(id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("documents.view"))):
    _get_employee_or_404(db, id, include_archived=True)
    docs = (
        db.query(DocumentModel)
        .filter(DocumentModel.employee_id == id)
        .order_by(DocumentModel.id.desc())
        .all()
    )
    return [_serialize_document(doc) for doc in docs]


@router.post("/{id}/documents", response_model=List[Document])
def generate_documents(
    id: int,
    payload: DocumentGenerateRequest = Body(default_factory=DocumentGenerateRequest),
    request: Request = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents.generate")),
):
    db_emp = _get_employee_or_404(db, id, include_archived=True)
    types = payload.types if payload else ["contract", "order"]
    try:
        docs = DocumentService.generate_documents(db, db_emp, types=types, user_id=_user_id(user), require_templates=True)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    add_history(db, db_emp.id, "documents_generated", "Сформированы кадровые документы", _user_id(user))
    add_audit(db, "Создан документ", "employee", db_emp.id, details=", ".join(types), user_id=_user_id(user), ip_address=client_ip(request))
    db.commit()
    return [_serialize_document(doc) for doc in docs]


@router.get("/{id}/history", response_model=List[EmployeeHistory])
def list_employee_history(id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("employees.view"))):
    _get_employee_or_404(db, id, include_archived=True)
    items = (
        db.query(EmployeeHistoryModel)
        .filter(EmployeeHistoryModel.employee_id == id)
        .order_by(EmployeeHistoryModel.id.desc())
        .all()
    )
    return [_serialize_history(item) for item in items]
