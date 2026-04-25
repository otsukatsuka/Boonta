"""JRDB fixed-length file parser."""
from src.parser.bac import BAC_FIELDS
from src.parser.bac import RECORD_LENGTH as BAC_RECORD_LENGTH
from src.parser.engine import build_race_key, parse_file, parse_record
from src.parser.hjc import HJC_FIELDS
from src.parser.hjc import RECORD_LENGTH as HJC_RECORD_LENGTH
from src.parser.kyi import KYI_FIELDS
from src.parser.kyi import RECORD_LENGTH as KYI_RECORD_LENGTH
from src.parser.sed import RECORD_LENGTH as SED_RECORD_LENGTH
from src.parser.sed import SED_FIELDS
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
    "BAC_FIELDS",
    "BAC_RECORD_LENGTH",
]
