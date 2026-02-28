type Props = {
  title: string;
  value: string;
  note?: string;
  colSpan?: number;
};

export function StatCard({ title, value, note, colSpan = 3 }: Props) {
  const span = Math.max(1, Math.min(12, colSpan));
  return (
    <div className="card" style={{ gridColumn: `span ${span}` }}>
      <div className="cardTitle">{title}</div>
      <div className="cardValue">{value}</div>
      {note ? <div className="cardNote">{note}</div> : null}
    </div>
  );
}

