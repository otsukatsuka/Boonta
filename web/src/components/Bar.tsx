export function Bar({
  value,
  max = 1,
  color = "amber",
  w = 80,
}: {
  value: number;
  max?: number;
  color?: "amber" | "green" | "cyan";
  w?: number;
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="bar-bg" style={{ width: w }}>
      <div className={"bar-fill " + color} style={{ width: pct + "%" }} />
    </div>
  );
}
