from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    username: str


class FileCreateRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=0)


class FileUpdateRequest(BaseModel):
    content: str = Field(min_length=0)


class FileItem(BaseModel):
    filename: str
    created_at: str
    updated_at: str


class FileDetail(BaseModel):
    filename: str
    content: str
    created_at: str
    updated_at: str


class FileEncryptedDetail(BaseModel):
    filename: str
    ciphertext: str
    iv: str
    tag: str
    created_at: str
    updated_at: str


class FileListResponse(BaseModel):
    count: int
    files: list[FileItem]
