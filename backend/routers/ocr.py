from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from deps import require_permission
from models import User
from services.audit_service import add_audit
from services.file_service import client_ip, save_identity, validate_upload
from services.ocr_service import OCRService
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.get("/status")
def ocr_status(user: User = Depends(require_permission("ocr.use"))):
    configured, message = OCRService.status()
    return {
        "configured": configured,
        "message": message or "Локальный Tesseract доступен",
        "provider": "tesseract",
    }


@router.post("")
async def process_ocr(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ocr.use")),
):
    data, filename, _ = validate_upload(file, "identity")
    saved_path = save_identity(data, filename)
    result = OCRService.process_document(data, file.content_type, file.filename)
    result["identity_file_name"] = filename
    result["identity_file_path"] = saved_path
    add_audit(
        db,
        "Загружено удостоверение",
        "ocr",
        result=result.get("status") or "ok",
        details=result.get("message") or "OCR выполнен",
        user_id=user.id,
        ip_address=client_ip(request),
    )
    db.commit()
    return result
