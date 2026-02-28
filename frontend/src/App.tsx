import { useEffect, useMemo, useState } from "react";
import { loadTickers } from "./lib/data";
import type { DatasetName } from "./lib/data";
import type { EstimatesJson, FilingsJson, FinancialsJson, NewsJson, PricesJson } from "./lib/types";
import { Tabs } from "./components/Tabs";
import { NewsList } from "./components/NewsList";
import { FilingsTable } from "./components/FilingsTable";
import { PriceChart } from "./components/PriceChart";
import { FinancialsPanel } from "./components/FinancialsPanel";
import { AnalysisPanel } from "./components/AnalysisPanel";
import { LLMSettingsDropdown } from "./components/LLMSettingsDropdown";
import { formatNumberCompact } from "./lib/format";
import { ReportFileSchema, type ReportFile } from "./intelligence/schema";
import type { LLMSettings } from "./intelligence/api";
import { loadLLMSettings, saveLLMSettings } from "./intelligence/settings";

type Tab = "analysis" | "news" | "prices" | "financials" | "filings" | "insider";

function getQueryParam(name: string): string | null {
  const url = new URL(window.location.href);
  return url.searchParams.get(name);
}

function setQueryParam(name: string, value: string) {
  const url = new URL(window.location.href);
  url.searchParams.set(name, value);
  window.history.pushState({}, "", url.toString());
}

async function fetchDataset<T>(ticker: string, dataset: DatasetName): Promise<T> {
  const res = await fetch(`/stocks/${ticker}/${dataset}.json`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Missing /stocks/${ticker}/${dataset}.json (HTTP ${res.status})`);
  return (await res.json()) as T;
}

async function fetchReportFile(ticker: string): Promise<ReportFile | null> {
  try {
    const res = await fetch(`/stocks/${ticker}/report.json`, { cache: "no-store" });
    if (!res.ok) return null;
    const obj = (await res.json()) as unknown;
    const parsed = ReportFileSchema.safeParse(obj);
    if (!parsed.success) return null;
    return parsed.data;
  } catch {
    return null;
  }
}

export function App() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [loadingTickers, setLoadingTickers] = useState(true);
  const [tickerError, setTickerError] = useState<string | null>(null);

  const [llmSettings, setLlmSettings] = useState<LLMSettings>(() => loadLLMSettings());
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string>(() => getQueryParam("t")?.toUpperCase() ?? "");
  const [tab, setTab] = useState<Tab>("analysis");

  const [news, setNews] = useState<NewsJson | null>(null);
  const [prices, setPrices] = useState<PricesJson | null>(null);
  const [financials, setFinancials] = useState<FinancialsJson | null>(null);
  const [estimates, setEstimates] = useState<EstimatesJson | null>(null);
  const [filings, setFilings] = useState<FilingsJson | null>(null);
  const [insider, setInsider] = useState<FilingsJson | null>(null);
  const [report, setReport] = useState<ReportFile | null>(null);

  const [dataError, setDataError] = useState<string | null>(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [tickerActions, setTickerActions] = useState<Record<string, "BUY" | "HOLD" | "SELL" | "AVOID" | null>>({});

  useEffect(() => {
    saveLLMSettings(llmSettings);
  }, [llmSettings]);

  useEffect(() => {
    (async () => {
      try {
        setLoadingTickers(true);
        setTickerError(null);
        const syms = await loadTickers();
        setTickers(syms);
        if (!selected && syms.length) {
          setSelected(syms[0]);
          setQueryParam("t", syms[0]);
        }
      } catch (e) {
        setTickerError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoadingTickers(false);
      }
    })();
    const onPop = () => {
      const t = getQueryParam("t")?.toUpperCase() ?? "";
      if (t) setSelected(t);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase();
    if (!q) return tickers;
    return tickers.filter((t) => t.includes(q));
  }, [tickers, search]);

  // Load report actions for sidebar labels (BUY / SELL)
  useEffect(() => {
    if (!filtered.length) return;
    let cancelled = false;
    (async () => {
      const results = await Promise.allSettled(
        filtered.map(async (t) => {
          const r = await fetchReportFile(t);
          return { ticker: t, action: r?.report?.action ?? null } as const;
        })
      );
      if (cancelled) return;
      const next: Record<string, "BUY" | "HOLD" | "SELL" | "AVOID" | null> = {};
      for (const res of results) {
        if (res.status === "fulfilled" && res.value) {
          next[res.value.ticker] = res.value.action;
        }
      }
      setTickerActions((prev) => ({ ...prev, ...next }));
    })();
    return () => {
      cancelled = true;
    };
  }, [filtered.join(",")]);

  useEffect(() => {
    if (!selected) return;
    setDataError(null);
    setDataLoading(true);
    setNews(null);
    setPrices(null);
    setFinancials(null);
    setEstimates(null);
    setFilings(null);
    setInsider(null);
    setReport(null);

    (async () => {
      try {
        const [n, p, f, e, fi, ins, rep] = await Promise.all([
          fetchDataset<NewsJson>(selected, "news").catch(() => null),
          fetchDataset<PricesJson>(selected, "prices").catch(() => null),
          fetchDataset<FinancialsJson>(selected, "financials").catch(() => null),
          fetchDataset<EstimatesJson>(selected, "estimates").catch(() => null),
          fetchDataset<FilingsJson>(selected, "filings").catch(() => null),
          fetchDataset<FilingsJson>(selected, "insider").catch(() => null),
          fetchReportFile(selected).catch(() => null),
        ]);
        setNews(n);
        setPrices(p);
        setFinancials(f);
        setEstimates(e);
        setFilings(fi);
        setInsider(ins);
        setReport(rep);
      } catch (e) {
        setDataError(e instanceof Error ? e.message : String(e));
      } finally {
        setDataLoading(false);
      }
    })();
  }, [selected]);

  const headerPill = useMemo(() => {
    if (!financials) return "stocks/";
    const cap = typeof financials.marketCap === "number" ? formatNumberCompact(financials.marketCap) : "—";
    const name = financials.name ?? selected;
    return `${selected} • ${name} • mktcap ${cap}`;
  }, [financials, selected]);

  const tabs = useMemo(
    () => [
      { id: "analysis" as const, label: "Analysis" },
      { id: "news" as const, label: "News" },
      { id: "prices" as const, label: "Prices" },
      { id: "financials" as const, label: "Financials" },
      { id: "filings" as const, label: "Filings" },
      { id: "insider" as const, label: "Insider" },
    ],
    [],
  );

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">
          <div className="brandTitle">AgentBuffet</div>
          <div className="pill">{headerPill}</div>
        </div>
        <div className="search">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={loadingTickers ? "Loading tickers…" : "Search tickers…"}
          />
        </div>
        <div className="topbarRight">
          <LLMSettingsDropdown settings={llmSettings} setSettings={setLlmSettings} />
          <div className="pill">data: {"stocks/<TICKER>/*.json"}</div>
        </div>
      </div>

      <div className="grid">
        <div className="panel">
          <div className="panelHeader">
            <div className="panelTitle">Tickers</div>
            <div className="small">{filtered.length}</div>
          </div>
          <div className="tickerList">
            {tickerError ? <div className="content error">{tickerError}</div> : null}
            {!tickerError && filtered.map((t) => (
              <div
                key={t}
                className={`tickerItem ${t === selected ? "tickerItemActive" : ""}`}
                onClick={() => {
                  setSelected(t);
                  setQueryParam("t", t);
                  setTab("analysis");
                }}
                role="button"
                tabIndex={0}
              >
                <div className="tickerSym">{t}</div>
                <div className="tickerMeta">
                  <div className="tickerName">{t === selected ? (financials?.name ?? t) : t}</div>
                  <div className="tickerSub">
                    {t === selected && financials
                      ? `${financials.sector ?? "—"} • ${financials.industry ?? "—"}`
                      : " "}
                  </div>
                </div>
                {tickerActions[t] === "BUY" ? (
                  <span className="tickerTarget tickerTargetBuy">BUY</span>
                ) : tickerActions[t] === "SELL" || tickerActions[t] === "AVOID" ? (
                  <span className="tickerTarget tickerTargetSell">SELL</span>
                ) : null}
              </div>
            ))}
            {!tickerError && !filtered.length && !loadingTickers ? (
              <div className="content muted">No matches.</div>
            ) : null}
          </div>
        </div>

        <div className="panel">
          <div className="panelHeader">
            <div className="panelTitle">{selected || "—"}</div>
            <div className="small">{dataLoading ? "Loading…" : ""}</div>
          </div>
          <div className="content">
            <Tabs tabs={tabs} active={tab} onChange={setTab} />
            {dataError ? <div className="error">{dataError}</div> : null}

            {tab === "analysis" ? (
              selected ? (
                <>
                  {financials ? (
                    <div className="row">
                      <FinancialsPanel financials={financials} estimates={estimates} prices={prices} />
                    </div>
                  ) : null}
                  <AnalysisPanel
                    ticker={selected}
                    settings={llmSettings}
                    setSettings={setLlmSettings}
                    existingReport={report}
                    onReportUpdated={(r) => setReport(r)}
                  />
                </>
              ) : (
                <div className="muted">Select a ticker.</div>
              )
            ) : null}

            {tab === "news" ? (news ? <NewsList news={news} /> : <div className="muted">No news loaded.</div>) : null}

            {tab === "prices" ? (
              prices ? (
                <div className="row">
                  <PriceChart prices={prices} />
                </div>
              ) : (
                <div className="muted">No prices loaded.</div>
              )
            ) : null}

            {tab === "financials" ? (
              financials ? (
                <div className="row">
                  <FinancialsPanel financials={financials} estimates={estimates} prices={prices} />
                </div>
              ) : (
                <div className="muted">No financials loaded.</div>
              )
            ) : null}

            {tab === "filings" ? (
              filings ? <FilingsTable title="Filings" filings={filings} /> : <div className="muted">No filings loaded.</div>
            ) : null}

            {tab === "insider" ? (
              insider ? (
                <FilingsTable title="Insider filings" filings={insider} />
              ) : (
                <div className="muted">No insider filings loaded.</div>
              )
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

