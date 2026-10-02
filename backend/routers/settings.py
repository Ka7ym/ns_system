from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from config import load_app_settings, save_app_settings
from database import get_db
from deps import client_ip, require_permission
from models import User
from schemas import SettingsOut, SettingsUpdate
from services.audit_service import write_audit
from services.ocr_service import OCRService

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsOut)
def get_settings(_: User = Depends(require_permission("settings.manage"))):
    stored = load_app_settings()
    configured, message = OCRService.status()
    return SettingsOut(
        max_upload_mb=int(stored.get("max_upload_mb", 10)),
        tesseract_cmd=stored.get("tesseract_cmd") or "",
        ocr_configured=configured,
        ocr_message=message or "Локальный Tesseract доступен",
        https_ready=False,
        company_name=stored.get("company_name") or "ТОО «НС Система»",
        company_bin=stored.get("company_bin") or "",
        company_address=stored.get("company_address") or "",
        company_director=stored.get("company_director") or "",
    )


@router.put("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings.manage")),
):
    stored = save_app_settings(payload.model_dump(exclude_unset=True))
    write_audit(
        db,
        "Изменены настройки",
        user=user,
        object_type="settings",
        details=str(payload.model_dump(exclude_unset=True)),
        ip_address=client_ip(request),
    )
    db.commit()
    configured, message = OCRService.status()
    return SettingsOut(
        max_upload_mb=int(stored.get("max_upload_mb", 10)),
        tesseract_cmd=stored.get("tesseract_cmd") or "",
        ocr_configured=configured,
        ocr_message=message or "Локальный Tesseract доступен",
        https_ready=False,
        company_name=stored.get("company_name") or "ТОО «НС Система»",
        company_bin=stored.get("company_bin") or "",
        company_address=stored.get("company_address") or "",
        company_director=stored.get("company_director") or "",
    )
