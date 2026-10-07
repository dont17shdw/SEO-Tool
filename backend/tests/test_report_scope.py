"""Verify explicit canonical scope evidence and compatibility with synthetic identities.
使用合成标识验证明确的规范范围证据与兼容性。
"""

import pytest
from pydantic import ValidationError

from app.imports.gsc.scope import ScopeEvidenceError, resolve_scope
from app.normalization.report_scope import (
    UNKNOWN_SCOPE_FINGERPRINT,
    ReportScope,
    ScopeDeclaration,
    ScopeFilter,
    canonical_scope_key,
    compare_report_scopes,
    normalize_property_id,
    unknown_scope,
)


def declared_scope(**changes) -> ReportScope:
    values = {"property_id": "sc-domain:example.test", "search_type": "web", "filters": []}
    values.update(changes)
    return resolve_scope(ScopeDeclaration(**values))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" SC-DOMAIN:EXAMPLE.TEST. ", "sc-domain:example.test"),
        ("https://EXAMPLE.TEST", "https://example.test/"),
        ("HTTPS://example.test:443/Path/", "https://example.test/Path/"),
        ("http://example.test:80/", "http://example.test/"),
        ("https://example.test:8443/Path", "https://example.test:8443/Path"),
        ("https://例子.test/路径", "https://xn--fsqu00a.test/路径"),
    ],
)
def test_property_normalization_retains_prefix_semantics(value, expected):
    assert normalize_property_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "example.test",
        "sc-domain:",
        "sc-domain:example.test/path",
        "sc-domain:example.test:443",
        "https://name:password@example.test/",
        "https://example.test/?query=1",
        "https://example.test/#fragment",
        "https://example.test\\path",
        "ftp://example.test/",
        "https://exa mple.test/",
    ],
)
def test_ambiguous_or_invalid_property_is_rejected(value):
    with pytest.raises(ValueError):
        normalize_property_id(value)


def test_domain_and_url_prefix_properties_remain_different():
    domain = declared_scope()
    prefix = declared_scope(property_id="https://example.test/")
    assert compare_report_scopes(domain, prefix).status == "incompatible"
    assert domain.fingerprint != prefix.fingerprint
    assert declared_scope(property_id="https://example.test/Path/").fingerprint != (
        declared_scope(property_id="https://example.test/path/").fingerprint
    )


def test_unknown_filters_are_distinct_from_an_explicit_complete_empty_ledger():
    unknown = declared_scope(filters=None)
    empty = declared_scope(filters=[])
    assert unknown.status == "unknown"
    assert empty.status == "known"
    assert unknown.fingerprint != empty.fingerprint
    assert compare_report_scopes(unknown, empty).status == "unknown"


def test_canonical_filter_order_aliases_and_duplicate_predicates_do_not_change_identity():
    first = declared_scope(
        filters=[
            {"dimension": "device", "operator": "equals", "value": " Mobile "},
            {"dimension": "country", "operator": "equals", "value": "usa"},
        ]
    )
    second = declared_scope(
        filters=[
            {"dimension": "country", "operator": "equals", "value": "USA"},
            {"dimension": "device", "operator": "equals", "value": "移动设备"},
            {"dimension": "country", "operator": "equals", "value": "usa"},
        ]
    )
    assert first.fingerprint == second.fingerprint
    assert compare_report_scopes(first, second).status == "compatible"
    assert [item.dimension for item in first.filters] == ["country", "device"]


def test_text_and_regex_values_keep_significant_case_spacing_and_syntax():
    query = ScopeFilter(dimension="query", operator="contains", value="  Brass  Lamp  ")
    assert query.value == "Brass  Lamp"
    regex = ScopeFilter(dimension="query", operator="regex", value=" ^Lamp[ ]+$ ")
    assert regex.value == " ^Lamp[ ]+$ "
    first = declared_scope(filters=[query])
    assert (
        first.fingerprint
        != declared_scope(
            filters=[{"dimension": "query", "operator": "contains", "value": "brass  Lamp"}]
        ).fingerprint
    )
    assert (
        first.fingerprint
        != declared_scope(
            filters=[{"dimension": "query", "operator": "contains", "value": "Brass Lamp"}]
        ).fingerprint
    )


@pytest.mark.parametrize(
    "condition",
    [
        {"dimension": "country", "operator": "equals", "value": "US"},
        {"dimension": "country", "operator": "equals", "value": "ZZZ"},
        {"dimension": "device", "operator": "equals", "value": "watch"},
        {"dimension": "device", "operator": "contains", "value": "mobile"},
        {"dimension": "search_appearance", "operator": "equals", "value": "Product snippets"},
        {"dimension": "query", "operator": "equals", "value": " "},
        {"dimension": "query", "operator": "equals", "value": "one\ntwo"},
        {"dimension": "date", "operator": "equals", "value": "2026-01-01"},
        {"dimension": "query", "operator": "approximately", "value": "lamp"},
    ],
)
def test_unsupported_filter_identity_is_not_guessed(condition):
    with pytest.raises(ValidationError):
        ScopeFilter(**condition)


def test_multiple_conditions_on_the_same_dimension_are_rejected():
    with pytest.raises(ValidationError):
        ScopeDeclaration(
            filters=[
                {"dimension": "device", "operator": "equals", "value": "mobile"},
                {"dimension": "device", "operator": "equals", "value": "desktop"},
            ]
        )


@pytest.mark.parametrize("dimension", ["country", "device", "search_appearance", "query", "page"])
def test_declaration_requires_the_filter_operator_instead_of_inventing_equals(dimension):
    with pytest.raises(ValidationError) as caught:
        ScopeDeclaration.model_validate(
            {
                "property_id": "sc-domain:example.test",
                "search_type": "web",
                "filters": [{"dimension": dimension, "value": "present"}],
            }
        )
    assert caught.value.errors()[0]["loc"] == ("filters", 0, "operator")


@pytest.mark.parametrize("field", ["site", "period_start", "filename", "fingerprint"])
def test_declaration_does_not_accept_unsupported_identity_fields(field):
    with pytest.raises(ValidationError):
        ScopeDeclaration(**{field: "invented"})


def test_canonical_unknown_identity_is_frozen_and_round_trips_api_fields():
    unknown = unknown_scope()
    assert unknown.fingerprint == UNKNOWN_SCOPE_FINGERPRINT
    assert canonical_scope_key(None) == UNKNOWN_SCOPE_FINGERPRINT
    assert canonical_scope_key({}) == UNKNOWN_SCOPE_FINGERPRINT
    assert ReportScope.model_validate(unknown.model_dump(mode="json")) == unknown
    scoped = declared_scope()
    assert ReportScope.model_validate(scoped.model_dump(mode="json")) == scoped


@pytest.mark.parametrize(
    ("changes", "conflict"),
    [
        ({"property_id": "sc-domain:other.test"}, "property_id"),
        ({"search_type": "image"}, "search_type"),
        (
            {"filters": [{"dimension": "device", "operator": "equals", "value": "mobile"}]},
            "filters.device",
        ),
        (
            {"filters": [{"dimension": "country", "operator": "equals", "value": "USA"}]},
            "filters.country",
        ),
        (
            {"filters": [{"dimension": "query", "operator": "equals", "value": "lamp"}]},
            "filters.query",
        ),
    ],
)
def test_explicit_scope_conflicts_are_incompatible(changes, conflict):
    result = compare_report_scopes(declared_scope(), declared_scope(**changes))
    assert result.status == "incompatible"
    assert conflict in result.conflicts


def test_partial_explicit_conflict_is_incompatible_without_complete_identity():
    first = ReportScope(search_type="web")
    second = ReportScope(search_type="image")
    assert compare_report_scopes(first, second).status == "incompatible"
    first = ReportScope(
        filters=[ScopeFilter(dimension="device", operator="equals", value="mobile")]
    )
    second = ReportScope(
        filters=[ScopeFilter(dimension="device", operator="equals", value="desktop")]
    )
    assert compare_report_scopes(first, second).status == "incompatible"


def test_partial_absence_is_unknown_but_complete_absence_proves_filter_conflict():
    partial_mobile = ReportScope(
        filters=[ScopeFilter(dimension="device", operator="equals", value="mobile")]
    )
    assert compare_report_scopes(partial_mobile, unknown_scope()).status == "unknown"
    assert compare_report_scopes(partial_mobile, declared_scope()).status == "incompatible"
    assert compare_report_scopes(declared_scope(), partial_mobile).status == "incompatible"


def test_matching_partial_known_values_are_still_unknown():
    first = ReportScope(property_id="sc-domain:example.test", search_type="web")
    assert compare_report_scopes(first, first).status == "unknown"
    assert compare_report_scopes(None, None).status == "unknown"


def test_resolution_keeps_evidence_origin_and_excludes_origins_from_scope_identity():
    declared = ScopeDeclaration(property_id="sc-domain:example.test", filters=[])
    observed = ScopeDeclaration(search_type="网络")
    first = resolve_scope(declared, observed)
    second = declared_scope()
    assert first.status == "known"
    assert first.user_declared.property_id == first.property_id
    assert first.user_declared.search_type is None
    assert first.workbook_observed.search_type == "web"
    assert first.fingerprint == second.fingerprint


def test_unsupported_workbook_metadata_prevents_a_complete_scope_claim():
    result = resolve_scope(
        ScopeDeclaration(property_id="sc-domain:example.test", search_type="web", filters=[]),
        issues=["unsupported_filter_metadata"],
    )
    assert result.status == "unknown"
    assert not result.filters_complete
    assert result.user_declared.filters == []
    assert result.issues == ["unsupported_filter_metadata"]


def test_user_complete_ledger_must_account_for_every_observed_filter():
    observed = ScopeDeclaration(
        filters=[ScopeFilter(dimension="device", operator="equals", value="mobile")]
    )
    with pytest.raises(ScopeEvidenceError) as caught:
        resolve_scope(ScopeDeclaration(filters=[]), observed)
    assert caught.value.code == "scope_declaration_conflict"
    matching = ScopeDeclaration(
        filters=[ScopeFilter(dimension="device", operator="equals", value="mobile")]
    )
    assert resolve_scope(matching, observed).filters_complete
