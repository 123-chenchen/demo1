const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
const rawAuthDisabled = import.meta.env.VITE_AUTH_DISABLED || 'false';

export const API_BASE_URL = rawApiBaseUrl.replace(/\/+$/, '');
export const API_ENDPOINT_LABEL = API_BASE_URL ? API_BASE_URL.replace(/^https?:\/\//, '') : 'same-origin /api';
export const AUTH_DISABLED = rawAuthDisabled.toLowerCase() === 'true';
export const ACCESS_TOKEN_KEY = 'pdf-chatbot-access-token';
export const USER_KEY = 'pdf-chatbot-user';

export const initialMessages = [
  {
    id: 'welcome',
    role: 'assistant',
    content: 'Upload a processed PDF, select a document, then ask questions about its content.',
    sources: [],
  },
];

export function readStoredJson(key) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

export function persistStoredSession(token, user) {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function parseResponse(response) {
  const text = await response.text();
  let data = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    throw new Error(data?.detail || `Request failed with status ${response.status}`);
  }

  return data;
}

export function apiFetch(path, options = {}, accessToken = '') {
  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(options.headers || {}),
    },
  })
    .catch((error) => {
      if (error instanceof TypeError) {
        const target = API_BASE_URL || globalThis.location?.origin || '/api';
        throw new Error(`Cannot reach backend at ${target}. Check that the backend or API proxy is running.`);
      }
      throw error;
    })
    .then(parseResponse);
}
