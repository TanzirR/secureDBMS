import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  ApiError,
  createFile,
  deleteFile,
  getEncryptedFile,
  getFile,
  getFiles,
  getStoredSession,
  login,
  logout,
  register,
  updateFile,
  type FileDetail,
  type FileEncryptedDetail,
  type FileItem,
} from './api';

type Mode = 'login' | 'register';
type Composer = 'create' | 'view' | 'encrypted' | 'update' | 'delete';

const LOGIN_COOLDOWN_STORAGE_KEY = 'securevault_login_cooldown_until';

export default function App() {
  const [mode, setMode] = useState<Mode>('login');
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const storedTheme = localStorage.getItem('securevault_theme');
    return storedTheme === 'light' ? 'light' : 'dark';
  });
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [preview, setPreview] = useState<FileDetail | null>(null);
  const [encryptedPreview, setEncryptedPreview] = useState<FileEncryptedDetail | null>(null);
  const [search, setSearch] = useState('');
  const [composer, setComposer] = useState<Composer>('create');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [, setCooldownTick] = useState(0);
  const [loginCooldownUntil, setLoginCooldownUntil] = useState<number | null>(() => {
    const storedValue = localStorage.getItem(LOGIN_COOLDOWN_STORAGE_KEY);
    const parsedValue = storedValue ? Number.parseInt(storedValue, 10) : Number.NaN;
    return Number.isFinite(parsedValue) && parsedValue > Date.now() ? parsedValue : null;
  });

  const [authForm, setAuthForm] = useState({ username: '', password: '' });
  const [createForm, setCreateForm] = useState({ filename: '', content: '' });
  const [updateContent, setUpdateContent] = useState('');
  const [deleteConfirmed, setDeleteConfirmed] = useState(false);

  useEffect(() => {
    const session = getStoredSession();
    if (session.token) {
      setToken(session.token);
      setUsername(session.username);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('securevault_theme', theme);
  }, [theme]);

  useEffect(() => {
    if (loginCooldownUntil) {
      localStorage.setItem(LOGIN_COOLDOWN_STORAGE_KEY, String(loginCooldownUntil));
      return;
    }

    localStorage.removeItem(LOGIN_COOLDOWN_STORAGE_KEY);
  }, [loginCooldownUntil]);

  useEffect(() => {
    if (!loginCooldownUntil) return;

    const timer = window.setInterval(() => {
      if (Date.now() >= loginCooldownUntil) {
        setLoginCooldownUntil(null);
      } else {
        setCooldownTick((current) => current + 1);
      }
    }, 1000);

    return () => window.clearInterval(timer);
  }, [loginCooldownUntil]);

  useEffect(() => {
    if (!token) return;
    void refreshFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!selectedFile && files.length > 0) {
      setSelectedFile(files[0].filename);
    }
    if (selectedFile && !files.some((file) => file.filename === selectedFile)) {
      setSelectedFile(files[0]?.filename ?? '');
    }
  }, [files, selectedFile]);

  useEffect(() => {
    if (!token || !selectedFile) {
      setPreview(null);
      setEncryptedPreview(null);
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        if (composer === 'encrypted') {
          const detail = await getEncryptedFile(selectedFile);
          if (!cancelled) {
            setEncryptedPreview(detail);
            setPreview(null);
          }
        } else {
          const detail = await getFile(selectedFile);
          if (!cancelled) {
            setPreview(detail);
            setEncryptedPreview(null);
            setUpdateContent(detail.content);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load file');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token, selectedFile, composer]);

  const filteredFiles = useMemo(
    () => files.filter((file) => file.filename.toLowerCase().includes(search.toLowerCase())),
    [files, search],
  );

  async function refreshFiles() {
    try {
      const result = await getFiles();
      setFiles(result.files);
      if (!selectedFile && result.files.length > 0) {
        setSelectedFile(result.files[0].filename);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load files');
    }
  }

  async function handleAuthSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const username = authForm.username.trim();
      const password = authForm.password;
      const now = Date.now();

      if (!username) {
        throw new Error('Username is required');
      }

      if (mode === 'login' && loginCooldownUntil && now < loginCooldownUntil) {
        const remainingSeconds = Math.max(1, Math.ceil((loginCooldownUntil - now) / 1000));
        throw new Error(`Too many failed login attempts. Please wait ${remainingSeconds} seconds before trying again.`);
      }

      if (mode === 'register' && password.length < 8) {
        throw new Error('Password must be at least 8 characters long');
      }

      const action = mode === 'login' ? login : register;
      const result = await action(username, password);
      setToken(result.access_token);
      setUsername(result.username);
      setAuthForm({ username: '', password: '' });
      setLoginCooldownUntil(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429 && mode === 'login') {
        const retryAfterSeconds = err.retryAfterSeconds ?? 120;
        setLoginCooldownUntil(Date.now() + retryAfterSeconds * 1000);
      }
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const created = await createFile(createForm.filename.trim(), createForm.content);
      setSelectedFile(created.filename);
      setCreateForm({ filename: '', content: '' });
      setShowCreateForm(false);
      setComposer('view');
      await refreshFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdate(event: FormEvent) {
    event.preventDefault();
    if (!selectedFile) return;
    setLoading(true);
    setError('');
    try {
      await updateFile(selectedFile, updateContent);
      await refreshFiles();
      setPreview(await getFile(selectedFile));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(event: FormEvent) {
    event.preventDefault();
    if (!selectedFile) return;
    setLoading(true);
    setError('');
    try {
      await deleteFile(selectedFile);
      setDeleteConfirmed(false);
      const nextFiles = files.filter((file) => file.filename !== selectedFile);
      setFiles(nextFiles);
      setSelectedFile(nextFiles[0]?.filename ?? '');
      setPreview(null);
      await refreshFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    logout();
    setToken(null);
    setUsername(null);
    setFiles([]);
    setSelectedFile('');
    setPreview(null);
    setEncryptedPreview(null);
    setCreateForm({ filename: '', content: '' });
    setUpdateContent('');
    setShowCreateForm(false);
    setComposer('create');
  }

  function toggleTheme() {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'));
  }

  function selectFile(filename: string, nextComposer: Composer = 'view') {
    setSelectedFile(filename);
    setComposer(nextComposer);
    setDeleteConfirmed(false);
  }

  async function showEncryptedView(filename: string) {
    setSelectedFile(filename);
    setComposer('encrypted');
    setDeleteConfirmed(false);
  }

  const loginCooldownRemainingSeconds = loginCooldownUntil
    ? Math.max(0, Math.ceil((loginCooldownUntil - Date.now()) / 1000))
    : 0;

  const isLoginCooldownActive = mode === 'login' && loginCooldownRemainingSeconds > 0;

  if (!token) {
    return (
      <div className={`theme-shell ${theme === 'light' ? 'theme-light' : 'theme-dark'}`}>
        <div className="shell auth-shell">
          <div className="auth-topbar">
            <div className="brand-lock">SecureDBMS</div>
            <button className="ghost small" type="button" onClick={toggleTheme}>
              {theme === 'dark' ? 'Light theme' : 'Dark theme'}
            </button>
          </div>
          <div className="auth-hero">
            <div className="brand-lock">SecureDBMS</div>
            <h1>Your encrypted files, accessible only to you.</h1>
            <p>
              Store sensitive content, decrypt it on demand, and manage your vault.
            </p>
            <div className="auth-points">
              <span>Fast authentication</span>
              <span>AES-256-GCM file encryption</span>
              <span>Readable file browser</span>
            </div>
          </div>

          <div className="card auth-card">
            <div className="tabs">
              <button className={mode === 'login' ? 'tab active' : 'tab'} onClick={() => setMode('login')}>
                Login
              </button>
              <button className={mode === 'register' ? 'tab active' : 'tab'} onClick={() => setMode('register')}>
                Register
              </button>
            </div>

            <form onSubmit={handleAuthSubmit} className="stack">
              <label>
                Username
                <input
                  value={authForm.username}
                  onChange={(event) => setAuthForm({ ...authForm, username: event.target.value })}
                  placeholder="yourname"
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={authForm.password}
                  minLength={mode === 'register' ? 8 : 1}
                  onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })}
                  placeholder="••••••••"
                />
              </label>
              {isLoginCooldownActive ? (
                <div className="alert info">
                  Too many failed login attempts. Try again in {loginCooldownRemainingSeconds} second
                  {loginCooldownRemainingSeconds === 1 ? '' : 's'}.
                </div>
              ) : mode === 'register' ? (
                <div className="muted">Password must be at least 8 characters.</div>
              ) : null}
              {error ? <div className="alert error">{error}</div> : null}
              <button className="primary" type="submit" disabled={loading || isLoginCooldownActive}>
                {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`theme-shell ${theme === 'light' ? 'theme-light' : 'theme-dark'}`}>
      <div className="shell app-shell">
        <header className="topbar card">
          <div>
            <div className="brand-lock">SecureDBMS</div>
            <div className="muted">Logged in as {username}</div>
          </div>
          <div className="topbar-actions">
            <button className="ghost" onClick={toggleTheme} type="button">
              {theme === 'dark' ? 'Light theme' : 'Dark theme'}
            </button>
            <button className="primary" onClick={() => setShowCreateForm((current) => !current)} type="button">
              New file
            </button>
            <button className="ghost" onClick={handleLogout} type="button">
              Logout
            </button>
          </div>
        </header>

      {error ? <div className="alert error">{error}</div> : null}

      {showCreateForm ? (
        <div className="card panel create-panel">
          <div className="panel-heading">
            <div>
              <div className="eyebrow">Add file</div>
              <h3>Encrypt a new file</h3>
            </div>
            <button className="ghost" type="button" onClick={() => setShowCreateForm(false)}>
              Close
            </button>
          </div>
          <form onSubmit={handleCreate} className="stack">
            <label>
              File name
              <input
                value={createForm.filename}
                onChange={(event) => setCreateForm({ ...createForm, filename: event.target.value })}
                placeholder="notes.txt"
              />
            </label>
            <label>
              Content
              <textarea
                value={createForm.content}
                onChange={(event) => setCreateForm({ ...createForm, content: event.target.value })}
                rows={8}
                placeholder="Write the secret you want to encrypt..."
              />
            </label>
            <button className="primary" type="submit" disabled={loading}>
              Encrypt & Save
            </button>
          </form>
        </div>
      ) : null}

      <div className="card panel library-panel">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">Encrypted files</div>
            <h3>File list</h3>
          </div>
          <div className="muted">{files.length} files</div>
        </div>

        <label>
          Search
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filter by filename" />
        </label>

        <div className="file-list">
          {filteredFiles.length === 0 ? (
            <div className="empty-state">No matching files found.</div>
          ) : (
            filteredFiles.map((file) => (
              <div key={file.filename} className={file.filename === selectedFile ? 'file-row active' : 'file-row'}>
                <button className="file-row-main" onClick={() => selectFile(file.filename, 'view')} type="button">
                  <div>
                    <strong>{file.filename}</strong>
                    <span>Created {file.created_at}</span>
                  </div>
                  <small>Updated {file.updated_at}</small>
                </button>
                <div className="row-actions">
                  <button className="ghost small" type="button" onClick={() => selectFile(file.filename, 'view')}>
                    View
                  </button>
                  <button className="secondary small" type="button" onClick={() => void showEncryptedView(file.filename)}>
                    Encrypted
                  </button>
                  <button className="secondary small" type="button" onClick={() => selectFile(file.filename, 'update')}>
                    Edit
                  </button>
                  <button className="danger small" type="button" onClick={() => selectFile(file.filename, 'delete')}>
                    Remove
                  </button>
                </div>

                {selectedFile === file.filename && composer === 'view' ? (
                  <div className="inline-panel">
                    {preview ? (
                      <>
                        <div className="meta-grid">
                          <span>Created {preview.created_at}</span>
                          <span>Updated {preview.updated_at}</span>
                        </div>
                        <pre className="preview-content slim-preview">{preview.content}</pre>
                      </>
                    ) : (
                      <div className="empty-state">Decrypting file…</div>
                    )}
                  </div>
                ) : null}

                {selectedFile === file.filename && composer === 'encrypted' ? (
                  <div className="inline-panel">
                    {encryptedPreview ? (
                      <>
                        <div className="meta-grid">
                          <span>Ciphertext (base64)</span>
                          <span>IV (base64)</span>
                          <span>Tag (base64)</span>
                        </div>
                        <pre className="preview-content slim-preview encrypted-preview">{encryptedPreview.ciphertext}

IV: {encryptedPreview.iv}

TAG: {encryptedPreview.tag}</pre>
                      </>
                    ) : (
                      <div className="empty-state">Loading encrypted data…</div>
                    )}
                  </div>
                ) : null}

                {selectedFile === file.filename && composer === 'update' ? (
                  <form onSubmit={handleUpdate} className="stack inline-panel">
                    <label>
                      New content
                      <textarea
                        value={updateContent}
                        onChange={(event) => setUpdateContent(event.target.value)}
                        rows={6}
                      />
                    </label>
                    <div className="row-actions compact-actions">
                      <button className="ghost small" type="button" onClick={() => selectFile(file.filename, 'view')}>
                        View
                      </button>
                      <button className="danger small" type="submit" disabled={loading || !selectedFile}>
                        Save changes
                      </button>
                    </div>
                  </form>
                ) : null}

                {selectedFile === file.filename && composer === 'delete' ? (
                  <form onSubmit={handleDelete} className="stack inline-panel danger-zone">
                    <label className="checkbox-row">
                      <input type="checkbox" checked={deleteConfirmed} onChange={(event) => setDeleteConfirmed(event.target.checked)} />
                      I understand this action is permanent.
                    </label>
                    <div className="row-actions compact-actions">
                      <button className="ghost small" type="button" onClick={() => selectFile(file.filename, 'view')}>
                        View
                      </button>
                      <button className="danger small" type="submit" disabled={loading || !deleteConfirmed}>
                        Delete file
                      </button>
                    </div>
                  </form>
                ) : null}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
    </div>
  );
}
