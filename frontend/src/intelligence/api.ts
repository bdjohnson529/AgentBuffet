export type ProviderName = "either" | "openai" | "anthropic";

export type LLMSettings = {
  provider: ProviderName;
  model?: string;
  temperature?: number;
  maxOutputTokens?: number;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
  return (text ? (JSON.parse(text) as T) : ({} as T));
}

export async function completeReportText(req: {
  settings: LLMSettings;
  prompt: string;
}): Promise<{ text: string; providerUsed: string; modelUsed: string }> {
  return postJson("/api/intelligence/complete-report", req);
}

export async function chatComplete(req: {
  settings: LLMSettings;
  system: string;
  messages: ChatMessage[];
}): Promise<{ text: string; providerUsed: string; modelUsed: string }> {
  return postJson("/api/intelligence/chat", req);
}

export async function writeReportFiles(req: {
  ticker: string;
  reportJson: unknown;
  reportMarkdown: string;
}): Promise<{ ok: true }> {
  return postJson("/api/intelligence/write-report", req);
}

