"""Canonicalize explicit report evidence without inferring absent scope dimensions.
规范化明确报告证据，不推断缺失的范围维度。
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.normalization.gsc import normalize_url

SearchType = Literal["web", "image", "video", "news"]
ScopeDimension = Literal["country", "device", "search_appearance", "query", "page"]
ScopeOperator = Literal["equals", "not_equals", "contains", "not_contains", "regex", "not_regex"]
CompatibilityStatus = Literal["compatible", "incompatible", "unknown"]

SEARCH_TYPES = {
    "web": "web",
    "网络": "web",
    "网页": "web",
    "image": "image",
    "images": "image",
    "图片": "image",
    "图像": "image",
    "video": "video",
    "videos": "video",
    "视频": "video",
    "news": "news",
    "新闻": "news",
}
DEVICES = {
    "mobile": "mobile",
    "移动设备": "mobile",
    "移动": "mobile",
    "手机": "mobile",
    "desktop": "desktop",
    "桌面": "desktop",
    "桌面设备": "desktop",
    "电脑": "desktop",
    "tablet": "tablet",
    "平板电脑": "tablet",
    "平板": "tablet",
}
# ISO codes are identities; localized country names are deliberately not guessed.
# ISO 代码是标识符；刻意不猜测本地化的国家名称。
COUNTRY_CODES = frozenset(
    "AFG ALA ALB DZA ASM AND AGO AIA ATA ATG ARG ARM ABW AUS AUT AZE BHS BHR BGD BRB BLR BEL "
    "BLZ BEN BMU BTN BOL BES BIH BWA BVT BRA IOT BRN BGR BFA BDI CPV KHM CMR CAN CYM CAF TCD "
    "CHL CHN CXR CCK COL COM COG COD COK CRI CIV HRV CUB CUW CYP CZE DNK DJI DMA DOM ECU EGY "
    "SLV GNQ ERI EST SWZ ETH FLK FRO FJI FIN FRA GUF PYF ATF GAB GMB GEO DEU GHA GIB GRC GRL "
    "GRD GLP GUM GTM GGY GIN GNB GUY HTI HMD VAT HND HKG HUN ISL IND IDN IRN IRQ IRL IMN ISR "
    "ITA JAM JPN JEY JOR KAZ KEN KIR PRK KOR KWT KGZ LAO LVA LBN LSO LBR LBY LIE LTU LUX MAC "
    "MDG MWI MYS MDV MLI MLT MHL MTQ MRT MUS MYT MEX FSM MDA MCO MNG MNE MSR MAR MOZ MMR NAM "
    "NRU NPL NLD NCL NZL NIC NER NGA NIU NFK MKD MNP NOR OMN PAK PLW PSE PAN PNG PRY PER PHL "
    "PCN POL PRT PRI QAT REU ROU RUS RWA BLM SHN KNA LCA MAF SPM VCT WSM SMR STP SAU SEN SRB "
    "SYC SLE SGP SXM SVK SVN SLB SOM ZAF SGS SSD ESP LKA SDN SUR SJM SWE CHE SYR TWN TJK TZA "
    "THA TLS TGO TKL TON TTO TUN TUR TKM TCA TUV UGA UKR ARE GBR USA UMI URY UZB VUT VEN VNM "
    "VGB VIR WLF ESH YEM ZMB ZWE".split()
)


def normalize_property_id(value: str) -> str:
    """Normalize GSC property syntax while retaining significant URL-prefix paths.
    规范化 GSC 属性语法，同时保留有意义的 URL 前缀路径。

    Domain properties and URL-prefix properties remain distinct identities.
    网域属性与 URL 前缀属性保持不同的标识。
    """
    text = value.strip()
    if text.casefold().startswith("sc-domain:"):
        domain = text[len("sc-domain:") :]
        if any(character in domain for character in "/:?#@\\"):
            raise ValueError("Use sc-domain: followed by a domain, without a URL path or port.")
        parsed = urlsplit(normalize_url(f"https://{domain}/"))
        return f"sc-domain:{parsed.hostname.rstrip('.').encode('idna').decode('ascii').lower()}"
    parsed = urlsplit(normalize_url(text))
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(
            "A URL-prefix property cannot contain credentials, a query, or a fragment."
        )
    host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port
    if port is not None and (parsed.scheme, port) not in {("http", 80), ("https", 443)}:
        host = f"{host}:{port}"
    return urlunsplit((parsed.scheme.lower(), host, parsed.path or "/", "", ""))


class ScopeFilter(BaseModel):
    """Represent one supported filter predicate with explicit operator semantics.
    以明确的运算符语义表示一个受支持的筛选谓词。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: ScopeDimension
    operator: ScopeOperator
    value: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def normalize_value(self) -> "ScopeFilter":
        """Normalize enumerated identities, preserving significant text and regex contents.
        规范化枚举标识，同时保留有意义的文本及正则表达式内容。
        """
        value = self.value if self.operator in {"regex", "not_regex"} else self.value.strip()
        if not value.strip() or any(ord(character) < 32 for character in value):
            raise ValueError("Filter values must be nonblank text without control characters.")
        if self.dimension not in {"query", "page"}:
            if self.operator not in {"equals", "not_equals"}:
                raise ValueError("Enumerated filters support only equals or not_equals.")
            if self.dimension == "country":
                value = value.upper()
                if value not in COUNTRY_CODES:
                    raise ValueError("Country must be an ISO 3166-1 alpha-3 code, such as USA.")
            elif self.dimension == "device":
                value = DEVICES.get(value.casefold(), "")
                if not value:
                    raise ValueError("Device must be mobile, desktop, or tablet.")
            else:
                value = value.lower()
                if not re.fullmatch(r"[a-z][a-z0-9_]{0,99}", value):
                    raise ValueError("Search appearance must use a canonical machine identifier.")
        object.__setattr__(self, "value", value)
        return self


def _ordered_filters(filters: list[ScopeFilter]) -> list[ScopeFilter]:
    """Order unique predicates and reject multiple conditions for the same dimension.
    对唯一谓词排序，并拒绝同一维度的多个条件。
    """
    by_dimension: dict[str, ScopeFilter] = {}
    for item in filters:
        previous = by_dimension.get(item.dimension)
        if previous is not None and previous != item:
            raise ValueError("Only one distinct condition per filter dimension is supported.")
        by_dimension[item.dimension] = item
    return [by_dimension[key] for key in sorted(by_dimension)]


class ScopeDeclaration(BaseModel):
    """Keep a declaration's absent filter ledger distinct from an explicit empty ledger.
    将声明中缺失的筛选清单与明确为空的清单区分。
    """

    model_config = ConfigDict(extra="forbid")

    property_id: str | None = Field(default=None, max_length=2000)
    search_type: SearchType | None = None
    filters: list[ScopeFilter] | None = Field(default=None, max_length=5)

    @field_validator("property_id")
    @classmethod
    def normalize_property(cls, value: str | None) -> str | None:
        return normalize_property_id(value) if value is not None else None

    @field_validator("search_type", mode="before")
    @classmethod
    def normalize_search_type(cls, value: Any) -> Any:
        return (
            SEARCH_TYPES.get(value.strip().casefold(), value) if isinstance(value, str) else value
        )

    @field_validator("filters")
    @classmethod
    def canonicalize_filters(cls, value: list[ScopeFilter] | None) -> list[ScopeFilter] | None:
        return _ordered_filters(value) if value is not None else None


class ReportScope(BaseModel):
    """Separate resolved semantic identity from workbook and user evidence origins.
    将解析后的语义标识与工作簿及用户证据来源分开。

    Workbook filter rows are partial evidence, even when no filter rows exist.
    工作簿筛选行属于部分证据，即使没有筛选行也是如此。
    """

    model_config = ConfigDict(extra="forbid")

    property_id: str | None = None
    search_type: SearchType | None = None
    filters: list[ScopeFilter] = Field(default_factory=list)
    filters_complete: bool = False
    workbook_observed: ScopeDeclaration = Field(default_factory=ScopeDeclaration)
    user_declared: ScopeDeclaration = Field(default_factory=ScopeDeclaration)
    issues: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def discard_derived_fields(cls, value: Any) -> Any:
        """Recompute derived API fields when loading stored JSON rather than trusting them.
        读取存储 JSON 时重新计算派生 API 字段，不信任其存储值。
        """
        if isinstance(value, dict):
            return {
                key: item
                for key, item in value.items()
                if key not in {"status", "property_status", "fingerprint", "site_identifier"}
            }
        return value

    @field_validator("property_id")
    @classmethod
    def normalize_property(cls, value: str | None) -> str | None:
        return normalize_property_id(value) if value is not None else None

    @field_validator("filters")
    @classmethod
    def canonicalize_filters(cls, value: list[ScopeFilter]) -> list[ScopeFilter]:
        return _ordered_filters(value)

    @computed_field
    @property
    def status(self) -> Literal["known", "unknown"]:
        return (
            "known"
            if self.property_id and self.search_type and self.filters_complete
            else "unknown"
        )

    @computed_field
    @property
    def property_status(self) -> Literal["known", "unknown"]:
        return "known" if self.property_id is not None else "unknown"

    @computed_field
    @property
    def site_identifier(self) -> str | None:
        return self.property_id

    @computed_field
    @property
    def fingerprint(self) -> str:
        return canonical_scope_key(self)


def unknown_scope() -> ReportScope:
    return ReportScope()


def _as_scope(scope: ReportScope | dict | None) -> ReportScope:
    return scope if isinstance(scope, ReportScope) else ReportScope.model_validate(scope or {})


def canonical_scope_key(scope: ReportScope | dict | None) -> str:
    """Hash normalized semantic dimensions, excluding dates and evidence presentation.
    对标准化语义维度计算哈希，不包括日期与证据展示信息。
    """
    value = _as_scope(scope)
    identity = {
        "version": 1,
        "property_id": value.property_id,
        "search_type": value.search_type,
        "filters": [item.model_dump(mode="json") for item in _ordered_filters(value.filters)],
        "filters_complete": value.filters_complete,
    }
    serialized = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


UNKNOWN_SCOPE_FINGERPRINT = "a965b425ddf7be68f5b0aa31a332bd7a004d70e2908b09dfcbcf6883a265b877"


@dataclass(frozen=True)
class ReportScopeCompatibility:
    status: CompatibilityStatus
    conflicts: tuple[str, ...] = ()


def compare_report_scopes(
    left: ReportScope | dict | None, right: ReportScope | dict | None
) -> ReportScopeCompatibility:
    """Prove conflicts from explicit facts and require complete matching evidence for compatibility.
    根据明确事实证明冲突，并要求完整匹配证据才能认定兼容。

    Missing dimensions do not match by assumption; partial filter absence is never empty scope.
    不假定缺失维度匹配；部分筛选证据中的缺失绝不表示空范围。
    """
    first, second = _as_scope(left), _as_scope(right)
    conflicts: list[str] = []
    for dimension in ("property_id", "search_type"):
        left_value, right_value = getattr(first, dimension), getattr(second, dimension)
        if left_value is not None and right_value is not None and left_value != right_value:
            conflicts.append(dimension)
    left_filters = {item.dimension: item for item in first.filters}
    right_filters = {item.dimension: item for item in second.filters}
    for dimension in sorted(left_filters.keys() | right_filters.keys()):
        left_value, right_value = left_filters.get(dimension), right_filters.get(dimension)
        if left_value is not None and right_value is not None:
            conflict = left_value != right_value
        else:
            conflict = (left_value is None and first.filters_complete) or (
                right_value is None and second.filters_complete
            )
        if conflict:
            conflicts.append(f"filters.{dimension}")
    if conflicts:
        return ReportScopeCompatibility("incompatible", tuple(conflicts))
    if first.status == "known" and second.status == "known":
        return ReportScopeCompatibility("compatible")
    return ReportScopeCompatibility("unknown")
