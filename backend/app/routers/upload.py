from fastapi import APIRouter, File, HTTPException, UploadFile

from ..models import UploadResponse
from ..services.storage import save_uploads

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload(files: list[UploadFile] = File(...)) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="업로드된 파일이 없습니다.")
    media_ids = await save_uploads(files)
    return UploadResponse(mediaIds=media_ids)
