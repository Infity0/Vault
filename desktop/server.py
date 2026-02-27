from __future__ import annotations

import argparse
import base64
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.crypto import CryptoError, CryptoManager
from src.core.db_base import BaseDatabase
from src.core.db_mysql import MySQLConfig, MySQLDatabase
from src.core.models import CATEGORIES, Record, RecordData



SECRET_KEY: str = secrets.token_hex(32)
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24




def _build_database() -> BaseDatabase:
    cfg = MySQLConfig(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "vault_user"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "vault_db"),
        ssl_ca=os.environ.get("MYSQL_SSL_CA", ""),
    )
    print(f"[DB] Используется MySQL: {cfg.safe_str()}")
    return MySQLDatabase(cfg)


_db_lock = threading.Lock()
_db: BaseDatabase = _build_database()



_sessions: dict[str, dict] = {}
_sessions_lock = threading.Lock()


def _session_cleanup_worker() -> None:
    while True:
        time.sleep(3600)
        now = datetime.now(timezone.utc)
        with _sessions_lock:
            expired = [
                sid for sid, s in _sessions.items()
                if s.get("expires_at", now) <= now
            ]
            for sid in expired:
                sess = _sessions.pop(sid, None)
                if sess:
                    sess["crypto"].lock()


threading.Thread(
    target=_session_cleanup_worker, daemon=True, name="session-cleanup"
).start()



app = FastAPI(
    title="Vault API",
    description="REST API для безопасного хранилища документов Vault",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()



class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class CategoryFieldInfo(BaseModel):
    label: str
    key: str
    secret: bool


class CategoryInfo(BaseModel):
    key: str
    label: str
    icon: str
    color: str
    has_expiry: bool
    fields: list[CategoryFieldInfo]


class RecordListItem(BaseModel):
    id: int
    title: str
    category: str
    icon: str
    color: str
    is_favorite: bool
    expiry_date: Optional[str]
    created_at: str
    updated_at: str


class RecordDetail(RecordListItem):
    fields: dict[str, str]
    notes: str
    custom_fields: list[list[str]]


class SaveRecordRequest(BaseModel):
    title: str
    category: str
    is_favorite: bool = False
    expiry_date: Optional[str] = None
    fields: dict[str, str] = {}
    notes: str = ""
    custom_fields: list[list[str]] = []


class AttachmentInfo(BaseModel):
    id: int
    record_id: int
    filename: str
    mimetype: str
    size: int
    created_at: str



def _create_token(session_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": session_id, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _get_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        session_id: str = payload.get("sub", "")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или просроченный токен",
        )
    with _sessions_lock:
        session = _sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия истекла — войдите заново",
        )
    return session


def _record_to_list_item(r: Record) -> RecordListItem:
    return RecordListItem(
        id=r.id,
        title=r.title,
        category=r.category,
        icon=r.icon,
        color=r.color,
        is_favorite=r.is_favorite,
        expiry_date=r.expiry_date,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _get_record_or_404(record_id: int, account_id: int) -> Record:
    with _db_lock:
        record = _db.get_record_by_id(record_id)
    if not record or record.account_id != account_id:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return record



@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/categories", response_model=list[CategoryInfo], tags=["system"])
def get_categories():
    return [
        CategoryInfo(
            key=key,
            label=info["label"],
            icon=info["icon"],
            color=info["color"],
            has_expiry=info.get("has_expiry", True),
            fields=[
                CategoryFieldInfo(label=f[0], key=f[1], secret=f[2])
                for f in info["fields"]
            ],
        )
        for key, info in CATEGORIES.items()
    ]



@app.post("/auth/register", status_code=201, tags=["auth"])
def register(req: RegisterRequest):
    if not req.username.strip():
        raise HTTPException(status_code=400, detail="Имя пользователя не может быть пустым")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Пароль слишком короткий (минимум 4 символа)")

    with _db_lock:
        existing = _db.get_account(req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Пользователь уже существует")

    salt = CryptoManager.generate_salt()
    crypto = CryptoManager()
    crypto.unlock(req.password, salt)
    canary = crypto.make_canary()
    crypto.lock()

    with _db_lock:
        _db.create_account(req.username, base64.b64encode(salt).decode(), canary)

    return {"message": "Аккаунт создан"}


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(req: LoginRequest):
    with _db_lock:
        info = _db.get_account(req.username)

    if not info:
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    salt = base64.b64decode(info["salt"])
    crypto = CryptoManager()
    crypto.unlock(req.password, salt)

    if not crypto.verify_canary(info["canary"]):
        crypto.lock()
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    session_id = secrets.token_hex(32)
    with _sessions_lock:
        _sessions[session_id] = {
            "id": session_id,
            "account_id": info["id"],
            "username": req.username,
            "crypto": crypto,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
        }

    return TokenResponse(
        access_token=_create_token(session_id),
        username=req.username,
    )


@app.post("/auth/logout", tags=["auth"])
def logout(session: dict = Depends(_get_session)):
    with _sessions_lock:
        sess = _sessions.pop(session["id"], None)
    if sess:
        sess["crypto"].lock()
    return {"message": "Выход выполнен"}



@app.get("/records", response_model=list[RecordListItem], tags=["records"])
def list_records(
    category: Optional[str] = None,
    favorites: bool = False,
    session: dict = Depends(_get_session),
):
    from datetime import date, datetime
    account_id = session["account_id"]
    with _db_lock:
        if favorites:
            records = [r for r in _db.get_all_records(account_id) if r.is_favorite]
        elif category == "expiring":
            today = date.today()
            result = []
            for r in _db.get_all_records(account_id):
                if not r.expiry_date:
                    continue
                try:
                    exp = datetime.strptime(r.expiry_date, "%Y-%m-%d").date()
                    if (exp - today).days <= 30:
                        result.append(r)
                except ValueError:
                    pass
            records = result
        elif category and category != "all":
            records = _db.get_records_by_category(category, account_id)
        else:
            records = _db.get_all_records(account_id)

    return [_record_to_list_item(r) for r in records]


@app.get("/records/search", response_model=list[RecordListItem], tags=["records"])
def search_records(q: str, session: dict = Depends(_get_session)):
    crypto: CryptoManager = session["crypto"]
    query_lower = q.lower()
    results: list[Record] = []

    with _db_lock:
        all_records = _db.get_all_records(session["account_id"])

    for r in all_records:
        if query_lower in r.title.lower():
            results.append(r)
            continue
        try:
            data = RecordData.from_json(crypto.decrypt(r.encrypted_data))
            combined = " ".join(data.fields.values()) + data.notes
            if query_lower in combined.lower():
                results.append(r)
        except CryptoError:
            pass

    return [_record_to_list_item(r) for r in results]


@app.get("/records/{record_id}", response_model=RecordDetail, tags=["records"])
def get_record(record_id: int, session: dict = Depends(_get_session)):
    crypto: CryptoManager = session["crypto"]
    record = _get_record_or_404(record_id, session["account_id"])

    try:
        data = RecordData.from_json(crypto.decrypt(record.encrypted_data))
    except CryptoError:
        raise HTTPException(status_code=500, detail="Ошибка расшифровки")

    return RecordDetail(
        **_record_to_list_item(record).model_dump(),
        fields=data.fields,
        notes=data.notes,
        custom_fields=data.custom_fields,
    )


@app.post("/records", response_model=RecordListItem, status_code=201, tags=["records"])
def create_record(req: SaveRecordRequest, session: dict = Depends(_get_session)):
    crypto: CryptoManager = session["crypto"]
    data = RecordData(
        fields=req.fields,
        notes=req.notes,
        custom_fields=[tuple(cf) for cf in req.custom_fields],
    )
    encrypted = crypto.encrypt(data.to_json())
    record = Record(
        title=req.title,
        category=req.category,
        encrypted_data=encrypted,
        is_favorite=req.is_favorite,
        expiry_date=req.expiry_date,
        account_id=session["account_id"],
    )
    with _db_lock:
        record.id = _db.insert_record(record)

    return _record_to_list_item(_get_record_or_404(record.id, session["account_id"]))


@app.put("/records/{record_id}", response_model=RecordListItem, tags=["records"])
def update_record(
    record_id: int,
    req: SaveRecordRequest,
    session: dict = Depends(_get_session),
):
    crypto: CryptoManager = session["crypto"]
    record = _get_record_or_404(record_id, session["account_id"])

    data = RecordData(
        fields=req.fields,
        notes=req.notes,
        custom_fields=[tuple(cf) for cf in req.custom_fields],
    )
    record.title = req.title
    record.category = req.category
    record.is_favorite = req.is_favorite
    record.expiry_date = req.expiry_date
    record.encrypted_data = crypto.encrypt(data.to_json())

    with _db_lock:
        _db.update_record(record)

    return _record_to_list_item(_get_record_or_404(record_id, session["account_id"]))


@app.delete("/records/{record_id}", status_code=204, tags=["records"])
def delete_record(record_id: int, session: dict = Depends(_get_session)):
    _get_record_or_404(record_id, session["account_id"])
    with _db_lock:
        _db.delete_record(record_id)


@app.patch("/records/{record_id}/favorite", response_model=RecordListItem, tags=["records"])
def toggle_favorite(record_id: int, session: dict = Depends(_get_session)):
    _get_record_or_404(record_id, session["account_id"])
    with _db_lock:
        _db.toggle_favorite(record_id)
    return _record_to_list_item(_get_record_or_404(record_id, session["account_id"]))



MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024


@app.get(
    "/records/{record_id}/attachments",
    response_model=list[AttachmentInfo],
    tags=["attachments"],
)
def list_attachments(record_id: int, session: dict = Depends(_get_session)):
    _get_record_or_404(record_id, session["account_id"])
    with _db_lock:
        rows = _db.get_attachments(record_id)
    return [
        AttachmentInfo(
            id=r["id"],
            record_id=r["record_id"],
            filename=r["filename"],
            mimetype=r["mimetype"],
            size=r["size"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@app.post(
    "/records/{record_id}/attachments",
    response_model=AttachmentInfo,
    status_code=201,
    tags=["attachments"],
)
async def upload_attachment(
    record_id: int,
    file: UploadFile = File(...),
    session: dict = Depends(_get_session),
):
    _get_record_or_404(record_id, session["account_id"])

    data = await file.read()
    if len(data) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Файл слишком большой (максимум {MAX_ATTACHMENT_SIZE // 1024 // 1024} МБ)",
        )

    mimetype = file.content_type or "application/octet-stream"
    filename = file.filename or "file"

    with _db_lock:
        att_id = _db.insert_attachment(
            record_id=record_id,
            account_id=session["account_id"],
            filename=filename,
            mimetype=mimetype,
            data=data,
        )
        row = _db.get_attachments(record_id)

    att = next((r for r in row if r["id"] == att_id), None)
    if not att:
        raise HTTPException(status_code=500, detail="Ошибка при сохранении вложения")

    return AttachmentInfo(
        id=att["id"],
        record_id=att["record_id"],
        filename=att["filename"],
        mimetype=att["mimetype"],
        size=att["size"],
        created_at=att["created_at"],
    )


@app.get("/attachments/{attachment_id}/download", tags=["attachments"])
def download_attachment(attachment_id: int, session: dict = Depends(_get_session)):
    with _db_lock:
        att = _db.get_attachment(attachment_id)

    if not att:
        raise HTTPException(status_code=404, detail="Вложение не найдено")

    if att["account_id"] != session["account_id"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    import io
    return StreamingResponse(
        io.BytesIO(att["data"]),
        media_type=att["mimetype"],
        headers={
            "Content-Disposition": f'attachment; filename="{att["filename"]}"',
            "Content-Length": str(att["size"]),
        },
    )


@app.get("/attachments/{attachment_id}/view", tags=["attachments"])
def view_attachment(attachment_id: int, session: dict = Depends(_get_session)):
    with _db_lock:
        att = _db.get_attachment(attachment_id)

    if not att:
        raise HTTPException(status_code=404, detail="Вложение не найдено")

    if att["account_id"] != session["account_id"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    import io
    return StreamingResponse(
        io.BytesIO(att["data"]),
        media_type=att["mimetype"],
        headers={
            "Content-Disposition": f'inline; filename="{att["filename"]}"',
            "Content-Length": str(att["size"]),
            "Cache-Control": "private, max-age=3600",
        },
    )


@app.delete("/attachments/{attachment_id}", status_code=204, tags=["attachments"])
def delete_attachment(attachment_id: int, session: dict = Depends(_get_session)):
    with _db_lock:
        att = _db.get_attachment(attachment_id)

    if not att:
        raise HTTPException(status_code=404, detail="Вложение не найдено")

    if att["account_id"] != session["account_id"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    with _db_lock:
        _db.delete_attachment(attachment_id)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vault API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Адрес (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Порт (default: 8080)")
    args = parser.parse_args()

    host_db = os.environ.get("MYSQL_HOST", "localhost")
    db_name  = os.environ.get("MYSQL_DATABASE", "vault_db")
    user_db  = os.environ.get("MYSQL_USER", "vault_user")
    print(f"\n{'='*55}")
    print(f"  Vault API Server")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Swagger UI: http://localhost:{args.port}/docs")
    print(f"  База данных: MySQL")
    print(f"  MySQL: {user_db}@{host_db}/{db_name}")
    print(f"{'='*55}\n")

    uvicorn.run("server:app", host=args.host, port=args.port, reload=False)
