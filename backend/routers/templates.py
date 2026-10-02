import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from deps import require_permission
from models import DocumentTemplate, User
from schemas import TemplateOut
from services.audit_service import add_audit
from services.document_service import TYPE_LABELS
from services.file_service import client_ip, save_template, validate_upload

router = APIRouter(prefix="/templates", tags=["Templates"])


def _out(item: DocumentTemplate) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "type": item.type,
        "description": item.description,
        "version": item.version,
        "is_active": bool(item.is_active),
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "created_by": item.created_by,
        "created_by_name": item.creator.username if item.creator else None,
    }


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), user: User = Depends(require_permission("templates.view"))):
    items = db.query(DocumentTemplate).order_by(DocumentTemplate.type, DocumentTemplate.id.desc()).all()
    return [_out(item) for item in items]


@router.post("", response_model=TemplateOut)
def upload_template(
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    version: str = Form("v1"),
    description: str = Form(""),
    is_active: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("templates.manage")),
):
    if type not in TYPE_LABELS:
        raise HTTPException(status_code=422, detail="Неизвестный тип шаблона")
    data, filename, _ = validate_upload(file, "template")
    path = save_template(data, filename)
    if is_active:
        db.query(DocumentTemplate).filter(DocumentTemplate.type == type).update({"is_active": False})
    item = DocumentTemplate(
        name=name,
        type=type,
        description=description,
        file_path=path,
        version=version,
        is_active=is_active,
        created_by=user.id,
        updated_at=datetime.datetime.now().isoformat(),
    )
    db.add(item)
    add_audit(db, "Загружен шаблон", "template", details=f"{name} {version}", user_id=user.id, ip_address=client_ip(request))
    db.commit()
    db.refresh(item)
    return _out(item)


@router.post("/{id}/activate", response_model=TemplateOut)
def activate_template(id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_permission("templates.manage"))):
    item = db.query(DocumentTemplate).filter(DocumentTemplate.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    db.query(DocumentTemplate).filter(DocumentTemplate.type == item.type).update({"is_active": False})
    item.is_active = True
    item.updated_at = datetime.datetime.now().isoformat()
    add_audit(db, "Изменён шаблон", "template", item.id, details=f"Активирован {item.version}", user_id=user.id, ip_address=client_ip(request))
    db.commit()
    db.refresh(item)
    return _out(item)


@router.delete("/{id}")
def archive_template(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("templates.archive")),
):
    item = db.query(DocumentTemplate).filter(DocumentTemplate.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    if item.is_active:
        raise HTTPException(status_code=409, detail="Сначала активируйте другую версию шаблона")
    item.is_active = False
    add_audit(
        db,
        "Архивирован шаблон",
        "template",
        item.id,
        details=f"{item.name} {item.version}",
        user_id=user.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return {"ok": True}
