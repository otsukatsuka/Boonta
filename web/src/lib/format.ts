export const fmtJPY = (n: number) => "¥" + n.toLocaleString("ja-JP");
export const fmtPct = (n: number, d = 1) => (n * 100).toFixed(d) + "%";
export const fmtNum = (n: number, d = 2) => n.toFixed(d);

export const PACE_LABEL: Record<string, string> = { H: "ハイ", M: "ミドル", S: "スロー" };
export const STYLE_LABEL: Record<number, string> = { 1: "逃", 2: "先", 3: "差", 4: "追" };
export const STYLE_LONG: Record<number, string> = { 1: "逃げ", 2: "先行", 3: "差し", 4: "追込" };
export const IO_LABEL: Record<number, string> = { 1: "最内", 2: "内", 3: "中", 4: "外", 5: "大外" };

export function parseRaceKey(k: string) {
  return {
    venue_code: k.slice(0, 2),
    year: k.slice(2, 4),
    kai: k.slice(4, 5),
    nichi: k.slice(5, 6),
    race_no: parseInt(k.slice(6, 8), 10),
  };
}
