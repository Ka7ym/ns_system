import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from database import get_db
from deps import client_ip, require_permission
from models import Employee, EmployeeAbsence, User
from schemas import EmployeeAbsenceCreate, EmployeeAbsenceOut, EmployeeAbsenceUpdate
from services.audit_service import add_audit, add_history

router = APIRouter(prefix="/absences", tags=["Absences"])
TYPE_LABELS = {
    "vacation": "Отпуск",
    "absence": "Отсутствие",
    "sick_leave": "Больничный",
}


def _validate_date_range(start_date: str, end_date: str) -> None:
    try:
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Дата должна быть в формате ГГГГ-ММ-ДД") from exc
    if end < start:
        raise HTTPException(status_code=422, detail="Дата окончания не может быть раньше даты начала")


def _serialize(record: EmployeeAbsence) -> dict:
    return {
        "id": record.id,
        "employee_id": record.employee_id,
        "employee_name": record.employee.full_name if record.employee else None,
        "type": record.type,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "note": record.note,
        "created_at": record.created_at,
        "created_by": record.created_by,
        "created_by_name": record.creator.username if record.creator else None,
    }


def _get_record(db: Session, record_id: int) -> EmployeeAbsence:
    record = (
        db.query(EmployeeAbsence)
        .options(joinedload(EmployeeAbsence.employee), joinedload(EmployeeAbsence.creator))
        .filter(EmployeeAbsence.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Запись отсутствия не найдена")
    return record


@router.get("", response_model=list[EmployeeAbsenceOut])
def list_absences(
    employee_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("absences.view")),
):
    query = (
        db.query(EmployeeAbsence)
        .options(joinedload(EmployeeAbsence.employee), joinedload(EmployeeAbsence.creator))
        .order_by(EmployeeAbsence.start_date.desc(), EmployeeAbsence.id.desc())
    )
    if employee_id:
        query = query.filter(EmployeeAbsence.employee_id == employee_id)
    return [_serialize(item) for item in query.all()]


@router.get("/employees")
def list_absence_employee_options(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("absences.manage")),
):
    employees = (
        db.query(Employee.id, Employee.full_name)
        .filter(Employee.is_deleted == False)  # noqa: E712
        .order_by(Employee.full_name.asc())
        .all()
    )
    return [{"id": employee_id, "full_name": full_name} for employee_id, full_name in employees]


@router.post("", response_model=EmployeeAbsenceOut)
def create_absence(
    payload: EmployeeAbsenceCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("absences.manage")),
):
    _validate_date_range(payload.start_date, payload.end_date)
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    record = EmployeeAbsence(
        employee_id=employee.id,
        type=payload.type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        note=payload.note,
        created_by=user.id,
    )
    db.add(record)
    db.flush()
    description = f"{TYPE_LABELS[payload.type]}: {payload.start_date} — {payload.end_date}"
    add_history(db, employee.id, "absence_recorded", description, user.id)
    add_audit(
        db,
        "Добавлена запись отсутствия",
        "absence",
        record.id,
        details=f"{employee.full_name}: {description}",
        user_id=user.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return _serialize(_get_record(db, record.id))


@router.put("/{record_id}", response_model=EmployeeAbsenceOut)
def update_absence(
    record_id: int,
    payload: EmployeeAbsenceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("absences.manage")),
):
    record = _get_record(db, record_id)
    values = payload.model_dump(exclude_unset=True)
    start_date = values.get("start_date", record.start_date)
    end_date = values.get("end_date", record.end_date)
    _validate_date_range(start_date, end_date)
    for key, value in values.items():
        setattr(record, key, value)
    description = f"{record.employee.full_name if record.employee else record.employee_id}: {TYPE_LABELS[record.type]}, {record.start_date} — {record.end_date}"
    add_history(db, record.employee_id, "absence_updated", description, user.id)
    add_audit(
        db,
        "Изменена запись отсутствия",
        "absence",
        record.id,
        details=description,
        user_id=user.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return _serialize(_get_record(db, record.id))


@router.delete("/{record_id}")
def delete_absence(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("absences.manage")),
):
    record = _get_record(db, record_id)
    description = f"{TYPE_LABELS[record.type]}: {record.start_date} — {record.end_date}"
    add_history(db, record.employee_id, "absence_deleted", description, user.id)
    add_audit(
        db,
        "Удалена запись отсутствия",
        "absence",
        record.id,
        details=description,
        user_id=user.id,
        ip_address=client_ip(request),
    )
    db.delete(record)
    db.commit()
    return {"ok": True}