# SecureVault

SecureVault is a file encryption and decryption app with:
- a FastAPI backend
- a React frontend
- AES-256-GCM file encryption
- Argon2id password hashing and JWT authentication

## Project layout
- `backend/` FastAPI API layer
- `frontend/` React/Vite frontend
- root Python modules provide the crypto, auth, CRUD, and database logic

## Run backend

```bash
cd /home/tanzir/inse_6110
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

## Run frontend

```bash
cd /home/tanzir/inse_6110/frontend
npm install
npm run dev
```

By default, the frontend talks to `http://localhost:8000/api`.
Set `VITE_API_URL` if you want to point it somewhere else.

If you open the frontend at `http://127.0.0.1:5173`, the backend already allows that origin too.
