"""Text limits for fixed-width fields in verified local form layouts."""
from typing import Annotated
from unicodedata import category, east_asian_width

from pydantic import AfterValidator, Field


def display_width(value, extra_wide=""):
    return sum(2 if char in extra_wide or east_asian_width(char) in {"W", "F"} else 1 for char in value)


def fixed_line(width, extra_wide=""):
    def check(value):
        if any(category(char).startswith("C") or category(char) in {"Zl", "Zp"} for char in value):
            raise ValueError("原表每栏只容纳一行文字")
        value = value.strip()
        if display_width(value, extra_wide) > width:
            raise ValueError("文字超出原表栏位的填写容量")
        return value
    return Annotated[str, Field(max_length=width), AfterValidator(check)]
