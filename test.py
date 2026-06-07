from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

key = secrets.token_bytes(32)   # 256-bit key
iv  = secrets.token_bytes(12)   # 96-bit nonce

aesgcm = AESGCM(key)
ciphertext = aesgcm.encrypt(iv, b"hello world", None)
plaintext  = aesgcm.decrypt(iv, ciphertext, None)

print(ciphertext)  # b"hello world"