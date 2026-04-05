"""Tests for FieldSpec and coerce function."""
from src.parser.spec import FieldSpec, coerce


class TestCoerce:
    def test_numeric_normal(self):
        assert coerce("123", "numeric") == 123

    def test_numeric_zero(self):
        assert coerce("0", "numeric") == 0

    def test_numeric_empty(self):
        assert coerce("", "numeric") is None

    def test_numeric_spaces(self):
        assert coerce("", "numeric") is None

    def test_numeric_with_minus(self):
        assert coerce("-5", "numeric", signed=True) == -5

    def test_text_normal(self):
        assert coerce("ディープインパクト", "text") == "ディープインパクト"

    def test_text_empty(self):
        assert coerce("", "text") is None

    def test_decimal_normal(self):
        assert coerce("12.3", "decimal", scale=1) == 12.3

    def test_decimal_integer_form(self):
        """ZZ9.9 format without decimal point is parsed as float."""
        assert coerce("123", "decimal", scale=1) == 123.0

    def test_decimal_empty(self):
        assert coerce("", "decimal", scale=1) is None

    def test_hex_normal(self):
        assert coerce("a", "hex") == 10

    def test_hex_digit(self):
        assert coerce("5", "hex") == 5

    def test_hex_empty(self):
        assert coerce("", "hex") is None

    def test_hex_f(self):
        assert coerce("f", "hex") == 15


class TestFieldSpec:
    def test_frozen(self):
        spec = FieldSpec("test", 1, 5, "numeric")
        assert spec.name == "test"
        assert spec.offset == 1
        assert spec.length == 5
        assert spec.field_type == "numeric"
        assert spec.scale == 0
        assert spec.signed is False

    def test_defaults(self):
        spec = FieldSpec("x", 1, 1, "text")
        assert spec.description == ""
