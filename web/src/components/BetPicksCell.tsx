import { useMemo } from "react";
import { buildBetPlan, withRecomputedEV } from "../lib/betting";
import type { Horse } from "../api/types";

export function BetPicksCell({
  horses,
  evThreshold,
}: {
  horses: Horse[];
  evThreshold: number;
}) {
  const plan = useMemo(
    () => buildBetPlan(withRecomputedEV(horses), evThreshold),
    [horses, evThreshold],
  );

  const counts = {
    tan: plan.tansho.length,
    fuku: plan.fukusho.length,
    umaren: plan.umaren_box.length,
    sanren: plan.sanrenpuku_box.length,
    nagashi: plan.nagashi.combos.length,
  };
  const total =
    counts.tan + counts.fuku + counts.umaren + counts.sanren + counts.nagashi;

  if (total === 0) {
    return <span className="dim">—</span>;
  }

  const Badge = ({ label, n }: { label: string; n: number }) => (
    <span
      className={"tnum " + (n > 0 ? "amb bold" : "dim")}
      style={{ marginRight: 6, fontSize: 10.5 }}
    >
      {label}
      {n}
    </span>
  );

  return (
    <span style={{ whiteSpace: "nowrap" }}>
      <Badge label="単" n={counts.tan} />
      <Badge label="複" n={counts.fuku} />
      <Badge label="馬連" n={counts.umaren} />
      <Badge label="3複" n={counts.sanren} />
      <Badge label="流" n={counts.nagashi} />
    </span>
  );
}
