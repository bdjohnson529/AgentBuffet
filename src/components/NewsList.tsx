import type { NewsJson } from "../lib/types";
import { formatDateISO } from "../lib/format";

type Props = {
  news: NewsJson;
};

export function NewsList({ news }: Props) {
  if (!news.items?.length) return <div className="muted">No news items.</div>;
  return (
    <table className="table">
      <thead>
        <tr>
          <th style={{ width: "22%" }}>Published</th>
          <th>Title</th>
        </tr>
      </thead>
      <tbody>
        {news.items.map((it, idx) => (
          <tr key={`${it.link}-${idx}`}>
            <td className="small">{formatDateISO(it.published)}</td>
            <td>
              <a className="linkOut" href={it.link} target="_blank" rel="noreferrer">
                {it.title}
              </a>
              {it.summary ? <div className="small" style={{ marginTop: 6 }}>{it.summary}</div> : null}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

