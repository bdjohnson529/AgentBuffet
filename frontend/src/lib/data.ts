import type {
  EstimatesJson,
  FilingsJson,
  FinancialsJson,
  NewsJson,
  PeersJson,
  PricesJson,
} from "./types";

export type DatasetName =
  | "news"
  | "financials"
  | "prices"
  | "estimates"
  | "filings"
  | "insider"
  | "peers";

export async function loadTickers(): Promise<string[]> {
  const res = await fetch("/stocks.txt", { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load stocks.txt (${res.status})`);
  const text = await res.text();
  const out: string[] = [];
  for (const line of text.split(/\r?\n/)) {
    const sym = line.trim().replace(/^\$/, "").trim().toUpperCase();
    if (!sym) continue;
    if (!/^[A-Z]+$/.test(sym)) continue;
    out.push(sym);
  }
  return Array.from(new Set(out)).sort();
}

export async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return (await res.json()) as T;
}

export function datasetPath(ticker: string, dataset: DatasetName): string {
  return `/stocks/${ticker}/${dataset}.json`;
}

export async function fetchNews(ticker: string): Promise<NewsJson> {
  return fetchJson(datasetPath(ticker, "news"));
}

export async function fetchPrices(ticker: string): Promise<PricesJson> {
  return fetchJson(datasetPath(ticker, "prices"));
}

export async function fetchFinancials(ticker: string): Promise<FinancialsJson> {
  return fetchJson(datasetPath(ticker, "financials"));
}

export async function fetchEstimates(ticker: string): Promise<EstimatesJson> {
  return fetchJson(datasetPath(ticker, "estimates"));
}

export async function fetchFilings(ticker: string): Promise<FilingsJson> {
  return fetchJson(datasetPath(ticker, "filings"));
}

export async function fetchInsider(ticker: string): Promise<FilingsJson> {
  // insider.json matches filings-like schema (form 4 list)
  return fetchJson(datasetPath(ticker, "insider"));
}

export async function fetchPeers(ticker: string): Promise<PeersJson> {
  return fetchJson(datasetPath(ticker, "peers"));
}

