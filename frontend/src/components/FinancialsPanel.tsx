import type { FinancialsJson, EstimatesJson, PricesJson } from "../lib/types";
import { formatNumberCompact, formatPercent } from "../lib/format";
import { StatCard } from "./StatCard";

type Props = {
  financials: FinancialsJson;
  estimates?: EstimatesJson | null;
  prices?: PricesJson | null;
};

export function FinancialsPanel({ financials, estimates, prices }: Props) {
  const name = financials.name ?? financials.ticker;
  const sector = financials.sector ?? "—";
  const industry = financials.industry ?? "—";
  const currency = financials.currency ?? "USD";

  const ret =
    prices?.summary?.totalReturnPct !== undefined && prices?.summary?.totalReturnPct !== null
      ? `${prices.summary.totalReturnPct.toFixed(1)}%`
      : "—";
  const vol =
    prices?.summary?.dailyVolatility !== undefined && prices?.summary?.dailyVolatility !== null
      ? `${(prices.summary.dailyVolatility * 100).toFixed(2)}%`
      : "—";

  return (
    <>
      <div className="card" style={{ gridColumn: "span 12" }}>
        <div className="cardTitle">{financials.ticker}</div>
        <div className="cardValue" style={{ fontSize: 20 }}>
          {name}
        </div>
        <div className="cardNote">
          {sector} • {industry} • {currency}
        </div>
      </div>

      <div className="row">
        <StatCard title="Market cap" value={formatNumberCompact(financials.marketCap)} note={currency} />
        <StatCard
          title="Enterprise value"
          value={formatNumberCompact(financials.enterpriseValue)}
          note={currency}
        />
        <StatCard title="P/E (ttm)" value={financials.trailingPE?.toFixed(2) ?? "—"} />
        <StatCard title="P/E (fwd)" value={financials.forwardPE?.toFixed(2) ?? "—"} />

        <StatCard title="Revenue" value={formatNumberCompact(financials.revenue)} note={currency} />
        <StatCard title="Rev growth" value={formatPercent(financials.revenueGrowth)} />
        <StatCard title="Earnings growth" value={formatPercent(financials.earningsGrowth)} />
        <StatCard title="FCF" value={formatNumberCompact(financials.freeCashFlow)} note={currency} />

        <StatCard title="Gross margin" value={formatPercent(financials.grossMargins)} />
        <StatCard title="Operating margin" value={formatPercent(financials.operatingMargins)} />
        <StatCard title="Profit margin" value={formatPercent(financials.profitMargins)} />
        <StatCard title="ROE" value={formatPercent(financials.roe)} />

        <StatCard title="52W low" value={financials["52WeekLow"]?.toFixed(2) ?? "—"} />
        <StatCard title="52W high" value={financials["52WeekHigh"]?.toFixed(2) ?? "—"} />
        <StatCard title="1Y return" value={ret} />
        <StatCard title="Daily vol" value={vol} note="std dev" />
      </div>

      <div className="card" style={{ gridColumn: "span 12" }}>
        <div className="cardTitle">Estimates</div>
        {estimates ? (
          <div className="row" style={{ marginTop: 10 }}>
            <StatCard
              title="Target mean"
              value={estimates.targetMeanPrice ? estimates.targetMeanPrice.toFixed(2) : "—"}
            />
            <StatCard
              title="Target range"
              value={
                estimates.targetLowPrice && estimates.targetHighPrice
                  ? `${estimates.targetLowPrice.toFixed(2)} – ${estimates.targetHighPrice.toFixed(2)}`
                  : "—"
              }
              colSpan={4}
            />
            <StatCard
              title="Analyst opinions"
              value={estimates.numberOfAnalystOpinions?.toString() ?? "—"}
            />
            <StatCard title="Recommendation" value={estimates.recommendationKey ?? "—"} />
          </div>
        ) : (
          <div className="muted">No estimates data.</div>
        )}
      </div>
    </>
  );
}

