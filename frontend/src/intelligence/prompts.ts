type AnyRecord = Record<string, unknown>;

export function buildReportPrompt(opts: {
  thesisText: string;
  factsBundle: AnyRecord;
  maxFilingChars?: number;
}): string {
  const maxFilingChars = opts.maxFilingChars ?? 18000;
  const facts: AnyRecord = { ...opts.factsBundle };

  const latest = facts["latest_filing"];
  if (latest && typeof latest === "object" && !Array.isArray(latest)) {
    const latestCopy: AnyRecord = { ...(latest as AnyRecord) };
    const fullText = latestCopy["text"];
    if (typeof fullText === "string" && fullText.trim()) {
      delete latestCopy["text"];
      latestCopy["text_excerpt"] = fullText.trim().slice(0, maxFilingChars);
    }
    facts["latest_filing"] = latestCopy;
  }

  const factsJson = JSON.stringify(facts, null, 2);

  return (
    "You are a senior equity analyst.\n" +
    "Your job: generate a report decision using ONLY the facts provided.\n\n" +
    "STRICT RULES:\n" +
    "- Do not invent numbers, dates, guidance, customers, or products.\n" +
    "- If data is missing, use 'unknown' and say so.\n" +
    "- Output MUST be valid JSON and MUST match the required fields.\n" +
    "- 'reasoning' must be 2-3 sentences maximum.\n\n" +
    "THESIS (authoritative):\n" +
    `${opts.thesisText.trim()}\n\n` +
    "FACTS (authoritative JSON):\n" +
    `${factsJson}\n\n` +
    "OUTPUT JSON SCHEMA (keys required):\n" +
    "{\n" +
    '  "moat": "High|Medium|Low|unknown",\n' +
    '  "financial_health": "Pass|Fail|unknown",\n' +
    '  "valuation": "Over-valued|Under-valued|unknown",\n' +
    '  "base_case": "string",\n' +
    '  "upside_case": "string",\n' +
    '  "downside_case": "string",\n' +
    '  "action": "BUY|HOLD|SELL|AVOID",\n' +
    '  "reasoning": "string",\n' +
    '  "evidence": [{"claim": "string", "source": "string"}]\n' +
    "}\n\n" +
    "Now output JSON only. No markdown, no commentary.\n"
  );
}

export function buildChatSystemPrompt(opts: {
  ticker: string;
  thesisText: string;
  factsBundle: AnyRecord;
  reportFile?: unknown;
}): string {
  const factsJson = JSON.stringify(opts.factsBundle, null, 2);
  const reportJson = opts.reportFile ? JSON.stringify(opts.reportFile, null, 2) : "";

  return (
    "You are a senior equity analyst.\n" +
    "Answer questions about the stock using ONLY the thesis + facts provided.\n" +
    "If the user asks for a number that is not present in the facts, say it is unknown.\n" +
    "Prefer concise answers with bullet points when useful.\n" +
    "When making a recommendation, use one of: BUY, HOLD, SELL, AVOID.\n\n" +
    `TICKER: ${opts.ticker}\n\n` +
    "THESIS (authoritative):\n" +
    `${opts.thesisText.trim()}\n\n` +
    "FACTS (authoritative JSON):\n" +
    `${factsJson}\n\n` +
    (reportJson
      ? "LATEST GENERATED REPORT (optional, not authoritative vs thesis/facts):\n" + `${reportJson}\n\n`
      : "")
  );
}

