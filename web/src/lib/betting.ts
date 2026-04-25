/**
 * EV computation + bet combo generation. Mirrors src/predict/betting.py so the
 * UI can react to slider changes without a server round-trip.
 *
 * EV formulas (must match _compute_race_ev / compute_expected_values):
 *   ev_tan  = (prob / 3) * odds
 *   ev_fuku = prob * fukusho_odds
 */
import type { BetPlan, Horse, NagashiPlan } from "../api/types";

export function recomputeEV(h: Horse): { ev_tan: number | null; ev_fuku: number | null } {
  const ev_tan =
    h.prob != null && h.odds != null && Number.isFinite(h.odds)
      ? (h.prob / 3) * h.odds
      : null;
  const ev_fuku =
    h.prob != null && h.fukusho_odds != null && Number.isFinite(h.fukusho_odds)
      ? h.prob * h.fukusho_odds
      : null;
  return { ev_tan, ev_fuku };
}

export function withRecomputedEV(horses: Horse[]): Horse[] {
  return horses.map((h) => {
    const { ev_tan, ev_fuku } = recomputeEV(h);
    return { ...h, ev_tan, ev_fuku };
  });
}

function combinations<T>(arr: T[], k: number): T[][] {
  const out: T[][] = [];
  const combo: T[] = [];
  function go(start: number) {
    if (combo.length === k) {
      out.push([...combo]);
      return;
    }
    for (let i = start; i < arr.length; i++) {
      combo.push(arr[i]);
      go(i + 1);
      combo.pop();
    }
  }
  go(0);
  return out;
}

export function buildBetPlan(
  horses: Horse[],
  evThreshold: number,
  opts: { maxTan?: number; boxSize?: number; trifectaBoxSize?: number; maxPartners?: number } = {},
): BetPlan {
  const maxTan = opts.maxTan ?? 5;
  const boxSize = opts.boxSize ?? 3;
  const trifectaBoxSize = opts.trifectaBoxSize ?? 4;
  const maxPartners = opts.maxPartners ?? 5;

  const sortedByEvTan = [...horses]
    .filter((h) => h.ev_tan != null)
    .sort((a, b) => (b.ev_tan! - a.ev_tan!));

  const tansho = sortedByEvTan
    .filter((h) => h.ev_tan! > evThreshold)
    .slice(0, maxTan)
    .map((h) => h.horse_number);

  const fukusho = horses
    .filter((h) => h.ev_fuku != null && h.ev_fuku > evThreshold)
    .sort((a, b) => (b.ev_fuku! - a.ev_fuku!))
    .map((h) => h.horse_number);

  const topBox = sortedByEvTan.slice(0, boxSize).map((h) => h.horse_number);
  const umaren_box =
    topBox.length >= 2 ? combinations([...topBox].sort((a, b) => a - b), 2) : [];

  const topTri = sortedByEvTan.slice(0, trifectaBoxSize).map((h) => h.horse_number);
  const sanrenpuku_box =
    topTri.length >= 3 ? combinations([...topTri].sort((a, b) => a - b), 3) : [];

  const nagashi: NagashiPlan = (() => {
    const axisCandidates = horses
      .filter((h) => h.ev_fuku != null && h.ev_fuku > evThreshold)
      .sort((a, b) => (b.ev_fuku! - a.ev_fuku!));
    if (axisCandidates.length === 0) return { axis: null, partners: [], combos: [] };
    const axis = axisCandidates[0].horse_number;
    const partners = sortedByEvTan
      .filter((h) => h.horse_number !== axis)
      .slice(0, maxPartners)
      .map((h) => h.horse_number);
    const combos = combinations(partners, 2).map((pair) =>
      [axis, ...pair].sort((a, b) => a - b),
    );
    return { axis, partners, combos };
  })();

  return { tansho, fukusho, umaren_box, sanrenpuku_box, nagashi };
}
