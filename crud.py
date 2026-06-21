"""
create_file()  → encrypt file content + store in DB
read_file()    → fetch from DB + decrypt content
get_encrypted_file() → fetch encrypted bytes for display
update_file()  → re-encrypt with new content + update DB
delete_file()  → remove file from DB
list_files()   → return all filenames for the user
"""

import uuid
import base64
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from cryptography.exceptions import InvalidTag

from encryption import encrypt_file, decrypt_file
from model import EncryptedFile


def create_file(filename: str, content: str, user_id: str, dek: bytes, db: Session) -> dict:
    # step 1 — check if file already exists for this user
    existing = db.query(EncryptedFile).filter(
        EncryptedFile.owner_id == user_id,
        EncryptedFile.filename == filename
    ).first()
    if existing:
        raise ValueError(f"File '{filename}' already exists. Use update to modify it.")

    # step 2 — encrypt the file content
    ciphertext, iv, tag = encrypt_file(content.encode("utf-8"), dek)

    # step 3 — store in DB
    file_record = EncryptedFile(
        id=str(uuid.uuid4()),
        owner_id=user_id,
        filename=filename,
        ciphertext=ciphertext,
        iv=iv,
        tag=tag,
    )
    db.add(file_record)
    db.commit()

    return {"message": f"File '{filename}' created and encrypted successfully."}


def read_file(filename: str, user_id: str, dek: bytes, db: Session) -> dict:
    # step 1 — fetch file from DB
    file_record = db.query(EncryptedFile).filter(
        EncryptedFile.owner_id == user_id,
        EncryptedFile.filename == filename
    ).first()
    if not file_record:
        raise ValueError(f"File '{filename}' not found.")

    # step 2 — decrypt the file content
    try:
        content = decrypt_file(file_record.ciphertext, file_record.iv, file_record.tag, dek)
    except InvalidTag:
        raise ValueError("Decryption failed — file may be tampered with.")

    return {
        "filename": filename,
        "content": content.decode("utf-8"),
        "created_at": file_record.created_at.isoformat(),
        "updated_at": file_record.updated_at.isoformat(),
    }


def get_encrypted_file(filename: str, user_id: str, db: Session) -> dict:
    # step 1 — fetch file from DB
    file_record = db.query(EncryptedFile).filter(
        EncryptedFile.owner_id == user_id,
        EncryptedFile.filename == filename
    ).first()
    if not file_record:
        raise ValueError(f"File '{filename}' not found.")

    return {
        "filename": filename,
        "ciphertext": base64.b64encode(file_record.ciphertext).decode("utf-8"),
        "iv": base64.b64encode(file_record.iv).decode("utf-8"),
        "tag": base64.b64encode(file_record.tag).decode("utf-8"),
        "created_at": file_record.created_at.isoformat(),
        "updated_at": file_record.updated_at.isoformat(),
    }


def update_file(filename: str, new_content: str, user_id: str, dek: bytes, db: Session) -> dict:
    # step 1 — fetch file from DB
    file_record = db.query(EncryptedFile).filter(
        EncryptedFile.owner_id == user_id,
        EncryptedFile.filename == filename
    ).first()
    if not file_record:
        raise ValueError(f"File '{filename}' not found.")

    # step 2 — re-encrypt with new content
    ciphertext, iv, tag = encrypt_file(new_content.encode("utf-8"), dek)

    # step 3 — update DB record
    file_record.ciphertext = ciphertext
    file_record.iv = iv
    file_record.tag = tag
    file_record.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": f"File '{filename}' updated and re-encrypted successfully."}


def delete_file(filename: str, user_id: str, db: Session) -> dict:
    # step 1 — fetch file from DB
    file_record = db.query(EncryptedFile).filter(
        EncryptedFile.owner_id == user_id,
        EncryptedFile.filename == filename
    ).first()
    if not file_record:
        raise ValueError(f"File '{filename}' not found.")

    # step 2 — delete from DB
    db.delete(file_record)
    db.commit()

    return {"message": f"File '{filename}' deleted successfully."}


def list_files(user_id: str, db: Session) -> dict:
    # fetch all files belonging to this user
    files = db.query(EncryptedFile).filter(
        EncryptedFile.owner_id == user_id
    ).order_by(EncryptedFile.created_at.desc()).all()

    return {
        "files": [
            {
                "filename": f.filename,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat(),
            }
            for f in files
        ],
        "count": len(files),
    }


