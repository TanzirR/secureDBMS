from sqlalchemy import create_engine, Column, String, LargeBinary, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

DATABASE_URL = "sqlite:///./secure_files.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    __tablename__ = "users"

    #id, username, password_hash, kek_salt, wrapped_dek, created_at
    id = Column(String, primary_key=True)
    username = Column(String, unique = True, nullable=False)
    password_hash = Column(String, nullable=False)
    kek_salt = Column(LargeBinary,nullable=False)
    wrapped_dek = Column(LargeBinary,nullable=False)
    files = relationship("EncryptedFile", back_populates="owner", cascade="all, delete-orphan")
    created_at = Column(DateTime, default=datetime.utcnow)

class EncryptedFile(Base):
    __tablename__ = "encrypted_files"

    # id, owner_id, filename, ciphertext, iv, tag, created_at, updated_at
    id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey("users.id"),nullable=False)
    filename = Column(String, nullable=False)
    ciphertext = Column(LargeBinary, nullable=False)
    iv = Column(LargeBinary,nullable=False)
    tag = Column(LargeBinary,nullable=False) #AESGSM tag
    owner = relationship("User", back_populates="files")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default = datetime.utcnow, onupdate = datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Database and tables created successfully!")