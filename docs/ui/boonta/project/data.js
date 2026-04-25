// Sample race data shaped after Boonta's KYI/SED-derived features.
// race_key = 場(2) + 年(2) + 回(1) + 日(1,hex) + R(2)
window.BOONTA_DATA = (function () {
  const VENUES = {
    "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
    "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉",
  };

  const TODAY = "2026-04-25";

  // 6 races for the dashboard
  const RACES = [
    {
      race_key: "05260411", venue_code: "05", venue: "東京", race_no: 11,
      name: "天皇賞・春", grade: "G1", surface: "芝", distance: 3200,
      condition: "良", weather: "晴", post_time: "15:40",
      head_count: 16, pace: "M",
      best_ev_tan: 1.42, best_ev_fuku: 1.18,
      ml_top: { umaban: 7, name: "ヒシマサル", prob: 0.524 },
      status: "OPEN",
    },
    {
      race_key: "05260410", venue_code: "05", venue: "東京", race_no: 10,
      name: "青葉賞", grade: "G2", surface: "芝", distance: 2400,
      condition: "良", weather: "晴", post_time: "15:00",
      head_count: 18, pace: "S",
      best_ev_tan: 1.08, best_ev_fuku: 0.94,
      ml_top: { umaban: 12, name: "サクラランドマーク", prob: 0.412 },
      status: "OPEN",
    },
    {
      race_key: "06260411", venue_code: "06", venue: "中山", race_no: 11,
      name: "京葉ステークス", grade: "OP", surface: "ダ", distance: 1200,
      condition: "良", weather: "曇", post_time: "15:35",
      head_count: 14, pace: "H",
      best_ev_tan: 1.61, best_ev_fuku: 1.32,
      ml_top: { umaban: 4, name: "テンノカケラ", prob: 0.478 },
      status: "OPEN",
    },
    {
      race_key: "06260410", venue_code: "06", venue: "中山", race_no: 10,
      name: "下総ステークス", grade: "L", surface: "ダ", distance: 1800,
      condition: "稍", weather: "曇", post_time: "15:00",
      head_count: 16, pace: "M",
      best_ev_tan: 0.92, best_ev_fuku: 0.86,
      ml_top: { umaban: 9, name: "ガリバーストーム", prob: 0.388 },
      status: "OPEN",
    },
    {
      race_key: "09260411", venue_code: "09", venue: "阪神", race_no: 11,
      name: "マイラーズC", grade: "G2", surface: "芝", distance: 1600,
      condition: "良", weather: "晴", post_time: "15:35",
      head_count: 17, pace: "H",
      best_ev_tan: 1.24, best_ev_fuku: 1.05,
      ml_top: { umaban: 11, name: "ブライトホライズン", prob: 0.451 },
      status: "OPEN",
    },
    {
      race_key: "09260410", venue_code: "09", venue: "阪神", race_no: 10,
      name: "梅田ステークス", grade: "OP", surface: "芝", distance: 2000,
      condition: "良", weather: "晴", post_time: "15:00",
      head_count: 13, pace: "M",
      best_ev_tan: 0.78, best_ev_fuku: 0.81,
      ml_top: { umaban: 3, name: "アサキミドリ", prob: 0.342 },
      status: "OPEN",
    },
  ];

  // ── 天皇賞・春 detailed horse-level data ─────────
  const HORSES_TENNOH = [
    // umaban, waku, name, jockey, weight, running_style(1-4), idm,
    // mid_position, late3f_position, goal_position, goal_io(1-5),
    // odds, fukusho_odds, predict_prob, gate_miss_rate, upset_index, popularity, jockey_index
    { n: 1, w: 1, name: "ノーザンクラウン", jky: "戸崎圭太", wt: 58.0, rs: 2, idm: 58.4, midp: 4, latep: 6, goalp: 5, io: 2, odds: 12.4, fuku: 3.2, prob: 0.31, miss: 3.2, upset: 42, pop: 5, jky_i: 62 },
    { n: 2, w: 1, name: "シャイニングロー", jky: "横山武史", wt: 58.0, rs: 3, idm: 55.1, midp: 9, latep: 7, goalp: 8, io: 3, odds: 28.5, fuku: 6.8, prob: 0.18, miss: 4.1, upset: 65, pop: 8, jky_i: 70 },
    { n: 3, w: 2, name: "ヴィクトリーロード", jky: "C.ルメール", wt: 58.0, rs: 2, idm: 61.8, midp: 3, latep: 4, goalp: 3, io: 2, odds: 5.8, fuku: 1.9, prob: 0.41, miss: 2.8, upset: 38, pop: 3, jky_i: 88 },
    { n: 4, w: 2, name: "アースシェイカー", jky: "武豊", wt: 58.0, rs: 4, idm: 56.7, midp: 14, latep: 10, goalp: 11, io: 4, odds: 42.1, fuku: 9.4, prob: 0.13, miss: 6.5, upset: 78, pop: 11, jky_i: 75 },
    { n: 5, w: 3, name: "クレストオブザサン", jky: "川田将雅", wt: 58.0, rs: 1, idm: 59.2, midp: 1, latep: 3, goalp: 6, io: 3, odds: 9.7, fuku: 2.6, prob: 0.34, miss: 2.1, upset: 51, pop: 4, jky_i: 84 },
    { n: 6, w: 3, name: "テンペストキング", jky: "松山弘平", wt: 58.0, rs: 3, idm: 54.3, midp: 11, latep: 9, goalp: 10, io: 4, odds: 67.3, fuku: 14.2, prob: 0.09, miss: 5.8, upset: 82, pop: 13, jky_i: 60 },
    { n: 7, w: 4, name: "ヒシマサル", jky: "横山典弘", wt: 58.0, rs: 2, idm: 64.5, midp: 2, latep: 2, goalp: 1, io: 1, odds: 3.4, fuku: 1.4, prob: 0.524, miss: 1.8, upset: 28, pop: 1, jky_i: 78 },
    { n: 8, w: 4, name: "ブルーノヴァ", jky: "三浦皇成", wt: 58.0, rs: 3, idm: 53.8, midp: 12, latep: 11, goalp: 13, io: 4, odds: 89.4, fuku: 18.1, prob: 0.07, miss: 7.2, upset: 88, pop: 15, jky_i: 58 },
    { n: 9, w: 5, name: "サンライズコメット", jky: "福永祐一", wt: 58.0, rs: 4, idm: 57.9, midp: 13, latep: 5, goalp: 4, io: 5, odds: 18.6, fuku: 4.5, prob: 0.27, miss: 4.4, upset: 71, pop: 6, jky_i: 80 },
    { n: 10, w: 5, name: "オリオンの誓い", jky: "岩田望来", wt: 58.0, rs: 3, idm: 55.6, midp: 10, latep: 8, goalp: 9, io: 3, odds: 36.2, fuku: 7.9, prob: 0.16, miss: 5.1, upset: 73, pop: 9, jky_i: 67 },
    { n: 11, w: 6, name: "プラチナエッジ", jky: "M.デムーロ", wt: 58.0, rs: 2, idm: 60.4, midp: 5, latep: 4, goalp: 2, io: 1, odds: 4.9, fuku: 1.7, prob: 0.456, miss: 2.4, upset: 35, pop: 2, jky_i: 86 },
    { n: 12, w: 6, name: "ストームランナー", jky: "津村明秀", wt: 58.0, rs: 3, idm: 52.1, midp: 15, latep: 13, goalp: 14, io: 5, odds: 124.0, fuku: 25.3, prob: 0.05, miss: 8.4, upset: 91, pop: 16, jky_i: 55 },
    { n: 13, w: 7, name: "ヴェラジオドリーム", jky: "池添謙一", wt: 58.0, rs: 1, idm: 58.0, midp: 1, latep: 5, goalp: 7, io: 4, odds: 14.8, fuku: 3.8, prob: 0.24, miss: 3.7, upset: 58, pop: 7, jky_i: 73 },
    { n: 14, w: 7, name: "シルクラフィット", jky: "藤岡佑介", wt: 58.0, rs: 2, idm: 56.2, midp: 6, latep: 7, goalp: 8, io: 3, odds: 31.5, fuku: 7.2, prob: 0.17, miss: 3.9, upset: 62, pop: 10, jky_i: 65 },
    { n: 15, w: 8, name: "アーガティアラ", jky: "坂井瑠星", wt: 58.0, rs: 3, idm: 54.8, midp: 9, latep: 12, goalp: 12, io: 2, odds: 56.2, fuku: 11.5, prob: 0.11, miss: 6.0, upset: 80, pop: 12, jky_i: 71 },
    { n: 16, w: 8, name: "ファントムリーフ", jky: "石川裕紀人", wt: 58.0, rs: 4, idm: 53.0, midp: 16, latep: 14, goalp: 15, io: 5, odds: 78.9, fuku: 16.4, prob: 0.08, miss: 7.8, upset: 86, pop: 14, jky_i: 56 },
  ];

  // EV calculations
  HORSES_TENNOH.forEach(h => {
    h.ev_tan = +(h.prob / 3 * h.odds).toFixed(2);
    h.ev_fuku = +(h.prob * h.fuku).toFixed(2);
  });

  // Strategies for backtest
  const STRATEGIES = [
    { id: "fukusho_top3", label: "fukusho_top3", kind: "ML", races: 3453, bet_races: 3453, invested: 1035900, returned: 803254, hits: 1842 },
    { id: "umaren_top2", label: "umaren_top2", kind: "ML", races: 3453, bet_races: 3453, invested: 345300, returned: 268120, hits: 412 },
    { id: "sanrenpuku_top3", label: "sanrenpuku_top3", kind: "ML", races: 3453, bet_races: 3453, invested: 345300, returned: 287340, hits: 248 },
    { id: "ev_tansho", label: "ev_tansho", kind: "EV", races: 3453, bet_races: 1802, invested: 540000, returned: 525300, hits: 287 },
    { id: "ev_fukusho", label: "ev_fukusho", kind: "EV", races: 3453, bet_races: 2104, invested: 632100, returned: 651840, hits: 624 },
    { id: "ev_sanrenpuku_nagashi", label: "ev_sanrenpuku_nagashi", kind: "EV", races: 3453, bet_races: 1488, invested: 892800, returned: 956320, hits: 198 },
  ];

  STRATEGIES.forEach(s => { s.roi = +(s.returned / s.invested * 100).toFixed(1); });

  // Equity curve sample points (monthly cum P&L)
  const MONTHS = ["2025-01","2025-02","2025-03","2025-04","2025-05","2025-06","2025-07","2025-08","2025-09","2025-10","2025-11","2025-12"];
  function curve(seed) {
    let v = 0;
    return MONTHS.map((m, i) => {
      const r = ((Math.sin(seed + i * 1.3) + Math.cos(seed * 1.7 + i * 0.7)) * 0.5 + (Math.random() - 0.5) * 0.4) * (seed * 8000 + 4000);
      v += r;
      return { month: m, cum: Math.round(v) };
    });
  }
  STRATEGIES.forEach((s, i) => { s.equity = curve(0.5 + i * 0.4); });

  return { TODAY, VENUES, RACES, HORSES_TENNOH, STRATEGIES };
})();
