import { useMemo } from "react";
import type { LLMSettings } from "../intelligence/api";

type Props = {
  settings: LLMSettings;
  setSettings: React.Dispatch<React.SetStateAction<LLMSettings>>;
};

export function LLMSettingsDropdown({ settings, setSettings }: Props) {
  const openaiModelOptions = useMemo(
    () => ["gpt-4.1-mini", "gpt-4.1", "gpt-4.1-nano", "gpt-4o-mini", "gpt-4o"],
    [],
  );
  const anthropicModelOptions = useMemo(
    () => ["claude-opus-4-6", "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
    [],
  );

  const allKnownModels = useMemo(() => {
    const set = new Set<string>();
    for (const m of openaiModelOptions) set.add(m);
    for (const m of anthropicModelOptions) set.add(m);
    return Array.from(set);
  }, [anthropicModelOptions, openaiModelOptions]);

  const selectedModelValue = settings.model ?? "";
  const modelSelectValue =
    !selectedModelValue ? "" : allKnownModels.includes(selectedModelValue) ? selectedModelValue : "__custom__";

  return (
    <details className="settingsDetails">
      <summary className="pill settingsSummary">Settings</summary>
      <div className="card settingsMenu" role="dialog" aria-label="LLM settings">
        <div className="cardTitle">LLM settings</div>
        <div className="row" style={{ marginTop: 10 }}>
          <div className="card" style={{ gridColumn: "span 3" }}>
            <div className="cardTitle">Provider</div>
            <select
              className="input"
              value={settings.provider}
              onChange={(e) => setSettings((s) => ({ ...s, provider: e.target.value as any }))}
            >
              <option value="either">either (auto)</option>
              <option value="openai">openai</option>
              <option value="anthropic">anthropic</option>
            </select>
            <div className="small muted" style={{ marginTop: 6 }}>
              Keys are read from repo-root <span style={{ fontFamily: "var(--mono)" }}>.env</span>.
            </div>
          </div>

          <div className="card" style={{ gridColumn: "span 5" }}>
            <div className="cardTitle">Model (optional override)</div>
            <select
              className="input"
              value={modelSelectValue}
              onChange={(e) => {
                const v = e.target.value;
                if (!v) {
                  setSettings((s) => ({ ...s, model: undefined }));
                  return;
                }
                if (v === "__custom__") {
                  if (!selectedModelValue) setSettings((s) => ({ ...s, model: "" }));
                  return;
                }
                setSettings((s) => ({ ...s, model: v }));
              }}
            >
              <option value="">(use env default)</option>
              <optgroup label="OpenAI">
                {openaiModelOptions.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </optgroup>
              <optgroup label="Anthropic">
                {anthropicModelOptions.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </optgroup>
              <option value="__custom__">Custom…</option>
            </select>
            {modelSelectValue === "__custom__" ? (
              <input
                className="input"
                style={{ marginTop: 8 }}
                value={selectedModelValue}
                onChange={(e) => setSettings((s) => ({ ...s, model: e.target.value || undefined }))}
                placeholder="Type a model name…"
              />
            ) : null}
            <div className="small muted" style={{ marginTop: 6 }}>
              Leave blank to use <span style={{ fontFamily: "var(--mono)" }}>OPENAI_MODEL</span> /{" "}
              <span style={{ fontFamily: "var(--mono)" }}>ANTHROPIC_MODEL</span>.
            </div>
          </div>

          <div className="card" style={{ gridColumn: "span 2" }}>
            <div className="cardTitle">Temp</div>
            <input
              className="input"
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={settings.temperature ?? 0.2}
              onChange={(e) => setSettings((s) => ({ ...s, temperature: Number(e.target.value) }))}
            />
          </div>

          <div className="card" style={{ gridColumn: "span 2" }}>
            <div className="cardTitle">Max tokens</div>
            <input
              className="input"
              type="number"
              min={64}
              max={4000}
              step={64}
              value={settings.maxOutputTokens ?? 900}
              onChange={(e) => setSettings((s) => ({ ...s, maxOutputTokens: Number(e.target.value) }))}
            />
          </div>
        </div>
      </div>
    </details>
  );
}

