// Central HTTP layer: JWT in memory, one-shot refresh on 401, typed helpers,
// and an SSE reader for the chat stream. Components never call fetch directly.

const BASE = import.meta.env.VITE_API_URL || "";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let onAuthLost: (() => void) | null = null;

export function setTokens(access: string | null, refresh: string | null) {
  accessToken = access;
  refreshToken = refresh;
  if (refresh) localStorage.setItem("ashashala_refresh", refresh);
  else localStorage.removeItem("ashashala_refresh");
}

export function getAccessToken() {
  return accessToken;
}

export function loadStoredRefresh(): string | null {
  refreshToken = localStorage.getItem("ashashala_refresh");
  return refreshToken;
}

export function setOnAuthLost(cb: () => void) {
  onAuthLost = cb;
}

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function rawFetch(path: string, init: RequestInit): Promise<Response> {
  return fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init.headers || {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
  });
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data = (await res.json()) as { access_token: string; refresh_token: string };
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let code = "ERROR";
  let message = res.statusText;
  try {
    const body = await res.json();
    code = body.error_code || code;
    message = body.message || message;
  } catch {
    /* non-JSON error */
  }
  return new ApiError(res.status, code, message);
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = init.body && !(init.body instanceof FormData)
    ? { "Content-Type": "application/json", ...(init.headers || {}) }
    : init.headers || {};

  let res = await rawFetch(path, { ...init, headers });

  if (res.status === 401 && retry && (await tryRefresh())) {
    res = await rawFetch(path, { ...init, headers });
  }
  if (res.status === 401) {
    onAuthLost?.();
    throw new ApiError(401, "UNAUTHORIZED", "Session expired");
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "DELETE", body: body ? JSON.stringify(body) : undefined }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
};

// --- SSE: POST /student/chat streams tokens then a final `event: citations`. ---
export interface ChatStreamHandlers {
  onToken: (text: string) => void;
  onCitations: (citations: unknown[]) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

export async function streamChat(
  body: { question: string; class_id: string; subject_id?: string | null },
  handlers: ChatStreamHandlers,
): Promise<void> {
  const res = await rawFetch("/api/v1/student/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    handlers.onError(`Chat failed (${res.status})`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const handleEvent = (chunk: string) => {
    const lines = chunk.split("\n");
    let eventName = "message";
    const dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    const data = dataLines.join("\n");
    if (!data) return;
    try {
      if (eventName === "citations") {
        handlers.onCitations(JSON.parse(data));
      } else {
        const parsed = JSON.parse(data);
        if (parsed.type === "token") handlers.onToken(parsed.content);
        else if (parsed.type === "error") handlers.onError(parsed.message);
      }
    } catch {
      /* ignore malformed frame */
    }
  };

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      handleEvent(frame);
    }
  }
  handlers.onDone();
}
