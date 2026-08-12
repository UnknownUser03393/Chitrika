"""HTTP upload/download mapping for versioned full-data backups."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlmodel import Session

from src.chitrika.database import get_session, get_transactional_session
from src.chitrika.services.backup_service import BackupError, BackupService

router = APIRouter(tags=["export"])
MAX_BACKUP_BYTES = 100 * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024


def _read_backup_bounded(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = file.file.read(READ_CHUNK_BYTES)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_BACKUP_BYTES:
            raise HTTPException(status_code=413, detail="Backup exceeds the 100 MiB limit")
        chunks.append(chunk)


@router.get("/export/all")
def export_all(session: Session = Depends(get_session)) -> Response:
    payload = BackupService(session).export_payload()
    body = json.dumps(jsonable_encoder(payload), ensure_ascii=False, indent=2)
    exported_at = payload["exported_at"]
    filename = f"chitrika-backup-{exported_at.strftime('%Y%m%d-%H%M%S')}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore")
def restore_all(
    file: UploadFile = File(...),
    session: Session = Depends(get_transactional_session),
) -> dict:
    try:
        payload = json.loads(_read_backup_bounded(file).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="上传的不是有效的 JSON 备份文件") from exc
    try:
        return BackupService(session).restore(payload)
    except BackupError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
