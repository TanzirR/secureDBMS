export type AuthResponse = {
  access_token: string;
  username: string;
};

export type FileItem = {
  filename: string;
  created_at: string;
  updated_at: string;
};

export type FileDetail = FileItem & {
  content: string;
};

export type FileEncryptedDetail = FileItem & {
  ciphertext: string;
  iv: string;
  tag: string;
};

export type FileListResponse = {
  count: number;
  files: FileItem[];
};

export class ApiError extends Error {
  status: number;
  retryAfterSeconds: number | null;

  constructor(message: string, status: number, retryAfterSeconds: number | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

function getToken() {
  return localStorage.getItem('securevault_token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');

  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload?.detail || 'Request failed';
    const retryAfterHeader = response.headers.get('retry-after');
    const retryAfterSeconds = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : null;
    throw new ApiError(message, response.status, Number.isFinite(retryAfterSeconds) ? retryAfterSeconds : null);
  }

  return payload as T;
}

export async function login(username: string, password: string) {
  const payload = await request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  localStorage.setItem('securevault_token', payload.access_token);
  localStorage.setItem('securevault_username', payload.username);
  return payload;
}

export async function register(username: string, password: string) {
  const payload = await request<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  localStorage.setItem('securevault_token', payload.access_token);
  localStorage.setItem('securevault_username', payload.username);
  return payload;
}

export async function getFiles() {
  return request<FileListResponse>('/files');
}

export async function createFile(filename: string, content: string) {
  return request<FileDetail>('/files', {
    method: 'POST',
    body: JSON.stringify({ filename, content }),
  });
}

export async function getFile(filename: string) {
  return request<FileDetail>(`/files/${encodeURIComponent(filename)}`);
}

export async function getEncryptedFile(filename: string) {
  return request<FileEncryptedDetail>(`/files/${encodeURIComponent(filename)}/encrypted`);
}

export async function updateFile(filename: string, content: string) {
  return request<FileDetail>(`/files/${encodeURIComponent(filename)}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

export async function deleteFile(filename: string) {
  return request<{ message: string }>(`/files/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
}

export function logout() {
  localStorage.removeItem('securevault_token');
  localStorage.removeItem('securevault_username');
}

export function getStoredSession() {
  return {
    token: localStorage.getItem('securevault_token'),
    username: localStorage.getItem('securevault_username'),
  };
}
