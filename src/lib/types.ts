export type NewsItem = {
  title: string;
  link: string;
  published?: string;
  summary?: string;
};

export type NewsJson = {
  ticker: string;
  count: number;
  items: NewsItem[];
};

export type PricesPoint = {
  date: string;
  open?: number;
  high?: number;
  low?: number;
  close: number;
  volume?: number;
};

export type PricesJson = {
  ticker: string;
  summary?: {
    periodDays?: number;
    firstDate?: string;
    lastDate?: string;
    firstClose?: number;
    lastClose?: number;
    totalReturnPct?: number;
    dailyVolatility?: number;
    numPoints?: number;
  };
  series: PricesPoint[];
};

export type FilingsJson = {
  ticker: string;
  cik?: string;
  name?: string;
  count: number;
  filings: Array<{
    form: string;
    filingDate: string;
    accessionNumber?: string;
    primaryDocument?: string;
    documentUrl: string;
    description?: string;
  }>;
};

export type EstimatesJson = {
  ticker: string;
  name?: string;
  nextEarningsDate?: string | null;
  targetMeanPrice?: number | null;
  targetHighPrice?: number | null;
  targetLowPrice?: number | null;
  recommendationKey?: string | null;
  numberOfAnalystOpinions?: number | null;
  earningsGrowth?: number | null;
  revenueGrowth?: number | null;
};

export type FinancialsJson = Record<string, unknown> & {
  ticker: string;
  name?: string;
  sector?: string;
  industry?: string;
  currency?: string;
  marketCap?: number;
  enterpriseValue?: number;
  trailingPE?: number;
  forwardPE?: number;
  pegRatio?: number;
  priceToBook?: number;
  priceToSales?: number;
  revenue?: number;
  revenueGrowth?: number;
  grossMargins?: number;
  operatingMargins?: number;
  profitMargins?: number;
  operatingCashFlow?: number;
  freeCashFlow?: number;
  totalDebt?: number;
  totalCash?: number;
  debtToEquity?: number;
  currentRatio?: number;
  quickRatio?: number;
  roe?: number;
  roa?: number;
  earningsGrowth?: number;
  dividendYield?: number;
  beta?: number;
  "52WeekHigh"?: number;
  "52WeekLow"?: number;

  income_stmt_columns?: string[];
  balance_sheet_columns?: string[];
  cashflow_columns?: string[];
  income_stmt?: Record<string, Record<string, unknown>>;
  balance_sheet?: Record<string, Record<string, unknown>>;
  cashflow?: Record<string, Record<string, unknown>>;
};

export type PeersJson = {
  ticker: string;
  name?: string;
  sector?: string;
  industry?: string;
  count: number;
  peers: string[];
};

