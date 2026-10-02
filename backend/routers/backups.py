import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from deps import client_ip, require_permission
from models import Backup, User
from schemas import BackupOut
from services.audit_service import write_audit
from services.backup_service import create_backup

router = APIRouter(prefix="/backups", tags=["Backups"])


@router.get("", response_model=list[BackupOut])
def list_backups(db: Session = Depends(get_db), _: User = Depends(require_permission("settings.manage"))):
    return db.query(Backup).order_by(Backup.id.desc()).all()


@router.post("", response_model=BackupOut)
def make_backup(request: Request, db: Session = Depends(get_db), user: User = Depends(require_permission("settings.manage"))):
    record = create_backup(db, user)
    write_audit(
        db,
        "Создан backup",
        user=user,
        object_type="backup",
        object_id=record.id,
        details=record.file_name,
        ip_address=client_ip(request),
    )
    db.commit()
    return record


@router.get("/{backup_id}/download")
def download_backup(backup_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("settings.manage"))):
    record = db.query(Backup).filter(Backup.id == backup_id).first()
    if not record or not os.path.exists(record.file_path):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Резервная копия не найдена")
    return FileResponse(record.file_path, filename=record.file_name, media_type="application/zip")
