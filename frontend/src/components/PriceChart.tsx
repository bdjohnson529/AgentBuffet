import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import type { PricesJson } from "../lib/types";
import { formatDateISO } from "../lib/format";

type Props = {
  prices: PricesJson;
};

export function PriceChart({ prices }: Props) {
  const data = (prices.series || []).map((p) => ({ date: p.date, close: p.close }));
  if (!data.length) return <div className="muted">No price series available.</div>;

  return (
    <div className="card" style={{ gridColumn: "span 12", padding: 10 }}>
      <div className="cardTitle">Close price (last {prices.summary?.periodDays ?? "—"} days)</div>
      <div style={{ height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.10)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(d) => formatDateISO(d)}
              minTickGap={42}
              stroke="rgba(255,255,255,0.45)"
            />
            <YAxis
              dataKey="close"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v) => `${v}`}
              stroke="rgba(255,255,255,0.45)"
              width={60}
            />
            <Tooltip
              formatter={(v) => [`${v}`, "Close"]}
              labelFormatter={(l) => formatDateISO(String(l))}
              contentStyle={{
                background: "rgba(10,14,22,0.92)",
                border: "1px solid rgba(255,255,255,0.14)",
                borderRadius: 12,
                color: "rgba(255,255,255,0.92)",
              }}
            />
            <Line
              type="monotone"
              dataKey="close"
              dot={false}
              strokeWidth={2}
              stroke="rgba(125, 211, 252, 0.95)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

