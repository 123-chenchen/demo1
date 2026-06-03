import { useEffect, useMemo, useRef, useState } from 'react';

import {
  ACCESS_TOKEN_KEY,
  AUTH_DISABLED,
  USER_KEY,
  apiFetch,
  clearStoredSession,
  initialMessages,
  persistStoredSession,
  readStoredJson,
} from './api.js';

const guestUser = {
  email: 'guest@local',
  name: 'Guest',
  isGuest: true,
};

export function usePdfChatbotApp() {
  const [accessToken, setAccessToken] = useState(() => (AUTH_DISABLED ? '' : localStorage.getItem(ACCESS_TOKEN_KEY) || ''));
  const [user, setUser] = useState(() => (AUTH_DISABLED ? null : readStoredJson(USER_KEY)));
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
  const effectiveUser = user || (AUTH_DISABLED ? guestUser : null);
  const isAuthenticated = AUTH_DISABLED || Boolean(accessToken && user);

  const filteredDocuments = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) return documents;
    return documents.filter((item) => item.original_file_name.toLowerCase().includes(normalized));
  }, [documents, search]);

  useEffect(() => {
    if (accessToken) {
      loadMe();
      loadNotebooks();
    } else if (AUTH_DISABLED) {
      setUser(null);
      setNotebooks([]);
      setSelectedNotebookId('');
      setDocuments([]);
      setSelectedDocumentId('');
      setLastAnswer(null);
      loadDocuments('');
    } else {
      setUser(null);
      setNotebooks([]);
      setSelectedNotebookId('');
      setDocuments([]);
      setSelectedDocumentId('');
      setLastAnswer(null);
    }
  }, [accessToken]);

  useEffect(() => {
    if (accessToken || AUTH_DISABLED) {
      loadDocuments(selectedNotebookId);
    }
  }, [selectedNotebookId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAsking]);

  function authorizedFetch(path, options = {}) {
    return apiFetch(path, options, accessToken);
  }

  function persistSession(token, nextUser) {
    setAccessToken(token);
    setUser(nextUser);
    persistStoredSession(token, nextUser);
  }

  function logout() {
    setAccessToken('');
    setUser(null);
    setNotebooks([]);
    setSelectedNotebookId('');
    setDocuments([]);
    setSelectedDocumentId('');
    setSearch('');
    setQuery('');
    setError('');
    clearStoredSession();
    setMessages(initialMessages);
    setLastAnswer(null);
  }

  function switchAuthMode(nextMode) {
    setAuthMode(nextMode);
    setAuthMessage('');
    setError('');
  }

  async function loadMe() {
    try {
      const data = await authorizedFetch('/api/auth/me');
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
      const data = await authorizedFetch('/api/notebooks/');
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
      const created = await authorizedFetch('/api/notebooks/', {
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
    if (!accessToken && !AUTH_DISABLED) return;

    setIsLoadingDocuments(true);
    setError('');
    try {
      const params = notebookId ? `?notebook_id=${encodeURIComponent(notebookId)}` : '';
      const data = await authorizedFetch(`/api/documents/${params}`);
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
      const data = await authorizedFetch('/api/auth/register/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: authEmail,
          password: authPassword,
          confirm_password: authPassword,
        }),
      });
      setAuthMode('verify');
      setAuthMessage(data.message || 'The OTP has been sent to your email.');
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
      const data = await authorizedFetch('/api/auth/register/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, otp: authOtp }),
      });
      setAuthMode('login');
      setAuthOtp('');
      setAuthMessage(data.message || 'Verification completed. You can sign in now.');
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
      const data = await authorizedFetch('/api/auth/forgot-password/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail }),
      });
      setAuthMode('reset-verify');
      setAuthMessage(data.message || 'The password reset OTP has been sent to your email.');
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
      const data = await authorizedFetch('/api/auth/forgot-password/verify', {
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
      setAuthMessage(data.message || 'Password reset completed. You can sign in now.');
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
      const data = await authorizedFetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      persistSession(data.access_token, data.user);
      setAuthPassword('');
      setAuthMessage('Signed in successfully.');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAuthLoading(false);
    }
  }

  async function uploadPdf(file) {
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    if (selectedNotebookId) {
      formData.append('notebook_id', selectedNotebookId);
    }

    setIsUploading(true);
    setError('');
    try {
      const uploaded = await authorizedFetch('/api/documents/upload', {
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
          content: `Uploaded and processed "${uploaded.original_file_name}". You can ask questions about this document now.`,
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
      const answer = await authorizedFetch('/api/chatbot/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: trimmed,
          notebook_id: selectedNotebookId || null,
          document_id: selectedDocument?.status === 'processed' ? selectedDocument.id : null,
          top_k: 5,
          save_history: true,
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
          content: `Could not answer the question: ${err.message}`,
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

  return {
    isAuthenticated,
    isAuthDisabled: AUTH_DISABLED,
    auth: {
      mode: authMode,
      email: authEmail,
      password: authPassword,
      newPassword: authNewPassword,
      otp: authOtp,
      message: authMessage,
      error,
      isLoading: isAuthLoading,
      onSubmit: authSubmit,
      onModeChange: switchAuthMode,
      onEmailChange: setAuthEmail,
      onPasswordChange: setAuthPassword,
      onNewPasswordChange: setAuthNewPassword,
      onOtpChange: setAuthOtp,
    },
    header: {
      user: effectiveUser,
      isAuthDisabled: AUTH_DISABLED,
      onLogout: logout,
    },
    notebooks: {
      notebooks,
      selectedNotebookId,
      newNotebookTitle,
      isNotebookLoading,
      onReload: loadNotebooks,
      onSelectNotebook: setSelectedNotebookId,
      onNewNotebookTitleChange: setNewNotebookTitle,
      onCreateNotebook: createNotebook,
    },
    documents: {
      documents,
      filteredDocuments,
      selectedDocumentId,
      selectedNotebook,
      search,
      isLoadingDocuments,
      isUploading,
      fileInputRef,
      onReload: () => loadDocuments(),
      onUpload: uploadPdf,
      onSearchChange: setSearch,
      onSelectDocument: setSelectedDocumentId,
    },
    chat: {
      selectedDocument,
      error,
      messages,
      isAsking,
      query,
      chatEndRef,
      onSubmit: askQuestion,
      onQueryChange: setQuery,
    },
    status: {
      user: effectiveUser,
      selectedNotebook,
      selectedDocument,
      lastAnswer,
    },
  };
}
