import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  FileText,
  KeyRound,
  Loader2,
  LogOut,
  MessageSquareText,
  Plus,
  RefreshCw,
  Search,
  Send,
  UploadCloud,
  User,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const ACCESS_TOKEN_KEY = 'pdf-chatbot-access-token';
const USER_KEY = 'pdf-chatbot-user';

const initialMessages = [
  {
    id: 'welcome',
    role: 'assistant',
    content: 'Upload một file PDF đã xử lý, chọn tài liệu, rồi hỏi nội dung trong tài liệu đó.',
    sources: [],
  },
];

function readStoredJson(key) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function formatBytes(value) {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatStatus(status) {
  const labels = {
    pending: 'Đang chờ',
    processing: 'Đang xử lý',
    processed: 'Sẵn sàng',
    failed: 'Lỗi',
  };
  return labels[status] || status || 'Không rõ';
}

function statusClass(status) {
  if (status === 'processed') return 'bg-emerald-50 text-emerald-700 ring-emerald-100';
  if (status === 'failed') return 'bg-rose-50 text-rose-700 ring-rose-100';
  return 'bg-amber-50 text-amber-700 ring-amber-100';
}

async function parseResponse(response) {
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed with status ${response.status}`);
  }
  return data;
}

function App() {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN_KEY) || '');
  const [user, setUser] = useState(() => readStoredJson(USER_KEY));
  const [authMode, setAuthMode] = useState('login');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authNewPassword, setAuthNewPassword] = useState('');
  const [authOtp, setAuthOtp] = useState('');
  const [authMessage, setAuthMessage] = useState('');
  const [isAuthLoading, setIsAuthLoading] = useState(false);

  const [notebooks, setNotebooks] = useState([]);
  const [selectedNotebookId, setSelectedNotebookId] = useState('');
  const [newNotebookTitle, setNewNotebookTitle] = useState('');
  const [isNotebookLoading, setIsNotebookLoading] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [messages, setMessages] = useState(initialMessages);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState('');
  const [lastAnswer, setLastAnswer] = useState(null);
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  const selectedDocument = documents.find((item) => item.id === selectedDocumentId) || null;
  const selectedNotebook = notebooks.find((item) => item.id === selectedNotebookId) || null;

  const filteredDocuments = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) return documents;
    return documents.filter((item) => item.original_file_name.toLowerCase().includes(normalized));
  }, [documents, search]);

  function authHeaders() {
    return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  }

  async function apiFetch(path, options = {}) {
    return fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...authHeaders(),
        ...(options.headers || {}),
      },
    }).then(parseResponse);
  }

  function persistSession(token, nextUser) {
    setAccessToken(token);
    setUser(nextUser);
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
  }

  function logout() {
    setAccessToken('');
    setUser(null);
    setNotebooks([]);
    setSelectedNotebookId('');
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setMessages(initialMessages);
    setLastAnswer(null);
    loadDocuments('');
  }

  useEffect(() => {
    if (accessToken) {
      loadMe();
      loadNotebooks();
    } else {
      loadDocuments('');
    }
  }, [accessToken]);

  useEffect(() => {
    if (accessToken) {
      loadDocuments(selectedNotebookId);
    }
  }, [selectedNotebookId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAsking]);

  async function loadMe() {
    try {
      const data = await apiFetch('/api/auth/me');
      setUser(data);
      localStorage.setItem(USER_KEY, JSON.stringify(data));
    } catch (err) {
      setError(err.message);
      logout();
    }
  }

  async function loadNotebooks() {
    setIsNotebookLoading(true);
    setError('');
    try {
      const data = await apiFetch('/api/notebooks/');
      setNotebooks(data);
      setSelectedNotebookId((current) => current || data[0]?.id || '');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsNotebookLoading(false);
    }
  }

  async function createNotebook(event) {
    event.preventDefault();
    const title = newNotebookTitle.trim();
    if (!title) return;
    setIsNotebookLoading(true);
    setError('');
    try {
      const created = await apiFetch('/api/notebooks/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      setNotebooks((current) => [created, ...current]);
      setSelectedNotebookId(created.id);
      setNewNotebookTitle('');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsNotebookLoading(false);
    }
  }

  async function loadDocuments(notebookId = selectedNotebookId) {
    setIsLoadingDocuments(true);
    setError('');
    try {
      const params = accessToken && notebookId ? `?notebook_id=${encodeURIComponent(notebookId)}` : '';
      const data = await apiFetch(`/api/documents/${params}`);
      setDocuments(data);
      setSelectedDocumentId((current) => {
        if (data.some((item) => item.id === current)) return current;
        return data.find((item) => item.status === 'processed')?.id || data[0]?.id || '';
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  async function requestRegister(event) {
    event.preventDefault();
    setIsAuthLoading(true);
    setAuthMessage('');
    setError('');
    try {
      const data = await apiFetch('/api/auth/register/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: authEmail,
          password: authPassword,
          confirm_password: authPassword,
        }),
      });
      setAuthMode('verify');
      setAuthMessage(data.message || 'OTP đã được gửi tới email.');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAuthLoading(false);
    }
  }

  async function verifyRegister(event) {
    event.preventDefault();
    setIsAuthLoading(true);
    setAuthMessage('');
    setError('');
    try {
      const data = await apiFetch('/api/auth/register/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, otp: authOtp }),
      });
      setAuthMode('login');
      setAuthOtp('');
      setAuthMessage(data.message || 'Xác thực thành công. Bạn có thể đăng nhập.');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAuthLoading(false);
    }
  }

  async function requestPasswordReset(event) {
    event.preventDefault();
    setIsAuthLoading(true);
    setAuthMessage('');
    setError('');
    try {
      const data = await apiFetch('/api/auth/forgot-password/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail }),
      });
      setAuthMode('reset-verify');
      setAuthMessage(data.message || 'OTP đặt lại mật khẩu đã được gửi tới email.');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAuthLoading(false);
    }
  }

  async function verifyPasswordReset(event) {
    event.preventDefault();
    setIsAuthLoading(true);
    setAuthMessage('');
    setError('');
    try {
      const data = await apiFetch('/api/auth/forgot-password/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: authEmail,
          otp: authOtp,
          new_password: authNewPassword,
          confirm_new_password: authNewPassword,
        }),
      });
      setAuthMode('login');
      setAuthOtp('');
      setAuthNewPassword('');
      setAuthMessage(data.message || 'Đặt lại mật khẩu thành công. Bạn có thể đăng nhập.');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAuthLoading(false);
    }
  }

  async function login(event) {
    event.preventDefault();
    setIsAuthLoading(true);
    setAuthMessage('');
    setError('');
    try {
      const data = await apiFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      persistSession(data.access_token, data.user);
      setAuthPassword('');
      setAuthMessage('Đăng nhập thành công.');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAuthLoading(false);
    }
  }

  async function uploadPdf(file) {
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Chỉ hỗ trợ file PDF.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    if (accessToken && selectedNotebookId) {
      formData.append('notebook_id', selectedNotebookId);
    }

    setIsUploading(true);
    setError('');
    try {
      const uploaded = await apiFetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });
      setDocuments((current) => [uploaded, ...current.filter((item) => item.id !== uploaded.id)]);
      setSelectedDocumentId(uploaded.id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Đã upload và xử lý "${uploaded.original_file_name}". Bạn có thể hỏi tài liệu này ngay.`,
          sources: [],
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function askQuestion(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isAsking) return;

    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: 'user',
        content: trimmed,
        sources: [],
      },
    ]);
    setQuery('');
    setIsAsking(true);
    setError('');

    try {
      const answer = await apiFetch('/api/chatbot/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: trimmed,
          notebook_id: accessToken ? selectedNotebookId || null : null,
          document_id: selectedDocument?.status === 'processed' ? selectedDocument.id : null,
          top_k: 5,
          save_history: Boolean(accessToken),
        }),
      });

      setLastAnswer(answer);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: answer.answer,
          sources: answer.sources || [],
        },
      ]);
    } catch (err) {
      setError(err.message);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Không trả lời được câu hỏi: ${err.message}`,
          sources: [],
          isError: true,
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  }

  const authSubmit =
    authMode === 'login'
      ? login
      : authMode === 'register'
        ? requestRegister
        : authMode === 'verify'
          ? verifyRegister
          : authMode === 'reset'
            ? requestPasswordReset
            : verifyPasswordReset;

  return (
    <div className="min-h-screen bg-zinc-100 text-zinc-950">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between lg:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-600 text-white">
              <MessageSquareText size={22} />
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight sm:text-xl">PDF Chatbot</h1>
              <p className="text-sm text-zinc-500">Upload PDF, hỏi đáp theo nội dung đã trích xuất</p>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-600">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Backend {API_BASE_URL.replace(/^https?:\/\//, '')}
            </div>
            {user && (
              <button
                type="button"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-semibold text-zinc-700 hover:bg-zinc-50"
                onClick={logout}
              >
                <LogOut size={16} />
                Đăng xuất {user.name || user.email}
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[320px_minmax(0,1fr)_320px] lg:px-6">
        <aside className="space-y-4">
          {!user && (
            <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <div className="flex items-center gap-2">
                <KeyRound size={18} className="text-teal-700" />
                <h2 className="font-bold">Tài khoản</h2>
              </div>
              <form className="mt-4 space-y-3" onSubmit={authSubmit}>
                <input
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                  value={authEmail}
                  onChange={(event) => setAuthEmail(event.target.value)}
                  placeholder="Email"
                  type="email"
                  required
                />
                {(authMode === 'login' || authMode === 'register') && (
                  <input
                    className="w-full rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                    value={authPassword}
                    onChange={(event) => setAuthPassword(event.target.value)}
                    placeholder="Mật khẩu"
                    type="password"
                    minLength={8}
                    required
                  />
                )}
                {(authMode === 'verify' || authMode === 'reset-verify') && (
                  <input
                    className="w-full rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                    value={authOtp}
                    onChange={(event) => setAuthOtp(event.target.value)}
                    placeholder="Mã OTP"
                    minLength={4}
                    maxLength={12}
                    required
                  />
                )}
                {authMode === 'reset-verify' && (
                  <input
                    className="w-full rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                    value={authNewPassword}
                    onChange={(event) => setAuthNewPassword(event.target.value)}
                    placeholder="Mật khẩu mới"
                    type="password"
                    minLength={8}
                    required
                  />
                )}
                <button
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-teal-700 disabled:bg-zinc-300"
                  disabled={isAuthLoading}
                >
                  {isAuthLoading && <Loader2 className="animate-spin" size={17} />}
                  {authMode === 'login'
                    ? 'Đăng nhập'
                    : authMode === 'register'
                      ? 'Gửi OTP đăng ký'
                      : authMode === 'verify'
                        ? 'Xác thực OTP'
                        : authMode === 'reset'
                          ? 'Gửi OTP đặt lại'
                          : 'Đặt lại mật khẩu'}
                </button>
              </form>
              <div className="mt-3 flex flex-wrap gap-2 text-sm">
                <button className="font-semibold text-teal-700" onClick={() => setAuthMode('login')}>
                  Đăng nhập
                </button>
                <span className="text-zinc-300">/</span>
                <button className="font-semibold text-teal-700" onClick={() => setAuthMode('register')}>
                  Đăng ký
                </button>
                <span className="text-zinc-300">/</span>
                <button className="font-semibold text-teal-700" onClick={() => setAuthMode('reset')}>
                  Quên mật khẩu
                </button>
              </div>
              {authMessage && <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{authMessage}</p>}
            </section>
          )}

          {user && (
            <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="font-bold">Notebook</h2>
                  <p className="text-sm text-zinc-500">{notebooks.length} workspace cá nhân</p>
                </div>
                <button
                  className="rounded-lg border border-zinc-200 p-2 text-zinc-600 hover:bg-zinc-50"
                  onClick={loadNotebooks}
                  disabled={isNotebookLoading}
                  aria-label="Tải lại notebook"
                >
                  <RefreshCw size={18} className={isNotebookLoading ? 'animate-spin' : ''} />
                </button>
              </div>
              <select
                className="mt-4 w-full rounded-lg border border-zinc-200 px-3 py-2.5 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                value={selectedNotebookId}
                onChange={(event) => setSelectedNotebookId(event.target.value)}
              >
                {notebooks.map((notebook) => (
                  <option key={notebook.id} value={notebook.id}>
                    {notebook.title || 'Notebook không tên'}
                  </option>
                ))}
              </select>
              <form className="mt-3 flex gap-2" onSubmit={createNotebook}>
                <input
                  className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                  value={newNotebookTitle}
                  onChange={(event) => setNewNotebookTitle(event.target.value)}
                  placeholder="Notebook mới"
                />
                <button className="rounded-lg bg-zinc-950 p-2 text-white disabled:bg-zinc-300" disabled={!newNotebookTitle.trim()}>
                  <Plus size={18} />
                </button>
              </form>
            </section>
          )}

          <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="font-bold">Tài liệu PDF</h2>
                <p className="text-sm text-zinc-500">{documents.length} file {selectedNotebook ? `trong ${selectedNotebook.title || 'notebook'}` : 'public'}</p>
              </div>
              <button
                className="rounded-lg border border-zinc-200 p-2 text-zinc-600 hover:bg-zinc-50"
                onClick={() => loadDocuments()}
                disabled={isLoadingDocuments}
                aria-label="Tải lại tài liệu"
              >
                <RefreshCw size={18} className={isLoadingDocuments ? 'animate-spin' : ''} />
              </button>
            </div>

            <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-teal-300 bg-teal-50 px-4 py-6 text-center hover:bg-teal-100">
              {isUploading ? <Loader2 className="animate-spin text-teal-700" size={26} /> : <UploadCloud className="text-teal-700" size={28} />}
              <span className="mt-2 text-sm font-semibold text-teal-900">{isUploading ? 'Đang upload và xử lý...' : 'Chọn PDF để upload'}</span>
              <span className="mt-1 text-xs text-teal-700">Backend sẽ lưu, trích text, chunk và index vector</span>
              <input
                ref={fileInputRef}
                className="hidden"
                type="file"
                accept="application/pdf,.pdf"
                disabled={isUploading}
                onChange={(event) => uploadPdf(event.target.files?.[0])}
              />
            </label>

            <div className="relative mt-4">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={17} />
              <input
                className="w-full rounded-lg border border-zinc-200 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Tìm file..."
              />
            </div>
          </section>

          <section className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
            {filteredDocuments.map((document) => (
              <button
                key={document.id}
                className={`w-full rounded-lg border p-3 text-left shadow-sm transition ${
                  selectedDocumentId === document.id ? 'border-teal-500 bg-white ring-4 ring-teal-100' : 'border-zinc-200 bg-white hover:border-zinc-300'
                }`}
                onClick={() => setSelectedDocumentId(document.id)}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 rounded-lg bg-zinc-100 p-2 text-zinc-700">
                    <FileText size={18} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{document.original_file_name}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {document.total_pages || 0} trang · {document.total_chunks || 0} chunks · {formatBytes(document.file_size_bytes)}
                    </p>
                    <span className={`mt-2 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${statusClass(document.status)}`}>
                      {formatStatus(document.status)}
                    </span>
                  </div>
                </div>
              </button>
            ))}
            {!isLoadingDocuments && filteredDocuments.length === 0 && (
              <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-500">Chưa có PDF nào. Upload một file để bắt đầu.</div>
            )}
          </section>
        </aside>

        <section className="flex min-h-[680px] flex-col rounded-lg border border-zinc-200 bg-white shadow-sm">
          <div className="border-b border-zinc-200 px-4 py-3">
            <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-zinc-500">Đang hỏi</p>
                <h2 className="truncate text-lg font-bold">{selectedDocument?.original_file_name || 'Toàn bộ tài liệu hiện có'}</h2>
              </div>
              {selectedDocument && (
                <span className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusClass(selectedDocument.status)}`}>
                  {formatStatus(selectedDocument.status)}
                </span>
              )}
            </div>
          </div>

          {error && (
            <div className="mx-4 mt-4 flex gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
              <AlertCircle className="mt-0.5 shrink-0" size={18} />
              <span>{error}</span>
            </div>
          )}

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {message.role === 'assistant' && (
                  <div className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${message.isError ? 'bg-rose-100 text-rose-700' : 'bg-teal-100 text-teal-700'}`}>
                    <Bot size={18} />
                  </div>
                )}
                <div className={`max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'bg-zinc-950 text-white' : message.isError ? 'bg-rose-50 text-rose-900' : 'bg-zinc-100 text-zinc-900'}`}>
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.sources?.length > 0 && <p className="mt-2 text-xs font-semibold text-zinc-500">{message.sources.length} nguồn liên quan</p>}
                </div>
                {message.role === 'user' && (
                  <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white">
                    <User size={17} />
                  </div>
                )}
              </div>
            ))}
            {isAsking && (
              <div className="flex gap-3">
                <div className="mt-1 flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 text-teal-700">
                  <Bot size={18} />
                </div>
                <div className="rounded-lg bg-zinc-100 px-4 py-3 text-sm text-zinc-600">
                  <Loader2 className="inline animate-spin" size={16} /> Đang truy xuất đoạn liên quan và tạo câu trả lời...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form className="border-t border-zinc-200 p-4" onSubmit={askQuestion}>
            <div className="flex gap-2">
              <input
                className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-3 text-sm outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ví dụ: Tóm tắt tài liệu này trong 5 ý chính..."
                disabled={isAsking}
              />
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-3 text-sm font-bold text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
                disabled={!query.trim() || isAsking}
              >
                {isAsking ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                <span className="hidden sm:inline">Gửi</span>
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-4">
          <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="text-emerald-600" size={19} />
              <h2 className="font-bold">Trạng thái</h2>
            </div>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Tài khoản</dt>
                <dd className="text-right font-semibold">{user ? user.email : 'Khách'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Notebook</dt>
                <dd className="text-right font-semibold">{selectedNotebook?.title || 'Public'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Tài liệu chọn</dt>
                <dd className="text-right font-semibold">{selectedDocument ? formatStatus(selectedDocument.status) : 'Chưa chọn'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Nguồn truy xuất</dt>
                <dd className="text-right font-semibold">{lastAnswer?.retriever || 'Chưa hỏi'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Model trả lời</dt>
                <dd className="text-right font-semibold">{lastAnswer?.generator_model_name || lastAnswer?.generator_provider || 'Chưa hỏi'}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-zinc-500">Độ trễ</dt>
                <dd className="text-right font-semibold">{lastAnswer ? `${Math.round(lastAnswer.total_latency_ms)} ms` : 'N/A'}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
            <h2 className="font-bold">Nguồn trích dẫn</h2>
            <div className="mt-3 max-h-[560px] space-y-3 overflow-y-auto pr-1">
              {(lastAnswer?.sources || []).map((source, index) => (
                <article key={`${source.chunk_id}-${index}`} className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-semibold">{source.original_file_name}</p>
                    <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-zinc-600 ring-1 ring-zinc-200">#{index + 1}</span>
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    Trang {source.page_from || '?'}{source.page_to && source.page_to !== source.page_from ? `-${source.page_to}` : ''} · chunk {source.chunk_index}
                  </p>
                  <p className="mt-2 line-clamp-5 text-sm leading-6 text-zinc-700">{source.content}</p>
                </article>
              ))}
              {!lastAnswer?.sources?.length && <p className="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-500">Nguồn liên quan sẽ hiện sau khi chatbot trả lời.</p>}
            </div>
          </section>
        </aside>
      </main>
    </div>
  );
}

export default App;
