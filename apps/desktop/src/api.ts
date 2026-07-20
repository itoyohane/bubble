import type {
  AgentRun,
  Artifact,
  Bubble,
  BubbleDetail,
  Depth,
  Health,
  RunEvent,
} from "./types";

interface RuntimeConfig {
  apiBase: string;
  token: string;
}

let runtimePromise: Promise<RuntimeConfig> | null = null;

async function runtimeConfig(): Promise<RuntimeConfig> {
  if (!runtimePromise) {
    runtimePromise = (async () => {
      if ("__TAURI_INTERNALS__" in window) {
        const { invoke } = await import("@tauri-apps/api/core");
        return invoke<RuntimeConfig>("runtime_config");
      }
      return {
        apiBase: process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8765",
        token: process.env.NEXT_PUBLIC_API_TOKEN ?? "",
      };
    })();
  }
  return runtimePromise;
}

function headers(token: string, json = false): HeadersInit {
  return {
    ...(json ? { "Content-Type": "application/json" } : {}),
    ...(token ? { "X-Bubble-Token": token } : {}),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const runtime = await runtimeConfig();
  const response = await fetch(`${runtime.apiBase}${path}`, {
    ...init,
    headers: { ...headers(runtime.token, Boolean(init?.body)), ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? `请求失败：${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function requestText(path: string): Promise<string> {
  const runtime = await runtimeConfig();
  const response = await fetch(`${runtime.apiBase}${path}`, {
    headers: headers(runtime.token),
  });
  if (!response.ok) throw new Error(`导出失败：${response.status}`);
  return response.text();
}

export const api = {
  health: () => request<Health>("/health"),
  listBubbles: () => request<Bubble[]>("/api/bubbles"),
  getBubble: (id: string) => request<BubbleDetail>(`/api/bubbles/${id}`),
  createBubble: (payload: { name: string; raw_idea: string; depth: Depth }) =>
    request<Bubble>("/api/bubbles", { method: "POST", body: JSON.stringify(payload) }),
  updateBubble: (id: string, payload: { name?: string; depth?: Depth }) =>
    request<Bubble>(`/api/bubbles/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteBubble: (id: string) => request<void>(`/api/bubbles/${id}`, { method: "DELETE" }),
  startRun: (bubbleId: string, instruction?: string) =>
    request<AgentRun>(`/api/bubbles/${bubbleId}/runs`, {
      method: "POST",
      body: JSON.stringify({ instruction: instruction || null }),
    }),
  getRun: (runId: string) => request<AgentRun>(`/api/runs/${runId}`),
  resumeRun: (runId: string, answers: Record<string, string>) =>
    request<AgentRun>(`/api/runs/${runId}/resume`, {
      method: "POST",
      body: JSON.stringify({ answers, confirm_scope: true }),
    }),
  cancelRun: (runId: string) => request<AgentRun>(`/api/runs/${runId}/cancel`, { method: "POST" }),
  events: (runId: string, afterId = 0) =>
    request<RunEvent[]>(`/api/runs/${runId}/events/history?after_id=${afterId}`),
  artifacts: (bubbleId: string) => request<Artifact[]>(`/api/bubbles/${bubbleId}/artifacts`),
  exportBubble: (bubbleId: string) => requestText(`/api/bubbles/${bubbleId}/export`),
};

const eventNames = [
  "run_started",
  "node_started",
  "node_completed",
  "node_failed",
  "model_retry",
  "human_input_required",
  "run_completed",
  "run_failed",
  "run_cancelled",
];

export async function subscribeToRun(
  runId: string,
  afterId: number,
  onEvent: (event: RunEvent) => void,
  onStatus: (run: AgentRun) => void,
  onError: () => void,
): Promise<() => void> {
  const runtime = await runtimeConfig();
  const tokenQuery = runtime.token ? `&token=${encodeURIComponent(runtime.token)}` : "";
  const source = new EventSource(
    `${runtime.apiBase}/api/runs/${runId}/events?after_id=${afterId}${tokenQuery}`,
  );
  const eventHandler = (raw: Event) => {
    const message = raw as MessageEvent<string>;
    onEvent(JSON.parse(message.data) as RunEvent);
  };
  eventNames.forEach((name) => source.addEventListener(name, eventHandler));
  source.addEventListener("run_status", (raw) => {
    const message = raw as MessageEvent<string>;
    onStatus(JSON.parse(message.data) as AgentRun);
    source.close();
  });
  source.onerror = () => {
    onError();
    source.close();
  };
  return () => source.close();
}
