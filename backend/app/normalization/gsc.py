"""Validate and normalize observed GSC values without inventing unknown metrics.
校验并标准化观测到的 GSC 值，不编造未知指标。
"""

import ipaddress
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit

# Keep JSON counts exact in the browser; PostgreSQL BIGINT can store a wider range.
# 保证浏览器中的 JSON 计数精确；PostgreSQL BIGINT 可以存储更大范围。
MAX_COUNT = 2**53 - 1
MAX_POSITION = Decimal("999999.9999")


class InvalidGSCValue(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def normalize_url(value: Any) -> str:
    """Trim surrounding whitespace and validate an absolute URL without canonicalization.
    去除首尾空白并校验绝对 URL，不进行规范化改写。
    """
    if is_blank(value):
        raise InvalidGSCValue("missing_url", "A page URL is required.")
    if not isinstance(value, str):
        raise InvalidGSCValue("invalid_url", "Page URL must be text.")
    url = value.strip()
    message = "Page URL must be an absolute http:// or https:// URL with a valid host."
    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127 for character in url
    ):
        raise InvalidGSCValue("invalid_url", message)
    if "\\" in url:
        raise InvalidGSCValue("invalid_url", message)
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or not host:
            raise ValueError
        # Accessing the port validates malformed and out-of-range port syntax.
        # 读取端口会校验格式错误及超出范围的端口语法。
        _ = parsed.port
        if ":" in host:
            ipaddress.IPv6Address(host)
        else:
            ascii_host = host.rstrip(".").encode("idna").decode("ascii")
            if not ascii_host or len(ascii_host) > 253:
                raise ValueError
            if not all(
                re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                for label in ascii_host.split(".")
            ):
                raise ValueError
            if re.fullmatch(r"[\d.]+", ascii_host) and "." in ascii_host:
                ipaddress.IPv4Address(ascii_host)
    except (ValueError, UnicodeError) as exc:
        raise InvalidGSCValue("invalid_url", message) from exc
    return url


def _decimal(value: Any, code: str, message: str) -> Decimal:
    """Parse finite decimal inputs and translate invalid values into row-level errors.
    解析有限小数输入，并将无效值转换为行级错误。
    """
    if isinstance(value, bool):
        raise InvalidGSCValue(code, message)
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise InvalidGSCValue(code, message) from exc
    if not number.is_finite():
        raise InvalidGSCValue(code, message)
    return number


def normalize_count(value: Any, field: str) -> int | None:
    """Retain unknown counts as NULL and bound integers for exact JSON/browser transport.
    将未知计数保留为 NULL，并限制整数范围，保证 JSON 和浏览器传输精确。
    """
    if is_blank(value):
        return None
    message = f"{field.capitalize()} must be a non-negative whole number up to {MAX_COUNT}."
    if isinstance(value, str) and re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.0+)?", value.strip()):
        value = value.strip().replace(",", "")
    number = _decimal(value, f"invalid_{field}", message)
    if number < 0 or number > MAX_COUNT or number != number.to_integral_value():
        raise InvalidGSCValue(f"invalid_{field}", message)
    return int(number)


def normalize_ctr(value: Any) -> Decimal | None:
    """Convert percent or fractional CTR to the existing six-decimal 0–1 database field.
    将百分数或小数点击率转换为现有数据库字段的六位小数 0–1 比例。
    """
    if is_blank(value):
        return None
    message = "CTR must be a fraction between 0 and 1, or a percentage between 0% and 100%."
    percent = isinstance(value, str) and value.strip().endswith("%")
    number = _decimal(value.strip()[:-1] if percent else value, "invalid_ctr", message)
    if percent:
        if not 0 <= number <= 100:
            raise InvalidGSCValue("invalid_ctr", message)
        number /= 100
    # Validate before rounding so out-of-range source values cannot become valid.
    # 在舍入前校验，防止超范围的源值通过舍入变成合法值。
    if not 0 <= number <= 1:
        raise InvalidGSCValue("invalid_ctr", message)
    return number.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def normalize_position(value: Any) -> Decimal | None:
    """Quantize non-negative position to NUMERIC(10,4) without overflowing its range.
    将非负排名舍入为 NUMERIC(10,4)，同时避免超出字段范围。
    """
    if is_blank(value):
        return None
    message = f"Position must be a non-negative number no larger than {MAX_POSITION}."
    number = _decimal(value, "invalid_position", message)
    if number < 0 or number > MAX_POSITION:
        raise InvalidGSCValue("invalid_position", message)
    return number.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
