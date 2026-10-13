"""
Internationalisation — thin wrapper around translations/ JSON files.
"""

from .translations import (
    load,
    current_code,
    u as t,
    prayer_name as t_prayer,
    get_athkar,
    credits_html,
    credits_title,
    format_date,
    country_name,
    city_name,
)
from ._constants import LANGS

__all__ = [
    "load",
    "current_code",
    "t",
    "t_prayer",
    "get_athkar",
    "credits_html",
    "credits_title",
    "format_date",
    "country_name",
    "city_name",
    "LANGS",
    "set_lang",
    "get_lang",
]


def set_lang(code: str):
    load(code if code in LANGS else "ar")


def get_lang() -> str:
    return current_code()
