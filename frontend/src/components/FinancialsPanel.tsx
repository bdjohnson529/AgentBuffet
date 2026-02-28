import type { FinancialsJson, EstimatesJson, PricesJson } from "../lib/types";
import { formatNumberCompact, formatPercent } from "../lib/format";

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
  const currentPrice =
    prices?.summary?.lastClose !== undefined && prices?.summary?.lastClose !== null
      ? prices.summary.lastClose.toFixed(2)
      : null;

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

      <div className="card" style={{ gridColumn: "span 12" }}>
        <div className="statsCompact">
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Market cap</span>
            <span className="statsCompactValue">{formatNumberCompact(financials.marketCap)} {currency}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Enterprise value</span>
            <span className="statsCompactValue">{formatNumberCompact(financials.enterpriseValue)} {currency}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">P/E (ttm)</span>
            <span className="statsCompactValue">{financials.trailingPE?.toFixed(2) ?? "—"}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">P/E (fwd)</span>
            <span className="statsCompactValue">{financials.forwardPE?.toFixed(2) ?? "—"}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Revenue</span>
            <span className="statsCompactValue">{formatNumberCompact(financials.revenue)} {currency}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Rev growth</span>
            <span className="statsCompactValue">{formatPercent(financials.revenueGrowth)}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Earnings growth</span>
            <span className="statsCompactValue">{formatPercent(financials.earningsGrowth)}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">FCF</span>
            <span className="statsCompactValue">{formatNumberCompact(financials.freeCashFlow)} {currency}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Gross margin</span>
            <span className="statsCompactValue">{formatPercent(financials.grossMargins)}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Operating margin</span>
            <span className="statsCompactValue">{formatPercent(financials.operatingMargins)}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Profit margin</span>
            <span className="statsCompactValue">{formatPercent(financials.profitMargins)}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">ROE</span>
            <span className="statsCompactValue">{formatPercent(financials.roe)}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">52W low</span>
            <span className="statsCompactValue">{financials["52WeekLow"]?.toFixed(2) ?? "—"}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">52W high</span>
            <span className="statsCompactValue">{financials["52WeekHigh"]?.toFixed(2) ?? "—"}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">1Y return</span>
            <span className="statsCompactValue">{ret}</span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Daily vol (std dev)</span>
            <span className="statsCompactValue">{vol}</span>
          </div>
        </div>

        <hr className="statsSectionDivider" />
        <div className="statsSubsectionTitle">Estimates</div>
        <div className="statsCompact">
          {currentPrice != null && (
            <div className="statsCompactItem">
              <span className="statsCompactLabel">Current price</span>
              <span className="statsCompactValue">{currentPrice} {currency}</span>
            </div>
          )}
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Target mean</span>
            <span className="statsCompactValue">
              {estimates?.targetMeanPrice != null ? estimates.targetMeanPrice.toFixed(2) : "—"}
            </span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Target range</span>
            <span className="statsCompactValue">
              {estimates?.targetLowPrice != null && estimates?.targetHighPrice != null
                ? `${estimates.targetLowPrice.toFixed(2)} – ${estimates.targetHighPrice.toFixed(2)}`
                : "—"}
            </span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Analyst opinions</span>
            <span className="statsCompactValue">
              {estimates?.numberOfAnalystOpinions?.toString() ?? "—"}
            </span>
          </div>
          <div className="statsCompactItem">
            <span className="statsCompactLabel">Recommendation</span>
            <span className="statsCompactValue">
              {estimates?.recommendationKey ?? "—"}
            </span>
          </div>
        </div>
      </div>
    </>
  );
}

