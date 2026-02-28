import type { LLMSettings } from "./api";

const STORAGE_KEY = "ab_intelligence_settings";

export function loadLLMSettings(): LLMSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { provider: "either", temperature: 0.2, maxOutputTokens: 900 };
    const obj = JSON.parse(raw) as Partial<LLMSettings>;
    return {
      provider: obj.provider ?? "either",
      model: obj.model,
      temperature: typeof obj.temperature === "number" ? obj.temperature : 0.2,
      maxOutputTokens: typeof obj.maxOutputTokens === "number" ? obj.maxOutputTokens : 900,
    };
  } catch {
    return { provider: "either", temperature: 0.2, maxOutputTokens: 900 };
  }
}

export function saveLLMSettings(s: LLMSettings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    // ignore
  }
}

