import type { FilingsJson } from "../lib/types";
import { formatDateISO } from "../lib/format";

type Props = {
  title: string;
  filings: FilingsJson;
};

export function FilingsTable({ title, filings }: Props) {
  if (!filings.filings?.length) return <div className="muted">No {title.toLowerCase()}.</div>;
  return (
    <table className="table">
      <thead>
        <tr>
          <th style={{ width: "14%" }}>Date</th>
          <th style={{ width: "12%" }}>Form</th>
          <th>Description</th>
          <th style={{ width: "26%" }}>SEC</th>
        </tr>
      </thead>
      <tbody>
        {filings.filings.map((f, idx) => (
          <tr key={`${f.documentUrl}-${idx}`}>
            <td className="small">{formatDateISO(f.filingDate)}</td>
            <td style={{ fontFamily: "var(--mono)", fontWeight: 700 }}>{f.form}</td>
            <td className="small">{f.description ?? "—"}</td>
            <td className="small">
              <a className="linkOut" href={f.documentUrl} target="_blank" rel="noreferrer">
                {f.primaryDocument ?? "Open filing"}
              </a>
              {f.accessionNumber ? (
                <div className="small" style={{ marginTop: 6, fontFamily: "var(--mono)" }}>
                  {f.accessionNumber}
                </div>
              ) : null}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

