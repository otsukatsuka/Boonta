"""HJC (払戻データ) field definitions. Record length: 444 bytes (+2 CRLF).

HJC has repeating (OCC) structures for each bet type.
We flatten them into individual columns: e.g. 単勝馬番_1, 単勝払戻_1, etc.
"""
from src.parser.spec import FieldSpec

RECORD_LENGTH = 444  # JRDB spec "444 BYTE" includes CRLF


def _build_hjc_fields() -> list[FieldSpec]:
    """Build HJC field specs with repeating structures expanded."""
    fields: list[FieldSpec] = [
        # レースキー
        FieldSpec("場コード",  1,  2, "numeric", description="場コード"),
        FieldSpec("年",        3,  2, "numeric", description="年"),
        FieldSpec("回",        5,  1, "numeric", description="回"),
        FieldSpec("日",        6,  1, "hex",     description="日(16進数)"),
        FieldSpec("R",         7,  2, "numeric", description="レース番号"),
    ]

    # 単勝払戻: 3回, offset=9, 各9バイト (馬番2 + 払戻金7)
    offset = 9
    for i in range(1, 4):
        fields.append(FieldSpec(f"単勝馬番_{i}",  offset,     2, "numeric"))
        fields.append(FieldSpec(f"単勝払戻_{i}",  offset + 2, 7, "numeric"))
        offset += 9

    # 複勝払戻: 5回, offset=36, 各9バイト (馬番2 + 払戻金7)
    offset = 36
    for i in range(1, 6):
        fields.append(FieldSpec(f"複勝馬番_{i}",  offset,     2, "numeric"))
        fields.append(FieldSpec(f"複勝払戻_{i}",  offset + 2, 7, "numeric"))
        offset += 9

    # 枠連払戻: 3回, offset=81, 各9バイト (枠番組合せ2 + 払戻金7)
    offset = 81
    for i in range(1, 4):
        fields.append(FieldSpec(f"枠連組合せ_{i}", offset,     2, "text"))
        fields.append(FieldSpec(f"枠連払戻_{i}",   offset + 2, 7, "numeric"))
        offset += 9

    # 馬連払戻: 3回, offset=108, 各12バイト (馬番組合せ4 + 払戻金8)
    offset = 108
    for i in range(1, 4):
        fields.append(FieldSpec(f"馬連組合せ_{i}", offset,     4, "text"))
        fields.append(FieldSpec(f"馬連払戻_{i}",   offset + 4, 8, "numeric"))
        offset += 12

    # ワイド払戻: 7回, offset=144, 各12バイト (馬番組合せ4 + 払戻金8)
    offset = 144
    for i in range(1, 8):
        fields.append(FieldSpec(f"ワイド組合せ_{i}", offset,     4, "text"))
        fields.append(FieldSpec(f"ワイド払戻_{i}",   offset + 4, 8, "numeric"))
        offset += 12

    # 馬単払戻: 6回, offset=228, 各12バイト (馬番組合せ4 + 払戻金8)
    offset = 228
    for i in range(1, 7):
        fields.append(FieldSpec(f"馬単組合せ_{i}", offset,     4, "text"))
        fields.append(FieldSpec(f"馬単払戻_{i}",   offset + 4, 8, "numeric"))
        offset += 12

    # 3連複払戻: 3回, offset=300, 各14バイト (馬番組合せ6 + 払戻金8)
    offset = 300
    for i in range(1, 4):
        fields.append(FieldSpec(f"三連複組合せ_{i}", offset,     6, "text"))
        fields.append(FieldSpec(f"三連複払戻_{i}",   offset + 6, 8, "numeric"))
        offset += 14

    # 3連単払戻: 6回, offset=342, 各15バイト (馬番組合せ6 + 払戻金9)
    offset = 342
    for i in range(1, 7):
        fields.append(FieldSpec(f"三連単組合せ_{i}", offset,     6, "text"))
        fields.append(FieldSpec(f"三連単払戻_{i}",   offset + 6, 9, "numeric"))
        offset += 15

    return fields


HJC_FIELDS: list[FieldSpec] = _build_hjc_fields()
