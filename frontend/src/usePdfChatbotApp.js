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
import { displayDocumentListTitle } from './documentTitles.js';

const guestUser = {
  email: 'guest@local',
  name: 'Guest',
  isGuest: true,
};

const defaultUserSettings = {
  language: 'en',
  theme: 'light',
};
const SETTINGS_STORAGE_PREFIX = 'pdf-chatbot-settings:';
const WORKSPACE_STORAGE_PREFIX = 'pdf-chatbot-workspace:';

export function usePdfChatbotApp() {
  const initialSessionUser = AUTH_DISABLED ? null : readStoredJson(USER_KEY);
  const initialWorkspace = readStoredWorkspace(AUTH_DISABLED ? guestUser : initialSessionUser);
  const [accessToken, setAccessToken] = useState(() => (AUTH_DISABLED ? '' : localStorage.getItem(ACCESS_TOKEN_KEY) || ''));
  const [user, setUser] = useState(() => initialSessionUser);
  const [userSettings, setUserSettings] = useState(() => resolveStoredSettings(initialSessionUser));
  const [settingsMessage, setSettingsMessage] = useState('');
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authNewPassword, setAuthNewPassword] = useState('');
  const [authOtp, setAuthOtp] = useState('');
  const [authMessage, setAuthMessage] = useState('');
  const [isAuthLoading, setIsAuthLoading] = useState(false);

  const [notebooks, setNotebooks] = useState([]);
  const [selectedNotebookId, setSelectedNotebookId] = useState(() => initialWorkspace.selectedNotebookId || '');
  const [newNotebookTitle, setNewNotebookTitle] = useState('');
  const [isNotebookLoading, setIsNotebookLoading] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState(() => initialWorkspace.selectedDocumentId || '');
  const [selectedDocumentIds, setSelectedDocumentIds] = useState(() => initialWorkspace.selectedDocumentIds || []);
  const [messages, setMessages] = useState(() => normalizeStoredMessages(initialWorkspace.messages));
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const [suggestionTitle, setSuggestionTitle] = useState('');
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState(() => initialWorkspace.activeSessionId || '');
  const [chatSessions, setChatSessions] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState('');
  const [lastAnswer, setLastAnswer] = useState(null);
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);

  const selectedDocuments = selectedDocumentIds
    .map((documentId) => documents.find((item) => item.id === documentId))
    .filter(Boolean);
  const readySelectedDocuments = selectedDocuments.filter((document) => document.status === 'processed');
  const selectedDocument = documents.find((item) => item.id === selectedDocumentId) || selectedDocuments[0] || null;
  const selectedNotebook = notebooks.find((item) => item.id === selectedNotebookId) || null;
  const effectiveUser = user || (AUTH_DISABLED ? guestUser : null);
  const isAuthenticated = AUTH_DISABLED || Boolean(accessToken && user);
  const scopeLabel = buildScopeLabel(selectedDocuments);
  const hasReadyScope = readySelectedDocuments.length > 0;

  useEffect(() => {
    if (!effectiveUser) return;
    localStorage.setItem(
      workspaceStorageKey(effectiveUser),
      JSON.stringify({
        selectedNotebookId,
        selectedDocumentId,
        selectedDocumentIds,
        activeSessionId,
        messages,
      })
    );
  }, [
    effectiveUser?.email,
    selectedNotebookId,
    selectedDocumentId,
    selectedDocumentIds.join('|'),
    activeSessionId,
    messages,
  ]);

  const filteredDocuments = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    if (!normalized) return documents;
    return documents.filter((item) => {
      const title = displayDocumentListTitle([item]).toLowerCase();
      return title.includes(normalized) || item.original_file_name.toLowerCase().includes(normalized);
    });
  }, [documents, search]);

  useEffect(() => {
    if (accessToken) {
      loadMe();
      loadNotebooks();
    } else if (AUTH_DISABLED) {
      setUser(null);
      setNotebooks([]);
      setSelectedNotebookId('');
      setLastAnswer(null);
      loadDocuments('');
    } else {
      setUser(null);
      setNotebooks([]);
      setSelectedNotebookId('');
      setDocuments([]);
      setSelectedDocumentId('');
      setSelectedDocumentIds([]);
      setLastAnswer(null);
    }
  }, [accessToken]);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', userSettings.theme === 'dark');
    document.documentElement.dataset.theme = userSettings.theme;
  }, [userSettings.theme]);

  useEffect(() => {
    if (accessToken || AUTH_DISABLED) {
      loadDocuments(selectedNotebookId);
      loadChatSessions(selectedNotebookId);
    }
  }, [selectedNotebookId]);

  useEffect(() => {
    if (!accessToken && !AUTH_DISABLED) return undefined;
    if (!readySelectedDocuments.length) {
      setSuggestedQuestions([]);
      setSuggestionTitle('');
      setIsLoadingSuggestions(false);
      return undefined;
    }

    let cancelled = false;
    setIsLoadingSuggestions(true);

    authorizedFetch('/api/chatbot/suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        notebook_id: selectedNotebookId || null,
        document_ids: readySelectedDocuments.map((document) => document.id),
        language: userSettings.language,
      }),
    })
      .then((data) => {
        if (cancelled) return;
        setSuggestedQuestions(data.questions || []);
        setSuggestionTitle(data.title || '');
        if (readySelectedDocuments.length === 1 && data.title && (data.questions || []).length > 0) {
          const [document] = readySelectedDocuments;
          setDocuments((current) => current.map((item) => {
            if (item.id !== document.id) return item;
            return {
              ...item,
              metadata: {
                ...(item.metadata || {}),
                display_title: data.title,
              },
            };
          }));
        }
      })
      .catch(() => {
        if (cancelled) return;
        setSuggestedQuestions([]);
        setSuggestionTitle('');
      })
      .finally(() => {
        if (!cancelled) setIsLoadingSuggestions(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    accessToken,
    selectedNotebookId,
    selectedDocumentId,
    userSettings.language,
    readySelectedDocuments.map((document) => document.id).join('|'),
  ]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAsking]);

  function authorizedFetch(path, options = {}) {
    return apiFetch(path, options, accessToken);
  }

  function persistSession(token, nextUser) {
    setAccessToken(token);
    setUser(nextUser);
    applyUserSettings(nextUser?.settings, nextUser);
    persistStoredSession(token, nextUser);
  }

  function logout() {
    setAccessToken('');
    setUser(null);
    setNotebooks([]);
    setSelectedNotebookId('');
    setDocuments([]);
    setSelectedDocumentId('');
    setSelectedDocumentIds([]);
    setSearch('');
    setQuery('');
    setError('');
    setSettingsMessage('');
    setActiveSessionId('');
    setChatSessions([]);
    setSuggestedQuestions([]);
    setSuggestionTitle('');
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
      applyUserSettings(data.settings, data);
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
      setSelectedNotebookId((current) => {
        if (current && data.some((notebook) => notebook.id === current)) return current;
        return data[0]?.id || '';
      });
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

  async function deleteNotebook(notebookId = selectedNotebookId) {
    if (!notebookId || AUTH_DISABLED) return;

    setIsNotebookLoading(true);
    setError('');
    try {
      await authorizedFetch(`/api/notebooks/${notebookId}`, { method: 'DELETE' });
      setNotebooks((current) => {
        const next = current.filter((notebook) => notebook.id !== notebookId);
        setSelectedNotebookId((currentNotebookId) => {
          if (currentNotebookId !== notebookId) return currentNotebookId;
          return next[0]?.id || '';
        });
        return next;
      });
      setDocuments([]);
      setSelectedDocumentId('');
      setSelectedDocumentIds([]);
      setActiveSessionId('');
      setChatSessions([]);
      setMessages(initialMessages);
      setLastAnswer(null);
      await loadNotebooks();
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
      const preferredDocumentId = data.find((item) => item.status === 'processed')?.id || data[0]?.id || '';
      setSelectedDocumentIds((current) => {
        const availableIds = new Set(data.map((item) => item.id));
        const kept = current.filter((documentId) => availableIds.has(documentId));
        return kept.length ? kept : preferredDocumentId ? [preferredDocumentId] : [];
      });
      setSelectedDocumentId((current) => {
        if (data.some((item) => item.id === current)) return current;
        return preferredDocumentId;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  async function deleteDocument(documentId) {
    if (!documentId) return;

    setIsLoadingDocuments(true);
    setError('');
    try {
      await authorizedFetch(`/api/documents/${documentId}`, { method: 'DELETE' });
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      setSelectedDocumentIds((current) => current.filter((item) => item !== documentId));
      setSelectedDocumentId((current) => {
        if (current !== documentId) return current;
        const remaining = documents.filter((document) => document.id !== documentId);
        return remaining.find((document) => selectedDocumentIds.includes(document.id))?.id || remaining[0]?.id || '';
      });
      if (lastAnswer?.document_id === documentId || lastAnswer?.document_ids?.includes?.(documentId)) {
        setLastAnswer(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  async function loadChatSessions(notebookId = selectedNotebookId) {
    if (!accessToken || AUTH_DISABLED) {
      setChatSessions([]);
      return;
    }

    setIsLoadingHistory(true);
    setError('');
    try {
      const params = notebookId ? `?notebook_id=${encodeURIComponent(notebookId)}` : '';
      const data = await authorizedFetch(`/api/chat-sessions/${params}`);
      setChatSessions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingHistory(false);
    }
  }

  async function loadChatSession(sessionId) {
    if (!sessionId || !accessToken || AUTH_DISABLED) return;

    setIsLoadingHistory(true);
    setError('');
    try {
      const session = await authorizedFetch(`/api/chat-sessions/${sessionId}`);
      setActiveSessionId(session.id);
      setMessages([
        ...initialMessages,
        ...session.messages.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          sources: message.sources || [],
        })),
      ]);

      const sourceDocumentId = session.messages
        .flatMap((message) => message.sources || [])
        .find((source) => source.document_id)?.document_id;
      const metadataDocumentId = session.messages.find((message) => message.metadata?.document_id)?.metadata?.document_id;
      const metadataDocumentIds = session.messages.flatMap((message) => message.metadata?.document_ids || []);
      const nextDocumentIds = uniqueIds([
        ...session.messages.flatMap((message) => (message.sources || []).map((source) => source.document_id)),
        ...metadataDocumentIds,
        sourceDocumentId,
        metadataDocumentId,
      ]);
      if (nextDocumentIds.length) {
        setSelectedDocumentIds(nextDocumentIds);
        setSelectedDocumentId(String(nextDocumentIds[0]));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingHistory(false);
    }
  }

  async function deleteChatSession(sessionId) {
    if (!sessionId || !accessToken || AUTH_DISABLED) return;

    setIsLoadingHistory(true);
    setError('');
    try {
      await authorizedFetch(`/api/chat-sessions/${sessionId}`, { method: 'DELETE' });
      setChatSessions((current) => current.filter((session) => session.id !== sessionId));
      if (activeSessionId === sessionId) {
        startNewChat();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingHistory(false);
    }
  }

  function startNewChat() {
    setActiveSessionId('');
    setMessages(initialMessages);
    setLastAnswer(null);
    setQuery('');
    setError('');
  }

  function selectDocument(documentId) {
    setSelectedDocumentId(documentId);
    setSelectedDocumentIds((current) => (current.includes(documentId) ? current : [...current, documentId]));
  }

  function toggleDocumentScope(documentId) {
    setSelectedDocumentIds((current) => {
      const next = current.includes(documentId)
        ? current.filter((item) => item !== documentId)
        : [...current, documentId];
      if (!next.length) {
        setSelectedDocumentId('');
      } else if (!next.includes(selectedDocumentId)) {
        setSelectedDocumentId(next[0]);
      } else {
        setSelectedDocumentId(documentId);
      }
      return next;
    });
  }

  function submitSuggestedQuestion(question) {
    setQuery(question);
    return askQuestion(null, question);
  }

  function applyUserSettings(rawSettings, owner = effectiveUser) {
    const nextSettings = resolveStoredSettings(owner, rawSettings);
    setUserSettings(nextSettings);
    localStorage.setItem(settingsStorageKey(owner), JSON.stringify(nextSettings));
  }

  async function updateUserSettings(partialSettings) {
    const nextSettings = normalizeUserSettings({ ...userSettings, ...partialSettings });
    const previousSettings = userSettings;
    setUserSettings(nextSettings);
    localStorage.setItem(settingsStorageKey(effectiveUser), JSON.stringify(nextSettings));
    setSettingsMessage('');

    if (AUTH_DISABLED) {
      setSettingsMessage(nextSettings.language === 'vi' ? 'Đã lưu cài đặt.' : 'Settings saved.');
      return;
    }

    setIsSavingSettings(true);
    setError('');
    try {
      const savedSettings = nextSettings;
      applyUserSettings(savedSettings, effectiveUser);
      setUser((current) => {
        if (!current) return current;
        const nextUser = { ...current, settings: normalizeUserSettings(savedSettings) };
        localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
        return nextUser;
      });
      setSettingsMessage(savedSettings.language === 'vi' ? 'Đã lưu cài đặt.' : 'Settings saved.');
    } catch (err) {
      setUserSettings(previousSettings);
      localStorage.setItem(settingsStorageKey(effectiveUser), JSON.stringify(previousSettings));
      setError(err.message);
    } finally {
      setIsSavingSettings(false);
    }
  }

  async function updateLocalUserSettings(partialSettings) {
    const nextSettings = normalizeUserSettings({ ...userSettings, ...partialSettings });
    setIsSavingSettings(true);
    setError('');
    setSettingsMessage('');
    setUserSettings(nextSettings);
    localStorage.setItem(settingsStorageKey(effectiveUser), JSON.stringify(nextSettings));
    setUser((current) => {
      if (!current) return current;
      const nextUser = { ...current, settings: nextSettings };
      localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
      return nextUser;
    });
    setSettingsMessage(nextSettings.language === 'vi' ? 'Đã lưu cài đặt.' : 'Settings saved.');
    setIsSavingSettings(false);
  }

  async function changePassword(payload) {
    if (AUTH_DISABLED) return;
    setIsChangingPassword(true);
    setSettingsMessage('');
    setError('');
    try {
      const data = await authorizedFetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      setSettingsMessage(data.message || 'Password changed.');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsChangingPassword(false);
    }
  }

  async function deleteAccount(payload) {
    if (AUTH_DISABLED) return;
    setIsDeletingAccount(true);
    setSettingsMessage('');
    setError('');
    try {
      await authorizedFetch('/api/auth/account', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      logout();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsDeletingAccount(false);
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

  async function uploadPdf(files) {
    const fileList = Array.isArray(files) ? files : [files].filter(Boolean);
    if (!fileList.length) return;

    const invalidFile = fileList.find((file) => file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf'));
    if (invalidFile) {
      setError('Only PDF files are supported.');
      return;
    }

    setIsUploading(true);
    setError('');
    try {
      for (const file of fileList) {
        const formData = new FormData();
        formData.append('file', file);
        if (selectedNotebookId) {
          formData.append('notebook_id', selectedNotebookId);
        }

        const uploaded = await authorizedFetch('/api/documents/upload', {
          method: 'POST',
          body: formData,
        });
        setDocuments((current) => [uploaded, ...current.filter((item) => item.id !== uploaded.id)]);
        setSelectedDocumentId(uploaded.id);
        setSelectedDocumentIds((current) => uniqueIds([uploaded.id, ...current]));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function askQuestion(event, suggestedQuestion = '') {
    event?.preventDefault?.();
    const trimmed = (suggestedQuestion || query).trim();
    if (!trimmed || isAsking) return;

    const scopedDocuments = selectedDocuments.filter((document) => document.status === 'processed');
    if (!scopedDocuments.length) {
      setError(userSettings.language === 'vi' ? 'Vui lòng chọn ít nhất 1 PDF đã xử lý trước khi hỏi.' : 'Select at least one processed PDF before asking.');
      return;
    }

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
          document_id: scopedDocuments.length === 1 ? scopedDocuments[0].id : null,
          document_ids: scopedDocuments.map((document) => document.id),
          session_id: activeSessionId || null,
          top_k: 5,
          save_history: true,
        }),
      });

      setLastAnswer(answer);
      if (answer.session_id) {
        setActiveSessionId(answer.session_id);
        loadChatSessions(selectedNotebookId);
      }
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
      language: userSettings.language,
      onLogout: logout,
    },
    notebooks: {
      notebooks,
      selectedNotebookId,
      newNotebookTitle,
      isNotebookLoading,
      language: userSettings.language,
      onReload: loadNotebooks,
      onSelectNotebook: setSelectedNotebookId,
      onNewNotebookTitleChange: setNewNotebookTitle,
      onCreateNotebook: createNotebook,
      onDeleteNotebook: deleteNotebook,
    },
    documents: {
      documents,
      filteredDocuments,
      selectedDocumentId,
      selectedDocumentIds,
      selectedDocuments,
      selectedNotebook,
      search,
      isLoadingDocuments,
      isUploading,
      language: userSettings.language,
      fileInputRef,
      onReload: () => loadDocuments(),
      onUpload: uploadPdf,
      onSearchChange: setSearch,
      onSelectDocument: selectDocument,
      onToggleDocumentScope: toggleDocumentScope,
      onDeleteDocument: deleteDocument,
    },
    chat: {
      selectedDocument,
      selectedDocumentIds,
      selectedDocuments,
      readySelectedDocuments,
      scopeLabel,
      suggestionTitle,
      suggestedQuestions,
      isLoadingSuggestions,
      hasReadyScope,
      language: userSettings.language,
      error,
      messages,
      activeSessionId,
      isAsking,
      query,
      chatEndRef,
      onSubmit: askQuestion,
      onQueryChange: setQuery,
      onSuggestionSelect: submitSuggestedQuestion,
      onSelectSession: loadChatSession,
      onNewChat: startNewChat,
    },
    history: {
      sessions: chatSessions,
      activeSessionId,
      isLoading: isLoadingHistory,
      language: userSettings.language,
      messages,
      onReload: () => loadChatSessions(),
      onSelectSession: loadChatSession,
      onDeleteSession: deleteChatSession,
      onNewChat: startNewChat,
    },
    status: {
      user: effectiveUser,
      selectedNotebook,
      selectedDocument,
      lastAnswer,
    },
    settings: {
      user: effectiveUser,
      values: userSettings,
      message: settingsMessage,
      error,
      isAuthDisabled: AUTH_DISABLED,
      isSaving: isSavingSettings,
      isChangingPassword,
      isDeletingAccount,
      onLogout: logout,
      onUpdate: updateLocalUserSettings,
      onChangePassword: changePassword,
      onDeleteAccount: deleteAccount,
    },
  };
}

function normalizeUserSettings(settings) {
  const rawSettings = settings || {};
  return {
    language: rawSettings.language === 'vi' ? 'vi' : 'en',
    theme: rawSettings.theme === 'dark' ? 'dark' : 'light',
  };
}

function resolveStoredSettings(owner, fallbackSettings = null) {
  const storedSettings = readStoredJson(settingsStorageKey(owner));
  return normalizeUserSettings(storedSettings || fallbackSettings || owner?.settings || defaultUserSettings);
}

function settingsStorageKey(user) {
  return `${SETTINGS_STORAGE_PREFIX}${user?.email || 'guest'}`;
}

function workspaceStorageKey(user) {
  return `${WORKSPACE_STORAGE_PREFIX}${user?.email || 'guest'}`;
}

function readStoredWorkspace(owner) {
  const workspace = readStoredJson(workspaceStorageKey(owner));
  return {
    selectedNotebookId: typeof workspace?.selectedNotebookId === 'string' ? workspace.selectedNotebookId : '',
    selectedDocumentId: typeof workspace?.selectedDocumentId === 'string' ? workspace.selectedDocumentId : '',
    selectedDocumentIds: Array.isArray(workspace?.selectedDocumentIds)
      ? workspace.selectedDocumentIds.map(String).filter(Boolean)
      : [],
    activeSessionId: typeof workspace?.activeSessionId === 'string' ? workspace.activeSessionId : '',
    messages: Array.isArray(workspace?.messages) ? workspace.messages : initialMessages,
  };
}

function normalizeStoredMessages(messages) {
  if (!Array.isArray(messages) || !messages.length) return initialMessages;
  const normalized = messages.filter((message) => (
    message &&
    typeof message.id === 'string' &&
    ['assistant', 'user'].includes(message.role) &&
    typeof message.content === 'string'
  ));
  return normalized.length ? normalized : initialMessages;
}

function uniqueIds(values) {
  return values.reduce((ids, value) => {
    if (!value) return ids;
    const normalized = String(value);
    if (!ids.includes(normalized)) ids.push(normalized);
    return ids;
  }, []);
}

function buildScopeLabel(selectedDocuments) {
  return displayDocumentListTitle(selectedDocuments);
}
