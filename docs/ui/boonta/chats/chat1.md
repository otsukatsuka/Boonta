# 競馬予想API画面設計

_Started 2026-04-25 11:39 UTC_

---

## User

GitHub connected

## Assistant

Hey! GitHub is connected. Drop a github.com repository URL in the chat and I'll explore the structure and pull in whatever files we need as reference for design work.

## User

githubとつながってる？Boontaってリポジトリがみえるとおもうんだけど、現状はCLIの競馬予想ツールになってる
これにAPIを生やして画面つくるとしたらどんなデザインになるか考えてみて

## Assistant

リポジトリ見てみますね。

_[tool: github_list_repos]_

Boontaリポジトリ見てみます。

_[tool: github_get_tree]_

READMEとCLAUDE.md、ソースを並列で見ます。

_[tool: github_read_file]_

_[tool: github_read_file]_

_[tool: github_read_file]_

_[tool: github_get_tree]_

_[tool: github_get_tree]_

中身把握しました。展開予想やbetting、tenkaiのアウトプット形を見て、実際の画面要素を具体化します。

_[tool: github_read_file]_

_[tool: github_read_file]_

_[tool: github_read_file]_

_[tool: github_read_file]_

_[tool: github_read_file]_

[I'll snip the heavy github exploration messages now that I have what I need internally.]

_[tool: snip]_

Boontaのリポジトリ全体を把握しました。CLIで動いてる中身を踏まえて、Web画面とAPIをデザインしていきますね。

その前に方向性を詰めたいので、いくつか質問させてください。

_[tool: questions_v2]_

## User

Questions answered:
- primary_screen: EV/回収率バックテスト画面（evaluate）, レース詳細（展開予想・位置取り・ML確率・買い目）, 予測ダッシュボード（日付指定→全レース一覧）
- user_persona: 自分専用（CLIの代替、データ密度マシマシでOK）
- aesthetic: Bloomberg / トレーディング端末風（情報密度高・等幅・データ第一）
- variations: 2〜3案を比較したい
- show_api: 画面デザインだけでOK、APIは別資料にする
- interactivity: クリックで画面遷移するくらいの軽めプロト
- key_visual: コーナー位置取り図（馬番が前/中/後で並ぶ）, EV単・EV複の散布図 or バブル, 買い目カード（単勝/複勝/馬連BOX/3連複/流し）
- color_mode: ダーク（トレーディング端末・夜間使用）
- tweaks: EV閾値（0.8〜1.5）
- extras: 他の競馬予想のサービスってどうもダサい。古き良きデザインって感じがするので絶対に参考にしないでほしい。斬新かつ大胆な発想で考えてほしい。

## Assistant

_[tool: update_todos]_

[Plan locked in: data-dense Bloomberg-terminal aesthetic, dark, 3 screens, with 2-3 variations exposed via design_canvas. Key data shapes captured: race_key (場2+年2+回1+日1+R2), pace H/M/S, running_style 1-4 (逃/先/差/追), goal_position, goal_io 1-5, predict_prob, ev_tan/ev_fuku, betting types (tansho/fukusho/umaren BOX/sanrenpuku BOX/nagashi). VENUE_NAMES 01札幌〜10小倉. Strategies: fukusho_top3, umaren_top2, sanrenpuku_top3, ev_tansho, ev_fukusho, ev_sanrenpuku_nagashi.]

設計方向を決めました:
- **コンセプト**: "RACE TERMINAL" — Bloomberg端末を競馬予想に転用したらこうなるはず、という大胆な解釈
- **タイポ**: JetBrains Mono（数値・コード）+ Inter Tight（見出し）
- **配色**: 深い黒（oklch低彩度）+ ターミナル定番のアンバー/シアン/ブライトグリーン
- **3画面**: Dashboard（日付→全レース） / Race Detail（展開・コーナー位置取り図・ML・EV散布・買い目）/ Backtest（戦略×ROI）
- **3バリエーション**:
  - **A. CLASSIC TERMINAL**: 緑＋アンバーの古典的端末色、行密度MAX、罫線ベース
  - **B. NEO TRADING**: モダントレーディング風（Bloomberg黒+オレンジアクセント）、ヒートマップやスパークラインを多用
  - **C. RADAR**: コーナー位置取りをトラック俯瞰のレーダー風に大胆ビジュアル化、EVを軌跡で見せる

まずdesign_canvasと共通スタイルから組みます。

_[tool: snip]_

_[tool: copy_starter_component]_

_[tool: copy_starter_component]_

_[tool: write_file]_

_[tool: write_file]_

[Snipping resolved earlier phases.]

_[tool: snip]_

Now let me build the screens. I'll create three screen JSX files (Dashboard, Race Detail, Backtest) for variation A "CLASSIC TERMINAL", then variation B will be a styled remix layered on top.

_[tool: write_file]_

_[tool: snip]_

_[tool: write_file]_

_[tool: snip]_

Now let me build variation B (NEO TRADING) and the design canvas index.

_[tool: write_file]_

_[tool: snip]_

Now let me build variation C (RADAR) with a bold track-overhead visualization, and the design canvas index.

_[tool: write_file]_

_[tool: write_file]_

_[tool: snip]_

_[tool: done]_

_[tool: snip]_

_[tool: fork_verifier_agent]_

できました。Boontaのリポジトリを読んだ上で、競馬予想サービスにありがちな「古き良き」感を完全に避けて、**Bloombergトレーディング端末風** に振り切った提案にしました。

**3バリアント × 3画面** をひとつのキャンバスに並べてあります:

- **A. CLASSIC TERMINAL** — 罫線ベース・行密度MAX。Dashboard / Race Detail / Backtest 全部入り。CLIの`predict`/`evaluate`をそのまま端末画面に焼き直したイメージ
- **B. NEO TRADING** — 上部に流れるTAPE（ティッカー）、ビッグナンバー帯、レースカードでEVバーが効く
- **C. RADAR** — トラック俯瞰のレーダー風レーダーチャートでコーナー位置取りを視覚化、EVゲージ付き

**画面の中身は全部CLI出力と紐付け**:
- `race_key` (場2+年2+回1+日1+R2) を画面に明示
- 位置取り図は道中→後3F→ゴールの順位推移
- EV散布図にiso EV線（閾値の等高線）
- 買い目は単勝/複勝/馬連BOX/3連複BOX/軸1頭流しまで網羅

**Tweaks** で `EV閾値 0.80〜1.50` を動かせるので、BUY/WATCH/SKIPの判定がリアルタイムで変わります。

API設計は別資料、というご指定なのでこちらでは触れていません。気になった画面があれば、その方向でさらに作り込みます。

## User

めっちゃいいね！
VARIANT A · CLASSIC TERMINAL
でいこう！

## Assistant

VARIANT Aで進めましょう！キャンバスを Variant A 中心の構成に整理して、3画面（Dashboard / Race Detail / Backtest）を主役にします。

_[tool: snip]_

_[tool: copy_files]_

[Variant A is the chosen direction. Reorganizing canvas: lead with the 3 main screens at full size, drop B/C, optionally add a fullscreen prototype link.]

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: str_replace_edit]_

_[tool: snip]_

_[tool: done]_

[Cleaning up earlier work to free space.]

_[tool: snip]_

CLASSIC TERMINALに絞って、3画面 + フルプロトタイプ（タブ切替・Tweaks動作）の構成にしました。

- **MAIN SCREENS**: Dashboard / Race Detail / Backtest を1400×820で並列表示
- **LIVE PROTOTYPE**: タブ切替・EV閾値Tweakが動く完成形

旧版は `Boonta Web Design v1.html` に保存してあります。次に詰めたい画面や追加で見たい要素があれば教えてください。

