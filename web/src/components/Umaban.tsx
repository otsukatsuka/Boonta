export function Umaban({
  n,
  waku,
  sm = false,
}: {
  n: number;
  waku: number;
  sm?: boolean;
}) {
  return (
    <span className={`umaban waku-${waku} ${sm ? "umaban-sm" : ""}`}>{n}</span>
  );
}
