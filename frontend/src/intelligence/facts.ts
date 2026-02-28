import type { EstimatesJson, FilingsJson, FinancialsJson, NewsJson, PeersJson, PricesJson } from "../lib/types";
import { fetchJson } from "../lib/data";

type AnyRecord = Record<string, unknown>;

export type FactsBundle = {
  ticker: string;
  asOfUtc: string;
  facts: AnyRecord;
  missing: string[];
};

function isoDateUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

function pick(obj: AnyRecord, keys: string[]): AnyRecord {
  const out: AnyRecord = {};
  for (const k of keys) {
    if (k in obj && obj[k] !== null && obj[k] !== undefined) out[k] = obj[k];
  }
  return out;
}

async function fetchOptional<T>(path: string, missing: string[], missingName: string): Promise<T | null> {
  try {
    return await fetchJson<T>(path);
  } catch {
    missing.push(missingName);
    return null;
  }
}

async function fetchOptionalText(path: string): Promise<string | null> {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

export async function loadFactsForTicker(ticker: string): Promise<FactsBundle> {
  const t = ticker.trim().toUpperCase();
  const missing: string[] = [];

  const [financials, prices, news, filings, insider, estimates, peers] = await Promise.all([
    fetchOptional<FinancialsJson>(`/stocks/${t}/financials.json`, missing, "financials.json"),
    fetchOptional<PricesJson>(`/stocks/${t}/prices.json`, missing, "prices.json"),
    fetchOptional<NewsJson>(`/stocks/${t}/news.json`, missing, "news.json"),
    fetchOptional<FilingsJson>(`/stocks/${t}/filings.json`, missing, "filings.json"),
    fetchOptional<FilingsJson>(`/stocks/${t}/insider.json`, missing, "insider.json"),
    fetchOptional<EstimatesJson>(`/stocks/${t}/estimates.json`, missing, "estimates.json"),
    fetchOptional<PeersJson>(`/stocks/${t}/peers.json`, missing, "peers.json"),
  ]);

  const finObj = (financials ?? {}) as AnyRecord;
  const pricesObj = (prices ?? {}) as AnyRecord;
  const newsObj = (news ?? {}) as AnyRecord;
  const filingsObj = (filings ?? {}) as AnyRecord;
  const insiderObj = (insider ?? {}) as AnyRecord;
  const estimatesObj = (estimates ?? {}) as AnyRecord;
  const peersObj = (peers ?? {}) as AnyRecord;

  const facts: AnyRecord = {
    ticker: t,
    company: pick(finObj, ["name", "sector", "industry", "currency"]),
    financials: pick(finObj, [
      "marketCap",
      "enterpriseValue",
      "trailingPE",
      "forwardPE",
      "pegRatio",
      "priceToBook",
      "priceToSales",
      "revenue",
      "revenueGrowth",
      "grossMargins",
      "operatingMargins",
      "profitMargins",
      "operatingCashFlow",
      "freeCashFlow",
      "totalDebt",
      "totalCash",
      "debtToEquity",
      "currentRatio",
      "quickRatio",
      "roe",
      "roa",
      "earningsGrowth",
      "dividendYield",
      "beta",
      "52WeekHigh",
      "52WeekLow",
    ]),
    prices: (pricesObj["summary"] && typeof pricesObj["summary"] === "object" ? (pricesObj["summary"] as AnyRecord) : {}),
    news: Array.isArray(newsObj["items"]) ? (newsObj["items"] as unknown[]).slice(0, 8) : [],
    filings: Array.isArray(filingsObj["filings"]) ? (filingsObj["filings"] as unknown[]).slice(0, 10) : [],
    insider: Array.isArray(insiderObj["filings"]) ? (insiderObj["filings"] as unknown[]).slice(0, 10) : [],
    estimates:
      estimatesObj && typeof estimatesObj === "object"
        ? pick(estimatesObj, [
            "targetMeanPrice",
            "targetHighPrice",
            "targetLowPrice",
            "recommendationKey",
            "recommendationMean",
            "numberOfAnalystOpinions",
            "nextEarningsDate",
          ])
        : {},
    peers: Array.isArray(peersObj["peers"]) ? peersObj["peers"] : [],
  };

  // Optional filing cache: meta + text (text can be large; prompt builder will excerpt it).
  const [filingMeta, filingText] = await Promise.all([
    fetchOptional<AnyRecord>(`/stocks/${t}/filing_latest.meta.json`, missing, "filing_latest.meta.json"),
    fetchOptionalText(`/stocks/${t}/filing_latest.txt`),
  ]);
  if (filingMeta || (filingText && filingText.trim())) {
    facts["latest_filing"] = {
      meta: filingMeta ?? {},
      has_text: Boolean(filingText && filingText.trim()),
      ...(filingText && filingText.trim() ? { text: filingText } : {}),
    };
  }

  return { ticker: t, asOfUtc: isoDateUtc(), facts, missing };
}

export async function loadThesisText(): Promise<string> {
  const res = await fetch("/thesis.md", { cache: "no-store" });
  if (!res.ok) throw new Error(`Missing thesis.md (HTTP ${res.status})`);
  return await res.text();
}

