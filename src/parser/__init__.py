"""JRDB fixed-length file parser."""
from src.parser.engine import build_race_key, parse_file, parse_record
from src.parser.hjc import HJC_FIELDS, RECORD_LENGTH as HJC_RECORD_LENGTH
from src.parser.kyi import KYI_FIELDS, RECORD_LENGTH as KYI_RECORD_LENGTH
from src.parser.sed import SED_FIELDS, RECORD_LENGTH as SED_RECORD_LENGTH
from src.parser.spec import FieldSpec, coerce

__all__ = [
    "FieldSpec",
    "coerce",
    "parse_record",
    "parse_file",
    "build_race_key",
    "KYI_FIELDS",
    "KYI_RECORD_LENGTH",
    "SED_FIELDS",
    "SED_RECORD_LENGTH",
    "HJC_FIELDS",
    "HJC_RECORD_LENGTH",
]
