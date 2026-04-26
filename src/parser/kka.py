"""KKA (競走馬拡張データ) field definitions. Record length: 324 bytes (incl. CRLF).

Each "成績" group is 12 bytes = 1着数 (3) + 2着数 (3) + 3着数 (3) + 着外数 (3),
each ZZ9 (right-justified 3-digit number, blank when 0). We expose them as a
single text field (12 chars) and let downstream feature code split as needed.
"""
from src.parser.spec import FieldSpec

RECORD_LENGTH = 324


def _record_block(name: str, offset: int, description: str = "") -> FieldSpec:
    """Helper: 12-byte record (1着 / 2着 / 3着 / 着外, each ZZ9)."""
    return FieldSpec(name, offset, 12, "text", description=description)


# fmt: off
KKA_FIELDS: list[FieldSpec] = [
    FieldSpec("場コード", 1, 2, "numeric"),
    FieldSpec("年",       3, 2, "numeric"),
    FieldSpec("回",       5, 1, "numeric"),
    FieldSpec("日",       6, 1, "hex"),
    FieldSpec("R",        7, 2, "numeric"),
    FieldSpec("馬番",     9, 2, "numeric"),

    # 着度数 (1/2/3/着外)
    _record_block("JRA成績",           11),
    _record_block("交流成績",          23),
    _record_block("他成績",            35),
    # 該当条件別
    _record_block("芝ダ障害別成績",    47),
    _record_block("芝ダ障害別距離成績", 59),
    _record_block("トラック距離成績",   71),
    _record_block("ローテ成績",         83),
    _record_block("回り成績",           95),
    _record_block("騎手成績",          107),
    _record_block("良成績",            119),
    _record_block("稍成績",            131),
    _record_block("重成績",            143),
    _record_block("Sペース成績",       155),
    _record_block("Mペース成績",       167),
    _record_block("Hペース成績",       179),
    _record_block("季節成績",          191),
    _record_block("枠成績",            203),
    # 該当条件別 (騎手系)
    _record_block("騎手距離成績",      215),
    _record_block("騎手トラック距離成績", 227),
    _record_block("騎手調教師別成績",  239),
    _record_block("騎手馬主別成績",    251),
    _record_block("騎手ブリンカ成績",  263),
    _record_block("調教師馬主別成績",  275),

    # その他 — 種牡馬統計
    FieldSpec("父馬産駒芝連対率",      287, 3, "numeric", description="単位 %"),
    FieldSpec("父馬産駒ダ連対率",      290, 3, "numeric"),
    FieldSpec("父馬産駒連対平均距離",  293, 4, "numeric"),
    FieldSpec("母父馬産駒芝連対率",    297, 3, "numeric"),
    FieldSpec("母父馬産駒ダ連対率",    300, 3, "numeric"),
    FieldSpec("母父馬産駒連対平均距離", 303, 4, "numeric"),
]
# fmt: on
