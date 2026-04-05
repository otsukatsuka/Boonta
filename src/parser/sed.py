"""SED (成績データ) field definitions. Record length: 376 bytes (+2 CRLF)."""
from src.parser.spec import FieldSpec

RECORD_LENGTH = 376  # JRDB spec "376 BYTE" includes CRLF

# fmt: off
SED_FIELDS: list[FieldSpec] = [
    # レースキー
    FieldSpec("場コード",       1,   2, "numeric",  description="場コード"),
    FieldSpec("年",             3,   2, "numeric",  description="年"),
    FieldSpec("回",             5,   1, "numeric",  description="回"),
    FieldSpec("日",             6,   1, "hex",      description="日(16進数)"),
    FieldSpec("R",              7,   2, "numeric",  description="レース番号"),
    FieldSpec("馬番",           9,   2, "numeric",  description="馬番"),

    # 競走成績キー
    FieldSpec("血統登録番号",  11,   8, "text",     description="血統登録番号"),
    FieldSpec("年月日",        19,   8, "text",     description="年月日(YYYYMMDD)"),

    FieldSpec("馬名",          27,  36, "text",     description="馬名(全角18文字)"),

    # レース条件
    FieldSpec("距離",          63,   4, "numeric",  description="距離(m)"),
    FieldSpec("芝ダ障害コード", 67,  1, "numeric",  description="1:芝,2:ダ,3:障害"),
    FieldSpec("右左",          68,   1, "numeric",  description="1:右,2:左,3:直,9:他"),
    FieldSpec("内外",          69,   1, "numeric",  description="1:内,2:外,3:直ダ,9:他"),
    FieldSpec("馬場状態",      70,   2, "numeric",  description="馬場状態コード"),
    FieldSpec("種別",          72,   2, "numeric",  description="種別コード"),
    FieldSpec("条件",          74,   2, "text",     description="条件コード"),
    FieldSpec("記号",          76,   3, "numeric",  description="記号コード"),
    FieldSpec("重量",          79,   1, "numeric",  description="重量区分"),
    FieldSpec("グレード",      80,   1, "numeric",  description="グレード"),
    FieldSpec("レース名",      81,  50, "text",     description="レース名(全角25文字)"),
    FieldSpec("頭数",         131,   2, "numeric",  description="出走頭数"),
    FieldSpec("レース名略称", 133,   8, "text",     description="レース名略称(全角4文字)"),

    # 馬成績
    FieldSpec("着順",         141,   2, "numeric",  description="着順"),
    FieldSpec("異常区分",     143,   1, "numeric",  description="異常区分"),
    FieldSpec("タイム",       144,   4, "numeric",  description="走破タイム"),
    FieldSpec("斤量",         148,   3, "numeric",  description="斤量(0.1kg単位)"),
    FieldSpec("騎手名",       151,  12, "text",     description="騎手名(全角6文字)"),
    FieldSpec("調教師名",     163,  12, "text",     description="調教師名(全角6文字)"),
    FieldSpec("確定単勝オッズ", 175, 6, "decimal", scale=1, description="確定単勝オッズ"),
    FieldSpec("確定単勝人気順位", 181, 2, "numeric", description="確定単勝人気順位"),

    # JRDBデータ
    FieldSpec("IDM",          183,   3, "numeric",  description="IDM"),
    FieldSpec("素点",         186,   3, "numeric",  description="素点"),
    FieldSpec("馬場差",       189,   3, "numeric",  description="馬場差"),
    FieldSpec("ペース",       192,   3, "numeric",  description="ペース"),
    FieldSpec("出遅",         195,   3, "numeric",  description="出遅"),
    FieldSpec("位置取",       198,   3, "numeric",  description="位置取"),
    FieldSpec("不利",         201,   3, "numeric",  description="不利"),
    FieldSpec("前不利",       204,   3, "numeric",  description="前3F不利"),
    FieldSpec("中不利",       207,   3, "numeric",  description="道中不利"),
    FieldSpec("後不利",       210,   3, "numeric",  description="後3F不利"),
    FieldSpec("レース_jrdb",  213,   3, "numeric",  description="レース評価"),
    FieldSpec("コース取り",   216,   1, "numeric",  description="1:最内~5:大外"),
    FieldSpec("上昇度コード", 217,   1, "numeric",  description="上昇度(1:AA~5:?)"),
    FieldSpec("クラスコード", 218,   2, "numeric",  description="クラスコード"),
    FieldSpec("馬体コード",   220,   1, "numeric",  description="馬体コード"),
    FieldSpec("気配コード",   221,   1, "numeric",  description="気配コード"),
    FieldSpec("レースペース", 222,   1, "text",     description="レースペース(H/M/S)"),
    FieldSpec("馬ペース",     223,   1, "text",     description="馬ペース(H/M/S)"),
    FieldSpec("テン指数",     224,   5, "decimal", scale=1, description="テン指数(実績)"),
    FieldSpec("上がり指数",   229,   5, "decimal", scale=1, description="上がり指数(実績)"),
    FieldSpec("ペース指数",   234,   5, "decimal", scale=1, description="ペース指数(実績)"),
    FieldSpec("レースP指数",  239,   5, "decimal", scale=1, description="レースP指数(実績)"),
    FieldSpec("1着馬名",      244,  12, "text",     description="1(2)着馬名"),
    FieldSpec("1着タイム差",  256,   3, "numeric",  description="1(2)着タイム差(0.1秒)"),
    FieldSpec("前3Fタイム",   259,   3, "numeric",  description="前3Fタイム(0.1秒)"),
    FieldSpec("後3Fタイム",   262,   3, "numeric",  description="後3Fタイム(0.1秒)"),
    FieldSpec("備考",         265,  24, "text",     description="備考(全角12文字)"),

    # 第2版追加
    FieldSpec("確定複勝オッズ下", 291, 6, "decimal", scale=1, description="確定複勝オッズ下"),
    FieldSpec("10時単勝オッズ",   297, 6, "decimal", scale=1, description="10時単勝オッズ"),
    FieldSpec("10時複勝オッズ",   303, 6, "decimal", scale=1, description="10時複勝オッズ"),
    FieldSpec("コーナー順位1",   309,  2, "numeric",  description="コーナー順位1"),
    FieldSpec("コーナー順位2",   311,  2, "numeric",  description="コーナー順位2"),
    FieldSpec("コーナー順位3",   313,  2, "numeric",  description="コーナー順位3"),
    FieldSpec("コーナー順位4",   315,  2, "numeric",  description="コーナー順位4"),
    FieldSpec("前3F先頭差",      317,  3, "numeric",  description="前3F先頭差(0.1秒)"),
    FieldSpec("後3F先頭差",      320,  3, "numeric",  description="後3F先頭差(0.1秒)"),
    FieldSpec("騎手コード",      323,  5, "text",     description="騎手コード"),
    FieldSpec("調教師コード",    328,  5, "text",     description="調教師コード"),

    # 第3版追加
    FieldSpec("馬体重",       333,   3, "numeric",  description="馬体重"),
    FieldSpec("馬体重増減",   336,   3, "text",     description="馬体重増減(符号+数字)"),
    FieldSpec("天候コード",   339,   1, "numeric",  description="天候コード"),
    FieldSpec("コース",       340,   1, "text",     description="コース(A,B,C,D等)"),
    FieldSpec("レース脚質",   341,   1, "text",     description="脚質コード"),

    # 第4版追加
    FieldSpec("単勝払戻",     342,   7, "numeric",  description="単勝払戻(円)"),
    FieldSpec("複勝払戻",     349,   7, "numeric",  description="複勝払戻(円)"),
    FieldSpec("本賞金",       356,   5, "numeric",  description="本賞金(万円)"),
    FieldSpec("収得賞金_sed", 361,   5, "numeric",  description="収得賞金(万円)"),
    FieldSpec("レースペース流れ", 366, 2, "numeric", description="レースペース流れ"),
    FieldSpec("馬ペース流れ", 368,   2, "numeric",  description="馬ペース流れ"),
    FieldSpec("4角コース取り", 370,  1, "numeric",  description="4角コース取り(1:最内~5:大外)"),
    FieldSpec("発走時間",     371,   4, "text",     description="発走時間(HHMM)"),
]
# fmt: on
