from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import load_app_settings, save_app_settings
from database import get_db
from deps import require_permission
from models import User
from schemas import ReferenceSettings

router = APIRouter(prefix="/references", tags=["References"])


@router.get("", response_model=ReferenceSettings)
def get_references(_: User = Depends(require_permission("references.manage"))):
    stored = load_app_settings()
    return ReferenceSettings(
        positions=stored.get("reference_positions") or [],
        departments=stored.get("reference_departments") or [],
        contract_types=stored.get("reference_contract_types") or ["Трудовой договор", "Срочный трудовой договор"],
    )


@router.put("", response_model=ReferenceSettings)
def update_references(
    payload: ReferenceSettings,
    _: User = Depends(require_permission("references.manage")),
):
    stored = save_app_settings({
        "reference_positions": sorted(set(item.strip() for item in payload.positions if item.strip())),
        "reference_departments": sorted(set(item.strip() for item in payload.departments if item.strip())),
        "reference_contract_types": sorted(set(item.strip() for item in payload.contract_types if item.strip())),
    })
    return ReferenceSettings(
        positions=stored["reference_positions"],
        departments=stored["reference_departments"],
        contract_types=stored["reference_contract_types"],
    )
