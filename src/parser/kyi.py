"""KYI (競走馬データ) field definitions. Record length: 1024 bytes (+2 CRLF)."""
from src.parser.spec import FieldSpec

RECORD_LENGTH = 1024  # JRDB spec "1024 BYTE" includes CRLF

# fmt: off
KYI_FIELDS: list[FieldSpec] = [
    # レースキー
    FieldSpec("場コード",       1,   2, "numeric",  description="場コード"),
    FieldSpec("年",             3,   2, "numeric",  description="年"),
    FieldSpec("回",             5,   1, "numeric",  description="回"),
    FieldSpec("日",             6,   1, "hex",      description="日(16進数)"),
    FieldSpec("R",              7,   2, "numeric",  description="レース番号"),
    FieldSpec("馬番",           9,   2, "numeric",  description="馬番"),
    FieldSpec("血統登録番号",   11,   8, "text",     description="血統登録番号"),
    FieldSpec("馬名",          19,  36, "text",     description="馬名(全角18文字)"),

    # 指数
    FieldSpec("IDM",           55,   5, "decimal", scale=1, description="IDM"),
    FieldSpec("騎手指数",      60,   5, "decimal", scale=1, description="騎手指数"),
    FieldSpec("情報指数",      65,   5, "decimal", scale=1, description="情報指数"),
    FieldSpec("総合指数",      85,   5, "decimal", scale=1, description="総合指数"),

    # 属性
    FieldSpec("脚質",          90,   1, "numeric",  description="脚質コード"),
    FieldSpec("距離適性",      91,   1, "numeric",  description="距離適性"),
    FieldSpec("上昇度",        92,   1, "numeric",  description="上昇度"),
    FieldSpec("ローテーション", 93,  3, "numeric",  description="ローテーション"),

    # オッズ・人気
    FieldSpec("基準オッズ",    96,   5, "decimal", scale=1, description="基準オッズ"),
    FieldSpec("基準人気順位", 101,   2, "numeric",  description="基準人気順位"),
    FieldSpec("基準複勝オッズ", 103, 5, "decimal", scale=1, description="基準複勝オッズ"),
    FieldSpec("基準複勝人気順位", 108, 2, "numeric", description="基準複勝人気順位"),

    # 情報印数
    FieldSpec("特定情報◎",   110,   3, "numeric",  description="特定情報◎"),
    FieldSpec("特定情報○",   113,   3, "numeric",  description="特定情報○"),
    FieldSpec("特定情報▲",   116,   3, "numeric",  description="特定情報▲"),
    FieldSpec("特定情報△",   119,   3, "numeric",  description="特定情報△"),
    FieldSpec("特定情報×",   122,   3, "numeric",  description="特定情報×"),
    FieldSpec("総合情報◎",   125,   3, "numeric",  description="総合情報◎"),
    FieldSpec("総合情報○",   128,   3, "numeric",  description="総合情報○"),
    FieldSpec("総合情報▲",   131,   3, "numeric",  description="総合情報▲"),
    FieldSpec("総合情報△",   134,   3, "numeric",  description="総合情報△"),
    FieldSpec("総合情報×",   137,   3, "numeric",  description="総合情報×"),
    FieldSpec("人気指数",     140,   5, "numeric",  description="人気指数"),
    FieldSpec("調教指数",     145,   5, "decimal", scale=1, description="調教指数"),
    FieldSpec("厩舎指数",     150,   5, "decimal", scale=1, description="厩舎指数"),

    # 第3版追加
    FieldSpec("調教矢印コード", 155, 1, "numeric",  description="調教矢印コード"),
    FieldSpec("厩舎評価コード", 156, 1, "numeric",  description="厩舎評価コード"),
    FieldSpec("騎手期待連対率", 157, 4, "decimal", scale=1, description="騎手期待連対率"),
    FieldSpec("激走指数",     161,   3, "numeric",  description="激走指数"),
    FieldSpec("蹄コード",     164,   2, "numeric",  description="蹄コード"),
    FieldSpec("重適正コード", 166,   1, "numeric",  description="重適正コード"),
    FieldSpec("クラスコード", 167,   2, "numeric",  description="クラスコード"),

    # 第4版追加
    FieldSpec("ブリンカー",   171,   1, "text",     description="ブリンカー"),
    FieldSpec("騎手名",       172,  12, "text",     description="騎手名(全角6文字)"),
    FieldSpec("負担重量",     184,   3, "numeric",  description="負担重量(0.1kg単位)"),
    FieldSpec("見習い区分",   187,   1, "numeric",  description="見習い区分"),
    FieldSpec("調教師名",     188,  12, "text",     description="調教師名(全角6文字)"),
    FieldSpec("調教師所属",   200,   4, "text",     description="調教師所属(全角2文字)"),

    # 前走リンクキー
    FieldSpec("前走1競走成績キー", 204, 16, "text", description="前走1競走成績キー"),
    FieldSpec("前走2競走成績キー", 220, 16, "text", description="前走2競走成績キー"),
    FieldSpec("前走3競走成績キー", 236, 16, "text", description="前走3競走成績キー"),
    FieldSpec("前走4競走成績キー", 252, 16, "text", description="前走4競走成績キー"),
    FieldSpec("前走5競走成績キー", 268, 16, "text", description="前走5競走成績キー"),
    FieldSpec("前走1レースキー",   284,  8, "text", description="前走1レースキー"),
    FieldSpec("前走2レースキー",   292,  8, "text", description="前走2レースキー"),
    FieldSpec("前走3レースキー",   300,  8, "text", description="前走3レースキー"),
    FieldSpec("前走4レースキー",   308,  8, "text", description="前走4レースキー"),
    FieldSpec("前走5レースキー",   316,  8, "text", description="前走5レースキー"),

    FieldSpec("枠番",         324,   1, "numeric",  description="枠番"),

    # 第5版追加 - 印コード
    FieldSpec("総合印",       327,   1, "numeric",  description="総合印コード"),
    FieldSpec("IDM印",        328,   1, "numeric",  description="IDM印コード"),
    FieldSpec("情報印",       329,   1, "numeric",  description="情報印コード"),
    FieldSpec("騎手印",       330,   1, "numeric",  description="騎手印コード"),
    FieldSpec("厩舎印",       331,   1, "numeric",  description="厩舎印コード"),
    FieldSpec("調教印",       332,   1, "numeric",  description="調教印コード"),
    FieldSpec("激走印",       333,   1, "numeric",  description="激走印(1=激走馬)"),
    FieldSpec("芝適性コード", 334,   1, "text",     description="芝適性(1:◎,2:○,3:△)"),
    FieldSpec("ダ適性コード", 335,   1, "text",     description="ダ適性(1:◎,2:○,3:△)"),
    FieldSpec("騎手コード",   336,   5, "text",     description="騎手コード"),
    FieldSpec("調教師コード", 341,   5, "text",     description="調教師コード"),

    # 第6版追加 - 賞金・展開予想
    FieldSpec("獲得賞金",     347,   6, "numeric",  description="獲得賞金(万円)"),
    FieldSpec("収得賞金",     353,   5, "numeric",  description="収得賞金(万円)"),
    FieldSpec("条件クラス",   358,   1, "numeric",  description="条件グループコード"),
    FieldSpec("テン指数",     359,   5, "decimal", scale=1, description="予想テン指数"),
    FieldSpec("ペース指数",   364,   5, "decimal", scale=1, description="予想ペース指数"),
    FieldSpec("上がり指数",   369,   5, "decimal", scale=1, description="予想上がり指数"),
    FieldSpec("位置指数",     374,   5, "decimal", scale=1, description="予想位置指数"),
    FieldSpec("ペース予想",   379,   1, "text",     description="ペース予想(H/M/S)"),
    FieldSpec("道中順位",     380,   2, "numeric",  description="道中順位"),
    FieldSpec("道中差",       382,   2, "numeric",  description="道中差(半馬身単位)"),
    FieldSpec("道中内外",     384,   1, "numeric",  description="道中内外(2:内~5:大外)"),
    FieldSpec("後3F順位",     385,   2, "numeric",  description="後3F順位"),
    FieldSpec("後3F差",       387,   2, "numeric",  description="後3F差(半馬身単位)"),
    FieldSpec("後3F内外",     389,   1, "numeric",  description="後3F内外(2:内~5:大外)"),
    FieldSpec("ゴール順位",   390,   2, "numeric",  description="ゴール順位"),
    FieldSpec("ゴール差",     392,   2, "numeric",  description="ゴール差(半馬身単位)"),
    FieldSpec("ゴール内外",   394,   1, "numeric",  description="ゴール内外(1:最内~5:大外)"),
    FieldSpec("展開記号",     395,   1, "text",     description="展開記号コード"),

    # 第6a版追加
    FieldSpec("距離適性2",    396,   1, "numeric",  description="距離適性2"),
    FieldSpec("枠確定馬体重", 397,   3, "numeric",  description="枠確定馬体重"),
    FieldSpec("枠確定馬体重増減", 400, 3, "text",   description="枠確定馬体重増減(符号+数字)"),

    # 第7版追加
    FieldSpec("取消フラグ",   403,   1, "numeric",  description="取消フラグ(1=取消)"),
    FieldSpec("性別コード",   404,   1, "numeric",  description="性別(1:牡,2:牝,3:セン)"),
    FieldSpec("馬主名",       405,  40, "text",     description="馬主名(全角20文字)"),
    FieldSpec("馬主会コード", 445,   2, "numeric",  description="馬主会コード"),
    FieldSpec("馬記号コード", 447,   2, "numeric",  description="馬記号コード"),
    FieldSpec("激走順位",     449,   2, "numeric",  description="激走順位"),
    FieldSpec("LS指数順位",   451,   2, "numeric",  description="LS指数順位"),
    FieldSpec("テン指数順位", 453,   2, "numeric",  description="テン指数順位"),
    FieldSpec("ペース指数順位", 455, 2, "numeric",  description="ペース指数順位"),
    FieldSpec("上がり指数順位", 457, 2, "numeric",  description="上がり指数順位"),
    FieldSpec("位置指数順位", 459,   2, "numeric",  description="位置指数順位"),

    # 第8版追加
    FieldSpec("騎手期待単勝率",   461, 4, "decimal", scale=1, description="騎手期待単勝率"),
    FieldSpec("騎手期待3着内率",  465, 4, "decimal", scale=1, description="騎手期待3着内率"),
    FieldSpec("輸送区分",         469, 1, "text",     description="輸送区分"),

    # 第9版追加
    FieldSpec("走法",         470,   8, "text",     description="走法コード"),
    FieldSpec("体型",         478,  24, "text",     description="体型コード"),
    FieldSpec("体型総合1",    502,   3, "text",     description="体型総合1特記コード"),
    FieldSpec("体型総合2",    505,   3, "text",     description="体型総合2特記コード"),
    FieldSpec("体型総合3",    508,   3, "text",     description="体型総合3特記コード"),
    FieldSpec("馬特記1",      511,   3, "text",     description="馬特記1特記コード"),
    FieldSpec("馬特記2",      514,   3, "text",     description="馬特記2特記コード"),
    FieldSpec("馬特記3",      517,   3, "text",     description="馬特記3特記コード"),

    # 展開参考データ
    FieldSpec("馬スタート指数", 520, 4, "decimal", scale=1, description="馬スタート指数"),
    FieldSpec("馬出遅率",     524,   4, "decimal", scale=1, description="馬出遅率(%)"),
    FieldSpec("参考前走",     528,   2, "numeric",  description="参考前走"),
    FieldSpec("参考前走騎手コード", 530, 5, "text", description="参考前走騎手コード"),
    FieldSpec("万券指数",     535,   3, "numeric",  description="万券指数"),
    FieldSpec("万券印",       538,   1, "numeric",  description="万券印"),

    # 第10版追加
    FieldSpec("降級フラグ",   539,   1, "numeric",  description="降級フラグ"),
    FieldSpec("激走タイプ",   540,   2, "text",     description="激走タイプ"),
    FieldSpec("休養理由分類コード", 542, 2, "numeric", description="休養理由分類コード"),

    # 第11版追加
    FieldSpec("フラグ",       544,  16, "text",     description="初芝初ダ初障などのフラグ"),
    FieldSpec("入厩何走目",   560,   2, "numeric",  description="入厩何走目"),
    FieldSpec("入厩年月日",   562,   8, "text",     description="入厩年月日(YYYYMMDD)"),
    FieldSpec("入厩何日前",   570,   3, "numeric",  description="入厩何日前"),
    FieldSpec("放牧先",       573,  50, "text",     description="放牧先"),
    FieldSpec("放牧先ランク", 623,   1, "text",     description="放牧先ランク(A-E)"),
    FieldSpec("厩舎ランク",   624,   1, "numeric",  description="厩舎ランク(1高-9低)"),
]
# fmt: on
