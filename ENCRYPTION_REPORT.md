# Encryption and Decryption Report

This project uses a two-key design:

- a password-derived key to protect a long-term file key
- a separate file key to encrypt and decrypt the actual file data

That split is the core idea behind the code in `encryption.py`.

## 1. The Concepts

### Symmetric encryption

The project uses AES-GCM, which is a symmetric encryption scheme. Symmetric means the same kind of secret key is used to encrypt and decrypt data. In practice, the code does not use one key for everything. It uses a separate key for the user password side and another key for file contents.

### KEK and DEK

The code separates encryption into two layers:

- KEK: Key Encryption Key
- DEK: Data Encryption Key

The KEK is derived from the user’s password. It is used only to protect the DEK. The DEK is a random key generated for a user and used to encrypt file content. This design has a useful property: if the user changes files, the file data can be re-encrypted without changing the password-derived key. And if the password changes in a future extension, only the wrapped DEK needs to be updated, not every encrypted file.

### Salt

A salt is random data added before key derivation. It makes the derived KEK unique even if two users choose the same password. It also makes precomputed attacks much harder. A salt is not secret; it just needs to be random and stored so the same password can reproduce the same key later.

### PBKDF2

PBKDF2 is a password-based key derivation function. It turns a human password into a cryptographic key. The important idea is that passwords are weak compared with raw encryption keys, so the code applies many iterations of hashing work to make guessing expensive.

### AES-GCM

AES-GCM is an authenticated encryption mode. It does two things at once:

- encrypts the plaintext so outsiders cannot read it
- adds integrity protection so tampering is detected

That integrity check is the GCM authentication tag. If the ciphertext or tag is modified, decryption fails.

### IV / nonce

AES-GCM needs a unique initialization vector, or IV, for each encryption operation. The IV is not secret, but it must not be reused with the same key. The code generates a fresh 12-byte IV each time it encrypts either a DEK or file content.

## 2. How `encryption.py` Works

### `generate_kek_salt()`

This function creates a fresh 32-byte random salt for each user. The salt is stored with the user record so the same password can later derive the same KEK.

### `derive_kek(password, salt)`

This takes the user’s password and salt and runs PBKDF2-HMAC-SHA256 with 600,000 iterations. The result is a 32-byte KEK suitable for AES-256.

Conceptually:

`password + salt -> KEK`

This is not encryption yet. It is key derivation: turning a password into a strong key.

### `generate_dek()`

This creates a random 32-byte DEK. Unlike the KEK, the DEK is not derived from the password. It is randomly generated so file encryption has a strong, independent key.

Conceptually:

`random bytes -> DEK`

### `wrap_dek(dek, kek)`

This encrypts the DEK with the KEK using AES-GCM. The function generates a fresh IV, encrypts the DEK, and returns the IV concatenated with the encrypted result.

Conceptually:

`KEK + DEK -> wrapped DEK`

The wrapped DEK is what gets stored in the database. It is safe to store because it cannot be recovered without the KEK, which comes from the user’s password.

### `unwrap_dek(wrapped_dek, kek)`

This reverses `wrap_dek()`. It splits the stored value into IV and encrypted bytes, then decrypts them using the KEK.

Conceptually:

`KEK + wrapped DEK -> DEK`

If the password is wrong or the wrapped data is corrupted, decryption fails.

### `encrypt_file(content, dek)`

This encrypts file bytes with the DEK using AES-GCM. The function generates a fresh IV and returns three pieces:

- ciphertext
- IV
- tag

Conceptually:

`DEK + plaintext content -> ciphertext + IV + tag`

The code stores these separately in the database.

### `decrypt_file(ciphertext, iv, tag, dek)`

This reconstructs the AES-GCM input and decrypts the stored file data.

Conceptually:

`DEK + ciphertext + IV + tag -> plaintext content`

If any part has been altered, AES-GCM rejects it by raising an authentication error.

## 3. How This Maps to the App Flow

### Registration

In `auth.py`, registration does four important things:

1. hashes the password with Argon2id for authentication
2. generates a new salt
3. derives a KEK from the password and salt
4. generates a DEK and wraps it with the KEK

The database stores the password hash, the salt, and the wrapped DEK.

So during registration, the app is building two parallel protections:

- Argon2id protects password verification
- KEK/DEK wrapping protects file encryption material

### Login

During login, the app verifies the password hash first. Then it derives the KEK again from the password and stored salt, unwraps the DEK, and puts that DEK into the JWT payload.

That means the session token becomes the carrier of the file decryption key for the lifetime of the token.

### File creation and update

In `crud.py`, `create_file()` and `update_file()` both call `encrypt_file()` with the user’s DEK. The plaintext file content is encrypted before storage.

The database stores:

- ciphertext
- IV
- tag

The original plaintext is never stored.

### File read

`read_file()` fetches the encrypted record and calls `decrypt_file()` with the same DEK. If the DEK is correct and the data has not been tampered with, the original text is returned.

### Encrypted file view

`get_encrypted_file()` exposes the encrypted bytes in base64 form for display or debugging. It does not decrypt anything.

## 4. What Is Stored Where

### In the user record

- password hash
- KEK salt
- wrapped DEK

### In the encrypted file record

- ciphertext
- IV
- tag

This separation is deliberate. The password is never stored directly, and the file contents are never stored in plaintext.

## 5. Why the Design Is Useful

This design gives a few benefits:

- The password is never used directly to encrypt file data.
- A single random DEK can be reused for many file operations under the same user.
- AES-GCM provides both confidentiality and tamper detection.
- A fresh IV is used for each encryption, which is required for safe AES-GCM usage.

## 6. Important Implementation Note

The current implementation puts the DEK inside the JWT after login. That makes the JWT more than an identity token; it also becomes a temporary decryption credential. Anyone who gets the token before it expires can decrypt that user’s files through the API.

That may be acceptable for this project, but it is important to understand because it changes the security model.

## 7. Short Mental Model

You can think of the system like this:

1. The password unlocks a key box.
2. The key box contains a random file key.
3. The file key encrypts and decrypts the actual files.
4. The files are stored encrypted in the database.

Or in formula form:

`password -> KEK -> unwrap DEK -> decrypt file`

and in the other direction:

`plaintext file -> encrypt with DEK -> store ciphertext`

## 8. Summary

`encryption.py` implements the building blocks for the whole crypto design:

- generate a salt
- derive a password-based key
- generate a random file key
- wrap and unwrap that file key
- encrypt and decrypt file content

The rest of the app uses those helpers in a straightforward way: registration creates the cryptographic material, login recovers the DEK, and file CRUD operations use the DEK to protect the file contents.