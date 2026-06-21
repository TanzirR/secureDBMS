import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from auth import login_user, register_user, verify_token
from crud import create_file, delete_file, get_encrypted_file, list_files, read_file, update_file
from model import SessionLocal, init_db
from backend.schemas import (
    AuthResponse,
    FileCreateRequest,
    FileDetail,
    FileEncryptedDetail,
    FileListResponse,
    FileUpdateRequest,
    LoginRequest,
    RegisterRequest,
)

app = FastAPI(title="SecureVault API", version="1.0.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

    try:
        return verify_token(parts[1])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


CurrentUser = Annotated[dict, Depends(get_current_user)]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: DbSession):
    try:
        register_user(payload.username, payload.password, db)
        login_result = login_user(payload.username, payload.password, db)
        token_payload = verify_token(login_result["access_token"])
        return AuthResponse(access_token=login_result["access_token"], username=token_payload["username"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: DbSession):
    try:
        login_result = login_user(payload.username, payload.password, db)
        token_payload = verify_token(login_result["access_token"])
        return AuthResponse(access_token=login_result["access_token"], username=token_payload["username"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@app.get("/api/files", response_model=FileListResponse)
def get_files(current_user: CurrentUser, db: DbSession):
    result = list_files(current_user["user_id"], db)
    return FileListResponse(count=result["count"], files=result["files"])


@app.post("/api/files", response_model=FileDetail)
def create_new_file(payload: FileCreateRequest, current_user: CurrentUser, db: DbSession):
    try:
        create_file(payload.filename, payload.content, current_user["user_id"], current_user["dek"], db)
        result = read_file(payload.filename, current_user["user_id"], current_user["dek"], db)
        return FileDetail(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/api/files/{filename}", response_model=FileDetail)
def get_file(filename: str, current_user: CurrentUser, db: DbSession):
    try:
        result = read_file(filename, current_user["user_id"], current_user["dek"], db)
        return FileDetail(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/api/files/{filename}/encrypted", response_model=FileEncryptedDetail)
def get_encrypted_file_view(filename: str, current_user: CurrentUser, db: DbSession):
    try:
        result = get_encrypted_file(filename, current_user["user_id"], db)
        return FileEncryptedDetail(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.put("/api/files/{filename}", response_model=FileDetail)
def update_existing_file(filename: str, payload: FileUpdateRequest, current_user: CurrentUser, db: DbSession):
    try:
        update_file(filename, payload.content, current_user["user_id"], current_user["dek"], db)
        result = read_file(filename, current_user["user_id"], current_user["dek"], db)
        return FileDetail(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete("/api/files/{filename}")
def delete_existing_file(filename: str, current_user: CurrentUser, db: DbSession):
    try:
        delete_file(filename, current_user["user_id"], db)
        return {"message": f"File '{filename}' deleted successfully."}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
