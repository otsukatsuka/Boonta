"""BAC (番組データ) field definitions. Record length: 184 bytes (body 182 + CRLF).

BAC is the pre-race race-program file. Provides race-level metadata available
*before* the race runs (race name, distance, grade, post time, etc.) which
KYI does not carry.

Field offsets are 1-based (matching the JRDB official spec).
"""
from src.parser.spec import FieldSpec

RECORD_LENGTH = 184

# fmt: off
BAC_FIELDS: list[FieldSpec] = [
    # レースキー
    FieldSpec("場コード",       1,   2, "numeric",  description="場コード"),
    FieldSpec("年",             3,   2, "numeric",  description="年(下2桁)"),
    FieldSpec("回",             5,   1, "numeric",  description="回"),
    FieldSpec("日",             6,   1, "hex",      description="日(16進)"),
    FieldSpec("R",              7,   2, "numeric",  description="レース番号"),

    # レース基本情報
    FieldSpec("年月日",         9,   8, "text",     description="開催年月日(YYYYMMDD)"),
    FieldSpec("発走時間",      17,   4, "text",     description="発走時間(HHMM)"),
    FieldSpec("距離",          21,   4, "numeric",  description="距離(m)"),
    FieldSpec("芝ダ障害コード", 25,  1, "numeric",  description="1:芝 2:ダ 3:障"),
    FieldSpec("右左",          26,   1, "numeric",  description="右左コード"),
    FieldSpec("内外",          27,   1, "numeric",  description="内外コード"),
    FieldSpec("種別",          28,   2, "text",     description="種別コード"),
    FieldSpec("条件",          30,   2, "text",     description="条件コード"),
    FieldSpec("記号",          32,   3, "text",     description="記号(馬種別+性別+交流)"),
    FieldSpec("重量",          35,   1, "text",     description="重量コード"),
    FieldSpec("グレード",      36,   1, "numeric",  description="1:G1 2:G2 3:G3 4:重賞 5:特別 6:L"),
    FieldSpec("レース名",      37,  50, "text",     description="レース名(全角25文字)"),
    FieldSpec("回数",          87,   8, "text",     description="回数"),
    FieldSpec("頭数",          95,   2, "numeric",  description="頭数"),
    FieldSpec("コース",        97,   1, "numeric",  description="コース"),
    FieldSpec("開催区分",      98,   1, "numeric",  description="開催区分"),
    FieldSpec("レース名略称",  99,   8, "text",     description="レース名略称(全角4文字)"),
    FieldSpec("レース名9文字", 107, 18, "text",     description="レース名9文字"),
    FieldSpec("データ区分",   125,   1, "numeric",  description="データ区分"),

    # 賞金 (5 + 5 + 5 + 5 + 5 = 25 bytes)
    FieldSpec("1着賞金",      126,   5, "numeric",  description="1着本賞金(万円)"),
    FieldSpec("2着賞金",      131,   5, "numeric",  description="2着本賞金"),
    FieldSpec("3着賞金",      136,   5, "numeric",  description="3着本賞金"),
    FieldSpec("4着賞金",      141,   5, "numeric",  description="4着本賞金"),
    FieldSpec("5着賞金",      146,   5, "numeric",  description="5着本賞金"),
    FieldSpec("1着算入賞金",  151,   5, "numeric",  description="1着算入賞金"),
    FieldSpec("2着算入賞金",  156,   5, "numeric",  description="2着算入賞金"),

    # 馬券発売フラグ (それぞれ1byte)
    FieldSpec("単勝発売フラグ",       161, 1, "text"),
    FieldSpec("複勝発売フラグ",       162, 1, "text"),
    FieldSpec("枠連発売フラグ",       163, 1, "text"),
    FieldSpec("馬連発売フラグ",       164, 1, "text"),
    FieldSpec("ワイド発売フラグ",     165, 1, "text"),
    FieldSpec("馬単発売フラグ",       166, 1, "text"),
    FieldSpec("3連複発売フラグ",      167, 1, "text"),
    FieldSpec("3連単発売フラグ",      168, 1, "text"),
    # 169-176 reserved/unused
    FieldSpec("WIN5発売フラグ",       177, 1, "text"),
]
# fmt: on
