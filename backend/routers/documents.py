import os
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from config import GENERATED_DIR, IDENTITY_DIR
from database import get_db
from deps import require_permission
from models import Document as DocumentModel, Employee, User
from services.audit_service import add_audit
from services.file_service import client_ip

router = APIRouter(prefix="/documents", tags=["Documents"])


def _is_managed_document_path(path: str) -> bool:
    for directory in (GENERATED_DIR, IDENTITY_DIR):
        managed_dir = os.path.realpath(directory)
        try:
            if os.path.commonpath((path, managed_dir)) == managed_dir:
                return True
        except ValueError:
            continue
    return False


@router.get("")
def list_documents(db: Session = Depends(get_db), _: User = Depends(require_permission("documents.view"))):
    docs = (
        db.query(DocumentModel)
        .options(joinedload(DocumentModel.employee))
        .order_by(DocumentModel.id.desc())
        .all()
    )
    result = []
    for doc in docs:
        user = db.query(User).filter(User.id == doc.created_by).first() if doc.created_by else None
        result.append(
            {
                "id": doc.id,
                "employee_id": doc.employee_id,
                "type": doc.type,
                "file_name": doc.file_name,
                "file_path": doc.file_path,
                "status": doc.status,
                "version": doc.version,
                "created_at": doc.created_at,
                "created_by_name": user.username if user else None,
                "employee_name": doc.employee.full_name if doc.employee else "Неизвестно",
            }
        )
    return result


@router.get("/export.xlsx")
def export_documents_xlsx(db: Session = Depends(get_db), _: User = Depends(require_permission("documents.export"))):
    from openpyxl import Workbook

    docs = db.query(DocumentModel).options(joinedload(DocumentModel.employee)).order_by(DocumentModel.id.desc()).all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Документы"
    sheet.append(["Название", "Сотрудник", "Тип", "Статус", "Версия", "Дата создания"])
    for doc in docs:
        sheet.append([
            doc.file_name, doc.employee.full_name if doc.employee else "", doc.type or "",
            doc.status or "", doc.version or "", doc.created_at or "",
        ])
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=documents.xlsx"},
    )


@router.delete("")
def clear_documents(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("documents.clear")),
):
    docs = db.query(DocumentModel).all()
    document_paths = {
        os.path.realpath(doc.file_path)
        for doc in docs
        if doc.file_path
    }
    protected_paths = {
        os.path.realpath(path)
        for (path,) in db.query(Employee.identity_file_path).filter(Employee.identity_file_path.isnot(None)).all()
    }

    try:
        for doc in docs:
            db.delete(doc)
        add_audit(
            db,
            "Очищен список документов",
            "document",
            details=f"Удалено записей: {len(docs)}",
            user_id=user.id,
            ip_address=client_ip(request),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    files_deleted = 0
    for path in document_paths - protected_paths:
        if not os.path.isfile(path):
            continue
        if not _is_managed_document_path(path):
            continue
        try:
            os.remove(path)
            files_deleted += 1
        except OSError:
            pass

    return {"deleted": len(docs), "files_deleted": files_deleted}


@router.get("/{id}/download")
def download_document(id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("documents.download"))):
    doc = db.query(DocumentModel).filter(DocumentModel.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
