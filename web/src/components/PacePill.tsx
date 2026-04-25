import { PACE_LABEL } from "../lib/format";

export function PacePill({ pace }: { pace: string }) {
  return (
    <span className={"pace-pill " + pace}>
      {pace} {PACE_LABEL[pace] ?? ""}
    </span>
  );
}
