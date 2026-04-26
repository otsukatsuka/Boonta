"""CYB (調教分析データ) field definitions. Record length: 96 bytes (incl. CRLF)."""
from src.parser.spec import FieldSpec

RECORD_LENGTH = 96  # 94 body + CRLF 2

# fmt: off
CYB_FIELDS: list[FieldSpec] = [
    # レースキー + 馬番
    FieldSpec("場コード",     1,   2, "numeric"),
    FieldSpec("年",           3,   2, "numeric"),
    FieldSpec("回",           5,   1, "numeric"),
    FieldSpec("日",           6,   1, "hex"),
    FieldSpec("R",            7,   2, "numeric"),
    FieldSpec("馬番",         9,   2, "numeric"),

    # 調教内容
    FieldSpec("調教タイプ",   11,  2, "text",     description="調教タイプコード"),
    FieldSpec("調教コース種別", 13, 1, "text",    description="01=主場/02=場外等"),
    FieldSpec("調教コース_坂", 14, 2, "numeric", description="01:有/00:無"),
    FieldSpec("調教コース_W",  16, 2, "numeric"),
    FieldSpec("調教コース_ダ", 18, 2, "numeric"),
    FieldSpec("調教コース_芝", 20, 2, "numeric"),
    FieldSpec("調教コース_プ", 22, 2, "numeric", description="プール"),
    FieldSpec("調教コース_障", 24, 2, "numeric", description="障害練習"),
    FieldSpec("調教コース_ポ", 26, 2, "numeric", description="ポリトラック"),

    FieldSpec("調教距離",     28, 1, "text",      description="1:長め 2:普通 3:短め 4:2本"),
    FieldSpec("調教重点",     29, 1, "text",      description="1:テン 2:中間 3:終い 4:平均"),

    FieldSpec("追切指数",     30, 3, "numeric",   description="左詰め (既知バグ)"),
    FieldSpec("仕上指数",     33, 3, "numeric"),
    FieldSpec("調教量評価",   36, 1, "text",      description="A/B/C/D"),
    FieldSpec("仕上指数変化", 37, 1, "text"),

    FieldSpec("調教コメント", 38, 40, "text"),
    FieldSpec("コメント年月日", 78, 8, "text"),
    FieldSpec("調教評価",     86, 1, "text",      description="1:◎ 2:○ 3:△"),

    FieldSpec("一週前追切指数", 87, 3, "numeric"),
    FieldSpec("一週前追切コース", 90, 2, "numeric"),
]
# fmt: on
