import { useEffect, useMemo, useState } from "react";
import type { FactsBundle } from "../intelligence/facts";
import { loadFactsForTicker, loadThesisText } from "../intelligence/facts";
import { buildChatSystemPrompt, buildReportPrompt } from "../intelligence/prompts";
import { completeReportText, type ChatMessage, chatComplete, type LLMSettings, writeReportFiles } from "../intelligence/api";
import { renderReportMarkdown } from "../intelligence/render";
import { ReportSchema, type ReportFields, type ReportFile } from "../intelligence/schema";
import { Markdown } from "./Markdown";

type Props = {
  ticker: string;
  existingReport: ReportFile | null;
  onReportUpdated: (r: ReportFile) => void;
};

type Status = { kind: "idle" } | { kind: "working"; label: string } | { kind: "error"; message: string };

function extractLikelyJson(text: string): string {
  const t = (text || "").trim();
  if (!t) return "";
  const a = t.indexOf("{");
  const b = t.lastIndexOf("}");
  if (a !== -1 && b !== -1 && b > a) return t.slice(a, b + 1);
  return t;
}

function loadSettings(): LLMSettings {
  try {
    const raw = localStorage.getItem("ab_intelligence_settings");
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

function saveSettings(s: LLMSettings) {
  try {
    localStorage.setItem("ab_intelligence_settings", JSON.stringify(s));
  } catch {
    // ignore
  }
}

export function AnalysisPanel({ ticker, existingReport, onReportUpdated }: Props) {
  const [settings, setSettings] = useState<LLMSettings>(() => loadSettings());
  const [facts, setFacts] = useState<FactsBundle | null>(null);
  const [thesisText, setThesisText] = useState<string | null>(null);

  const openaiModelOptions = useMemo(
    () => ["gpt-4.1-mini", "gpt-4.1", "gpt-4.1-nano", "gpt-4o-mini", "gpt-4o"],
    [],
  );
  const anthropicModelOptions = useMemo(
    () => ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
    [],
  );

  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [reportFields, setReportFields] = useState<ReportFields | null>(existingReport?.report ?? null);
  const [reportMd, setReportMd] = useState<string | null>(null);
  const [showRawMarkdown, setShowRawMarkdown] = useState(false);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "Ask me about valuation, risks, or the final decision — I’ll answer using the thesis + facts for this ticker." },
  ]);
  const [chatInput, setChatInput] = useState("");

  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  useEffect(() => {
    setReportFields(existingReport?.report ?? null);
  }, [existingReport]);

  const systemPrompt = useMemo(() => {
    if (!facts || !thesisText) return null;
    return buildChatSystemPrompt({
      ticker,
      thesisText,
      factsBundle: facts.facts,
      reportFile: existingReport ?? (reportFields ? { ticker, asOfUtc: facts.asOfUtc, report: reportFields } : null),
    });
  }, [existingReport, facts, reportFields, thesisText, ticker]);

  async function ensureContextLoaded() {
    if (!facts) setFacts(await loadFactsForTicker(ticker));
    if (!thesisText) setThesisText(await loadThesisText());
  }

  async function generateReport() {
    try {
      setStatus({ kind: "working", label: "Loading facts + thesis…" });
      await ensureContextLoaded();
      const fb = facts ?? (await loadFactsForTicker(ticker));
      const tt = thesisText ?? (await loadThesisText());

      const prompt = buildReportPrompt({ thesisText: tt, factsBundle: fb.facts });

      setStatus({ kind: "working", label: "Calling model…" });
      const { text, providerUsed, modelUsed } = await completeReportText({ settings, prompt });

      const jsonText = extractLikelyJson(text);
      let obj: unknown;
      try {
        obj = JSON.parse(jsonText);
      } catch (e) {
        throw new Error(`Model did not return valid JSON. Raw: ${text.slice(0, 240)}…`);
      }

      const parsed = ReportSchema.safeParse(obj);
      if (!parsed.success) {
        throw new Error(`Model JSON failed validation: ${parsed.error.message}`);
      }

      const report: ReportFields = parsed.data;
      setReportFields(report);

      const asOfUtc = fb.asOfUtc;
      const reportFile: ReportFile = {
        ticker,
        asOfUtc,
        provider: providerUsed,
        model: modelUsed,
        inputsMissing: fb.missing,
        filingFetchStatus: fb.facts["latest_filing"] ? "present" : "missing",
        latestFilingMeta:
          fb.facts["latest_filing"] && typeof fb.facts["latest_filing"] === "object" ? (fb.facts["latest_filing"] as any).meta ?? null : null,
        report,
      };

      const md = renderReportMarkdown(ticker, report, asOfUtc);
      setReportMd(md);
      onReportUpdated(reportFile);
      setStatus({ kind: "idle" });
    } catch (e) {
      setStatus({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  }

  async function saveReport() {
    try {
      if (!reportFields) throw new Error("No report generated yet.");
      setStatus({ kind: "working", label: "Saving report.json + report.md…" });
      await ensureContextLoaded();
      const fb = facts ?? (await loadFactsForTicker(ticker));

      const asOfUtc = fb.asOfUtc;
      const reportFile: ReportFile = {
        ticker,
        asOfUtc,
        provider: existingReport?.provider ?? settings.provider,
        model: existingReport?.model ?? settings.model ?? null,
        inputsMissing: fb.missing,
        filingFetchStatus: fb.facts["latest_filing"] ? "present" : "missing",
        latestFilingMeta:
          fb.facts["latest_filing"] && typeof fb.facts["latest_filing"] === "object" ? (fb.facts["latest_filing"] as any).meta ?? null : null,
        report: reportFields,
      };

      const md = reportMd ?? renderReportMarkdown(ticker, reportFields, asOfUtc);
      await writeReportFiles({ ticker, reportJson: reportFile, reportMarkdown: md });
      onReportUpdated(reportFile);
      setReportMd(md);
      setStatus({ kind: "idle" });
    } catch (e) {
      setStatus({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  }

  async function sendChat() {
    try {
      const q = chatInput.trim();
      if (!q) return;
      setChatInput("");

      setStatus({ kind: "working", label: "Thinking…" });
      await ensureContextLoaded();
      const sys = systemPrompt ?? buildChatSystemPrompt({ ticker, thesisText: thesisText ?? "", factsBundle: facts?.facts ?? {} });

      const nextMessages: ChatMessage[] = [...chatMessages, { role: "user", content: q }];
      setChatMessages(nextMessages);

      const firstUserIdx = nextMessages.findIndex((m) => m.role === "user");
      const convo = firstUserIdx === -1 ? nextMessages : nextMessages.slice(firstUserIdx);
      const { text, providerUsed, modelUsed } = await chatComplete({ settings, system: sys, messages: convo });
      setChatMessages([...nextMessages, { role: "assistant", content: text }]);
      setStatus({ kind: "idle" });

      setSettings((s) => ({ ...s, provider: (providerUsed as any) ?? s.provider, model: modelUsed ?? s.model }));
    } catch (e) {
      setStatus({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  }

  const headline = existingReport?.report?.action ? `${existingReport.report.action}` : reportFields?.action ? reportFields.action : "—";

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
    <div className="row" style={{ gridColumn: "span 12" }}>
      <div className="card" style={{ gridColumn: "span 12" }}>
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

      <div className="card" style={{ gridColumn: "span 12" }}>
        <div className="cardTitle">Report generation</div>
        <div className="small muted" style={{ marginTop: 6 }}>
          Current action: <span style={{ fontFamily: "var(--mono)" }}>{headline}</span>
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
          <button className="btn" type="button" onClick={generateReport} disabled={status.kind === "working"}>
            Generate / refresh report
          </button>
          <button className="btnSecondary" type="button" onClick={saveReport} disabled={status.kind === "working" || !reportFields}>
            Save to stocks/{ticker}/report.* (writes files)
          </button>
          {status.kind === "working" ? <div className="pill">{status.label}</div> : null}
          {status.kind === "error" ? <div className="pill" style={{ color: "var(--bad)" }}>{status.message}</div> : null}
        </div>

        {reportFields ? (
          <div className="row" style={{ marginTop: 12 }}>
            <div className="card" style={{ gridColumn: "span 4" }}>
              <div className="cardTitle">Thesis alignment</div>
              <div className="small" style={{ marginTop: 8 }}>
                <div>Moat: <b>{reportFields.moat}</b></div>
                <div>Financial Health: <b>{reportFields.financial_health}</b></div>
                <div>Valuation: <b>{reportFields.valuation}</b></div>
              </div>
            </div>
            <div className="card" style={{ gridColumn: "span 8" }}>
              <div className="cardTitle">Decision</div>
              <div className="cardValue" style={{ fontSize: 18 }}>{reportFields.action}</div>
              <div className="small muted" style={{ marginTop: 8 }}>{reportFields.reasoning}</div>
            </div>

            <div className="card" style={{ gridColumn: "span 12" }}>
              <div className="cardTitle">Markdown preview</div>
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6, flexWrap: "wrap" }}>
                <label className="small" style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={showRawMarkdown}
                    onChange={(e) => setShowRawMarkdown(e.target.checked)}
                  />
                  Show raw markdown
                </label>
              </div>
              {(() => {
                const md = reportMd ?? renderReportMarkdown(ticker, reportFields, facts?.asOfUtc ?? null);
                return showRawMarkdown ? <pre className="pre">{md}</pre> : <Markdown markdown={md} />;
              })()}
            </div>
          </div>
        ) : (
          <div className="muted" style={{ marginTop: 12 }}>
            No report yet for {ticker}. Generate one to create <span style={{ fontFamily: "var(--mono)" }}>report.json</span> and{" "}
            <span style={{ fontFamily: "var(--mono)" }}>report.md</span>.
          </div>
        )}
      </div>

      <div className="card" style={{ gridColumn: "span 12" }}>
        <div className="cardTitle">Chat</div>
        <div className="chat">
          <div className="chatLog">
            {chatMessages.map((m, i) => (
              <div key={i} className={`chatMsg ${m.role === "user" ? "chatMsgUser" : "chatMsgAssistant"}`}>
                <div className="chatRole">{m.role}</div>
                <div className="chatContent">{m.content}</div>
              </div>
            ))}
          </div>
          <div className="chatComposer">
            <input
              className="input"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder={`Ask about ${ticker}…`}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) sendChat();
              }}
            />
            <button className="btn" type="button" onClick={sendChat} disabled={status.kind === "working"}>
              Send
            </button>
            <button
              className="btnSecondary"
              type="button"
              onClick={() => setChatMessages([{ role: "assistant", content: "Ask me about valuation, risks, or the final decision — I’ll answer using the thesis + facts for this ticker." }])}
              disabled={status.kind === "working"}
            >
              Reset
            </button>
          </div>
          {systemPrompt ? (
            <details style={{ marginTop: 10 }}>
              <summary className="small muted">Context sent to model (thesis + facts)</summary>
              <pre className="pre">{systemPrompt}</pre>
            </details>
          ) : null}
        </div>
      </div>
    </div>
  );
}

