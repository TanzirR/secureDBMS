from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

#generate a fresh salt for new user
def generate_kek_salt() -> bytes:
    return secrets.token_bytes(32)  # 256-bit random salt

#derive KEK from password + salt
def derive_kek(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),         # hint: hashes.SHA256()
        length=32,            # hint: 32 bytes for AES-256
        salt=salt,             # hint: the salt parameter
        iterations=600000,        # hint: 600_000
    )
    return kdf.derive(password.encode("utf-8"))    # hint: password needs to be bytes


salt = generate_kek_salt()
kek = derive_kek("mypassword123", salt)
print(len(kek))   # should print 32
print(type(kek))  # should print <class 'bytes'>

# same password + same salt = same key
kek2 = derive_kek("mypassword123", salt)
print(kek == kek2)  # should print True

# different password = different key
kek3 = derive_kek("wrongpassword", salt)
print(kek == kek3)  # should print False
