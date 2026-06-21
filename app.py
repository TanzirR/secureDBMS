"""
SecureVault
- Login / Register page
- After login: polished CRUD dashboard for encrypted files
"""

import html
import streamlit as st
from model import init_db, SessionLocal
from auth import register_user, login_user, verify_token
from crud import create_file, read_file, update_file, delete_file, list_files

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="SecureVault", page_icon="🔐", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --bg: #071114;
        --panel: rgba(10, 24, 28, 0.82);
        --panel-strong: rgba(13, 31, 36, 0.95);
        --border: rgba(255, 255, 255, 0.08);
        --text: #e8f1ef;
        --muted: rgba(232, 241, 239, 0.68);
        --accent: #56c2a6;
        --accent-strong: #2ea389;
        --accent-soft: rgba(86, 194, 166, 0.14);
        --danger: #ef6f6c;
        --shadow: 0 24px 70px rgba(0, 0, 0, 0.24);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(86, 194, 166, 0.20), transparent 26%),
            radial-gradient(circle at top right, rgba(76, 129, 255, 0.18), transparent 22%),
            linear-gradient(180deg, #071114 0%, #09161a 48%, #0b181c 100%);
        color: var(--text);
        font-family: 'Manrope', sans-serif;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1250px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .vault-hero {
        padding: 1.15rem 1.35rem;
        border: 1px solid var(--border);
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(12, 28, 32, 0.90), rgba(8, 20, 24, 0.78));
        box-shadow: var(--shadow);
        backdrop-filter: blur(12px);
        margin-bottom: 1rem;
    }
    .vault-brand {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.55rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #f5fbfa;
    }
    .vault-subtitle {
        color: var(--muted);
        margin-top: 0.2rem;
        font-size: 0.98rem;
    }
    .vault-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.4rem 0.75rem;
        border-radius: 999px;
        background: var(--accent-soft);
        color: #d8f6ee;
        border: 1px solid rgba(86, 194, 166, 0.18);
        font-size: 0.84rem;
        font-weight: 700;
    }
    .vault-section-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        color: #f4fbf8;
    }
    .vault-section-copy {
        color: var(--muted);
        margin-bottom: 0.9rem;
        font-size: 0.94rem;
    }
    .vault-card {
        padding: 0.95rem 1rem;
        border-radius: 16px;
        border: 1px solid var(--border);
        background: linear-gradient(180deg, rgba(14, 31, 36, 0.92), rgba(10, 24, 28, 0.78));
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
        margin-bottom: 0.8rem;
    }
    .vault-meta {
        color: var(--muted);
        font-size: 0.9rem;
    }
    .vault-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #f0faf7;
        margin-bottom: 0.2rem;
    }
    .vault-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        flex-wrap: wrap;
        margin-top: 0.6rem;
    }
    .vault-small {
        font-size: 0.84rem;
        color: var(--muted);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.04);
        border-radius: 999px;
        padding: 0.45rem 1rem;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(86, 194, 166, 0.18);
    }
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        background-color: rgba(8, 18, 22, 0.86) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        box-shadow: none !important;
        border-color: rgba(86, 194, 166, 0.72) !important;
    }
    .stButton > button {
        border-radius: 12px !important;
        border: 1px solid rgba(86, 194, 166, 0.24) !important;
        background: linear-gradient(180deg, rgba(86, 194, 166, 0.24), rgba(46, 163, 137, 0.18)) !important;
        color: #f3fbf9 !important;
        font-weight: 700 !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        border-color: rgba(86, 194, 166, 0.48) !important;
        transform: translateY(-1px);
    }
    .stMetric {
        background: rgba(12, 28, 32, 0.72);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 0.9rem 1rem;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
    }
</style>
""",
    unsafe_allow_html=True,
)

# ── Init DB ───────────────────────────────────────────────────────────────────

init_db()

# ── Session state ─────────────────────────────────────────────────────────────

for key, default in {
    "token": None,
    "username": None,
    "dek": None,
    "user_id": None,
    "preview_file": None,
    "file_search": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

def get_user_files():
    db = SessionLocal()
    try:
        return list_files(st.session_state.user_id, db)["files"]
    finally:
        db.close()


def read_user_file(filename: str):
    db = SessionLocal()
    try:
        return read_file(filename, st.session_state.user_id, st.session_state.dek, db)
    finally:
        db.close()


def render_file_cards(files: list[dict]):
    if not files:
        st.info("No files yet. Create your first encrypted file on the left.")
        return

    for file_info in files:
        filename = html.escape(str(file_info["filename"]))
        created_at = html.escape(str(file_info["created_at"]))
        updated_at = html.escape(str(file_info["updated_at"]))
        st.markdown(
            f"""
            <div class="vault-card">
                <div class="vault-title">{filename}</div>
                <div class="vault-meta">Created: {created_at}</div>
                <div class="vault-meta">Updated: {updated_at}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_file_browser(files: list[dict]):
    st.markdown('<div class="vault-section-title">File Browser</div>', unsafe_allow_html=True)
    st.markdown('<div class="vault-section-copy">Search, inspect, and open files from a clean list view.</div>', unsafe_allow_html=True)

    search_query = st.text_input(
        "Search files",
        key="file_search",
        placeholder="Filter by filename...",
        label_visibility="collapsed",
    ).strip().lower()

    filtered_files = [
        file_info for file_info in files
        if search_query in file_info["filename"].lower()
    ]

    if not filtered_files:
        st.info("No matching files found.")
        return

    for index, file_info in enumerate(filtered_files):
        filename = html.escape(str(file_info["filename"]))
        created_at = html.escape(str(file_info["created_at"]))
        updated_at = html.escape(str(file_info["updated_at"]))

        st.markdown(
            f"""
            <div class="vault-card">
                <div class="vault-title">{filename}</div>
                <div class="vault-meta">Created: {created_at}</div>
                <div class="vault-meta">Updated: {updated_at}</div>
                <div class="vault-row">
                    <div class="vault-small">Encrypted record</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open file", key=f"open_file_{index}_{file_info['filename']}", use_container_width=True):
            st.session_state.preview_file = file_info["filename"]
            st.rerun()


def render_file_summary(file_info: dict | None):
    if not file_info:
        st.info("Select a file to view its decrypted content and timestamps.")
        return

    st.markdown(
        f"""
        <div class="vault-card">
            <div class="vault-title">{html.escape(str(file_info['filename']))}</div>
            <div class="vault-meta">Created: {html.escape(str(file_info['created_at']))}</div>
            <div class="vault-meta">Updated: {html.escape(str(file_info['updated_at']))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_decrypted_preview(file_info: dict | None):
    if not file_info:
        return

    try:
        result = read_user_file(file_info["filename"])
        st.code(result["content"], language="text")
    except Exception as e:
        st.error(f"Could not decrypt file: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# ── AUTH + DASHBOARD ─────────────────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════

if not st.session_state.token:

    st.markdown("## 🔐 SecureVault")
    st.caption("AES-256-GCM · Argon2id · PBKDF2 · JWT · Key Wrapping")
    st.markdown("---")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login", use_container_width=True):
            if login_username and login_password:
                db = SessionLocal()
                try:
                    result = login_user(login_username, login_password, db)
                    payload = verify_token(result["access_token"])
                    st.session_state.token = result["access_token"]
                    st.session_state.username = payload["username"]
                    st.session_state.dek = payload["dek"]
                    st.session_state.user_id = payload["user_id"]
                    st.session_state.preview_file = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
                finally:
                    db.close()
            else:
                st.warning("Please enter username and password.")

    with tab2:
        st.subheader("Register")
        reg_username = st.text_input("Username", key="reg_user")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_pass2")

        if st.button("Register", use_container_width=True):
            if reg_username and reg_password and reg_confirm:
                if reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    db = SessionLocal()
                    try:
                        register_user(reg_username, reg_password, db)
                        st.success("Account created! You can now log in.")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")
                    finally:
                        db.close()
            else:
                st.warning("Please fill in all fields.")

else:

    files = get_user_files()
    file_names = [file_info["filename"] for file_info in files]
    latest_updated = max(files, key=lambda item: item["updated_at"]) if files else None
    selected_file = next((file_info for file_info in files if file_info["filename"] == st.session_state.preview_file), None)
    if selected_file is None and files:
        selected_file = files[0]
        st.session_state.preview_file = selected_file["filename"]

    st.markdown(
        f"""
        <div class="vault-hero">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;">
                <div>
                    <div class="vault-brand">SecureVault</div>
                    <div class="vault-subtitle">Manage encrypted files with a polished, secure workspace.</div>
                    <div style="margin-top:0.75rem;">
                        <span class="vault-chip">Encrypted storage</span>
                    </div>
                </div>
                <div style="font-weight:700;color:#b8d8d0;">{html.escape(str(st.session_state.username))}@securevault</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_left, metric_mid, metric_right = st.columns(3, gap="medium")
    with metric_left:
        st.metric("Files stored", len(file_names))
    with metric_mid:
        st.metric("Current focus", st.session_state.preview_file or "None selected")
    with metric_right:
        st.metric("Last updated", latest_updated["updated_at"] if latest_updated else "No files yet")

    if st.button("Logout"):
        for key in ["token", "username", "dek", "user_id", "preview_file"]:
            st.session_state[key] = None
        st.rerun()

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown('<div class="vault-section-title">Encrypt New File</div>', unsafe_allow_html=True)
        st.markdown('<div class="vault-section-copy">Create a new encrypted file and store it securely.</div>', unsafe_allow_html=True)
        with st.form("create_file_form", clear_on_submit=True):
            create_name = st.text_input("File name", placeholder="notes.txt")
            create_content = st.text_area(
                "Content",
                height=220,
                placeholder="Write the content you want to encrypt and store...",
            )
            create_submit = st.form_submit_button("Encrypt & Save", type="primary", use_container_width=True)

        if create_submit:
            if not create_name.strip() or not create_content.strip():
                st.warning("Please provide both a file name and some content.")
            else:
                db = SessionLocal()
                try:
                    create_file(create_name.strip(), create_content, st.session_state.user_id, st.session_state.dek, db)
                    st.success(f"File '{create_name.strip()}' encrypted and saved.")
                    st.session_state.preview_file = create_name.strip()
                    st.rerun()
                except Exception as e:
                    st.error(f"Create failed: {e}")
                finally:
                    db.close()

        st.markdown("---")
        st.markdown('<div class="vault-section-title">Decrypt Selected File</div>', unsafe_allow_html=True)
        st.markdown('<div class="vault-section-copy">Choose a file to decrypt and review its contents.</div>', unsafe_allow_html=True)

        if file_names:
            with st.form("read_file_form"):
                read_name = st.selectbox("Choose a file", file_names, key="read_file_name", index=file_names.index(selected_file["filename"]) if selected_file and selected_file["filename"] in file_names else 0)
                read_submit = st.form_submit_button("Decrypt & View", use_container_width=True)

            if read_submit:
                try:
                    result = read_user_file(read_name)
                    st.session_state.preview_file = read_name
                    st.success(f"Decrypted '{read_name}'.")
                    st.code(result["content"], language="text")
                    st.rerun()
                except Exception as e:
                    st.error(f"Read failed: {e}")
        else:
            st.info("No files available yet.")

        with st.expander("Manage file contents", expanded=False):
            st.caption("Use these actions when you need to modify or remove an existing file.")
            if file_names:
                update_tab, delete_tab = st.tabs(["Update", "Delete"])

                with update_tab:
                    with st.form("update_file_form"):
                        update_name = st.selectbox("Choose a file", file_names, key="update_file_name", index=file_names.index(selected_file["filename"]) if selected_file and selected_file["filename"] in file_names else 0)
                        update_content = st.text_area(
                            "New content",
                            height=220,
                            placeholder="Type the updated content here...",
                        )
                        update_submit = st.form_submit_button("Update file", use_container_width=True)

                    if update_submit:
                        if not update_content.strip():
                            st.warning("Please enter new content for the file.")
                        else:
                            db = SessionLocal()
                            try:
                                update_file(update_name, update_content, st.session_state.user_id, st.session_state.dek, db)
                                st.success(f"File '{update_name}' updated.")
                                st.session_state.preview_file = update_name
                                st.rerun()
                            except Exception as e:
                                st.error(f"Update failed: {e}")
                            finally:
                                db.close()

                with delete_tab:
                    with st.form("delete_file_form"):
                        delete_name = st.selectbox("Choose a file", file_names, key="delete_file_name", index=file_names.index(selected_file["filename"]) if selected_file and selected_file["filename"] in file_names else 0)
                        confirm_delete = st.checkbox(f"I understand that '{delete_name}' will be deleted permanently.")
                        delete_submit = st.form_submit_button("Delete file", use_container_width=True)

                    if delete_submit:
                        if not confirm_delete:
                            st.warning("Please confirm the deletion first.")
                        else:
                            db = SessionLocal()
                            try:
                                delete_file(delete_name, st.session_state.user_id, db)
                                st.success(f"File '{delete_name}' deleted.")
                                if st.session_state.preview_file == delete_name:
                                    st.session_state.preview_file = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete failed: {e}")
                            finally:
                                db.close()
            else:
                st.info("No files available yet.")

    with right:
        st.markdown('<div class="vault-section-title">Library</div>', unsafe_allow_html=True)
        st.markdown('<div class="vault-section-copy">Browse encrypted files, search quickly, and open any item for decryption.</div>', unsafe_allow_html=True)
        st.caption(f"{len(file_names)} file{'s' if len(file_names) != 1 else ''} stored securely")
        render_file_browser(files)
        st.markdown("---")
        st.markdown('<div class="vault-section-title">Decrypted Preview</div>', unsafe_allow_html=True)
        st.markdown('<div class="vault-section-copy">The selected file is decrypted here so you can verify contents at a glance.</div>', unsafe_allow_html=True)
        render_file_summary(selected_file)
        render_decrypted_preview(selected_file)