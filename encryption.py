"""
generate_kek_salt()   → generates fresh random salt
derive_kek()          → password + salt → KEK
generate_dek()        → generates fresh random DEK
wrap_dek()            → KEK + DEK → wrapped DEK
unwrap_dek()          → KEK + wrapped DEK → DEK
encrypt_file()        → DEK + content → ciphertext
decrypt_file()        → DEK + ciphertext → content
"""

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



"""
#Test for KEK

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

"""

#Generate DEK of 32 bytes
def generate_dek() -> bytes:
    return secrets.token_bytes(32)

#Wrap DEK using KEK 
def wrap_dek(dek: bytes, kek: bytes) -> bytes:
    iv = secrets.token_bytes(12)    # 12 bytes for AES-GCM
    aesgcm = AESGCM(kek)            # AES use kek
    encrypted = aesgcm.encrypt(iv, dek, None)  # iv, dek to encrypt
    return iv + encrypted           # store iv alongside the encrypted DEK

#Unwrap DEK using KEK
def unwrap_dek(wrapped_dek: bytes, kek: bytes) -> bytes:
    iv = wrapped_dek[:12]           # first 12 bytes are the iv
    encrypted = wrapped_dek[12:]    # rest is the encrypted DEK
    aesgcm = AESGCM(kek)            # same key as wrap_dek
    return aesgcm.decrypt(iv, encrypted, None)  # iv, then decrypt wrapped_dek

#Test for DEK

# generate fresh DEK
dek = generate_dek()
print(len(dek))         # should print 32

# derive a KEK to wrap it with
salt = generate_kek_salt()
kek = derive_kek("mypassword123", salt)

# wrap the DEK
wrapped = wrap_dek(dek, kek)
print(len(wrapped))     # should print more than 32 (iv + ciphertext + tag)

# unwrap with correct KEK
recovered_dek = unwrap_dek(wrapped, kek)
print(dek == recovered_dek)   # should print True

# unwrap with wrong KEK — should raise an error
wrong_kek = derive_kek("wrongpassword", salt)
try:
    unwrap_dek(wrapped, wrong_kek)
except Exception as e:
    print(f"Wrong KEK failed as expected: {e}")