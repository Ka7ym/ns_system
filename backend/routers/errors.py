import os

from fastapi import APIRouter, Depends

from config import BACKEND_DIR
from deps import require_permission
from models import User

router = APIRouter(prefix="/errors", tags=["Errors"])
ERROR_LOG = os.path.join(BACKEND_DIR, "errors.log")


@router.get("")
def list_errors(_: User = Depends(require_permission("errors.view"))):
    if not os.path.exists(ERROR_LOG):
        return {"items": []}
    with open(ERROR_LOG, "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()[-200:]
    return {"items": [{"id": index, "message": line.rstrip()} for index, line in enumerate(lines, 1)]}
