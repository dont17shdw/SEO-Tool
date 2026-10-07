"""Describe stored evidence quality without changing data or selecting a comparison.
描述已存储证据的数据质量，不修改数据，也不选择对比。
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from itertools import groupby
from typing import Any, Literal
from uuid import UUID

from app.analysis.performance_comparison import ComparisonOutcome, PerformanceObservation
from app.normalization.report_scope import (
    ReportScope,
    canonical_scope_key,
    compare_report_scopes,
    unknown_scope,
)

METRIC_FIELDS = ("clicks", "impressions", "ctr", "average_position")
CODE_ORDER = (
    "insufficient_history",
    "unknown_report_scope",
    "incompatible_report_scope",
    "unknown_reporting_dates",
    "incomplete_date_coverage",
    "unknown_date_coverage",
    "overlapping_comparison_periods",
    "missing_metrics",
    "zero_percentage_baseline",
    "same_period_revisions",
    "out_of_order_import",
    "overlapping_reporting_periods",
)


@dataclass(frozen=True)
class QualityObservation:
    """Expose a stable factual code with its affected records and supporting evidence.
    公开稳定的事实代码及其影响的记录和支持证据。
    """

    code: str
    severity: Literal["info", "warning", "blocking"]
    scope: Literal["page", "import"]
    message: str
    snapshot_ids: list[UUID]
    import_run_ids: list[UUID]
    evidence: dict[str, Any]


@dataclass(frozen=True)
class PageQuality:
    """Summarize selected-comparison readiness separately from historical caveats.
    将所选对比的就绪状态与历史限制分开汇总。
    """

    readiness: Literal["insufficient", "limited", "ready"]
    observations: list[QualityObservation]
    counts: dict[str, int]
    comparison_exists: bool
    selected_snapshot_ids: list[UUID]
    readiness_reasons: list[str]


@dataclass(frozen=True)
class ImportEvidence:
    """Carry only existing import metadata into the database-independent checks.
    仅将已有导入元数据传入不依赖数据库的检查。
    """

    id: UUID
    source: str
    source_type: str
    reporting_window: str
    period_start: date | None
    period_end: date | None
    imported_at: datetime
    file_hash: str
    report_scope: ReportScope | dict[str, Any] | None = None
    coverage_status: Literal["unknown", "partial", "complete"] = "unknown"
    observed_date_count: int | None = None
    dates_consecutive: bool | None = None


@dataclass(frozen=True)
class ImportQuality:
    """Describe a single import in its stored source/type/window context.
    在已存储的来源、类型及窗口上下文中描述单个导入。
    """

    observations: list[QualityObservation]
    counts: dict[str, int]


def _source_key(item: PerformanceObservation | ImportEvidence) -> tuple[str, str, str]:
    return item.source, item.source_type, item.reporting_window


def _period(item: PerformanceObservation | ImportEvidence) -> tuple[date, date] | None:
    if item.period_start is None or item.period_end is None:
        return None
    return item.period_start, item.period_end


def _report_scope(item: PerformanceObservation | ImportEvidence) -> ReportScope:
    return (
        ReportScope.model_validate(item.report_scope)
        if item.report_scope is not None
        else unknown_scope()
    )


def _source_evidence(item: PerformanceObservation | ImportEvidence) -> dict[str, Any]:
    return {
        "source": item.source,
        "source_type": item.source_type,
        "reporting_window": item.reporting_window,
        "period_start": item.period_start.isoformat() if item.period_start else None,
        "period_end": item.period_end.isoformat() if item.period_end else None,
        "imported_at": item.imported_at.isoformat(),
        "report_scope": _report_scope(item).model_dump(mode="json"),
        "coverage_status": item.coverage_status,
        "observed_date_count": item.observed_date_count,
        "dates_consecutive": item.dates_consecutive,
    }


def _snapshot_evidence(
    item: PerformanceObservation, snapshot_import_ids: Mapping[UUID, UUID]
) -> dict[str, Any]:
    import_id = snapshot_import_ids.get(item.id)
    return {
        "snapshot_id": str(item.id),
        "import_run_id": str(import_id) if import_id else None,
        **_source_evidence(item),
    }


def _import_evidence(item: ImportEvidence) -> dict[str, Any]:
    return {"import_run_id": str(item.id), **_source_evidence(item)}


def _page_observation(
    code: str,
    severity: Literal["info", "warning", "blocking"],
    message: str,
    affected: Sequence[PerformanceObservation],
    snapshot_import_ids: Mapping[UUID, UUID],
    evidence: dict[str, Any],
) -> QualityObservation:
    """Attach deterministically ordered record IDs without inventing missing provenance.
    关联确定性排序的记录 ID，不编造缺失的来源信息。
    """
    snapshots = sorted({item.id for item in affected}, key=lambda item: item.int)
    imports = sorted(
        {snapshot_import_ids[item] for item in snapshots if item in snapshot_import_ids},
        key=lambda item: item.int,
    )
    return QualityObservation(code, severity, "page", message, snapshots, imports, evidence)


def _ordered_observations(items: list[QualityObservation]) -> list[QualityObservation]:
    return sorted(items, key=lambda item: CODE_ORDER.index(item.code))


def _out_of_order_snapshots(
    exact: Sequence[PerformanceObservation],
) -> list[tuple[PerformanceObservation, PerformanceObservation]]:
    """Find a strictly earlier imported witness with a later reporting end per offender.
    为每个乱序记录找出严格更早导入且报告结束日期更晚的证据。

    Equal import timestamps provide no chronology, regardless of deterministic ID ordering.
    相同导入时间戳不提供时间先后证据，无论 ID 的确定性排序如何。
    """
    groups: dict[tuple[UUID, str, str, str, str], list[PerformanceObservation]] = defaultdict(list)
    for item in exact:
        groups[(item.page_id, *_source_key(item), canonical_scope_key(item.report_scope))].append(
            item
        )
    cases: list[tuple[PerformanceObservation, PerformanceObservation]] = []
    for key in sorted(groups):
        ordered = sorted(groups[key], key=lambda item: (item.imported_at, item.id.int))
        witness: PerformanceObservation | None = None
        for _, batch_iterator in groupby(ordered, key=lambda item: item.imported_at):
            batch = list(batch_iterator)
            for item in batch:
                if witness is not None and witness.period_end > item.period_end:
                    cases.append((item, witness))
            # Update only after the complete timestamp group has been inspected.
            # 仅在完整检查同一时间戳分组之后更新证据。
            witness = max(
                ([witness] if witness else []) + batch,
                key=lambda item: (item.period_end, item.imported_at, item.id.int),
            )
    return cases


def analyse_page_quality(
    observations: Sequence[PerformanceObservation],
    outcome: ComparisonOutcome,
    snapshot_import_ids: Mapping[UUID, UUID],
) -> PageQuality:
    """Explain full-history caveats while deriving readiness only for the supplied pair.
    解释完整历史的限制，仅针对已提供的对比快照对推导就绪状态。

    The caller supplies the existing comparison outcome and its complete snapshot context.
    调用方提供现有对比结果及其完整快照上下文。
    """
    ordered = sorted(observations, key=lambda item: (item.imported_at, item.id.int))
    exact = [item for item in ordered if _period(item) is not None]
    unknown = [item for item in ordered if _period(item) is None]
    missing = {
        item.id: [field for field in METRIC_FIELDS if getattr(item, field) is None]
        for item in ordered
        if any(getattr(item, field) is None for field in METRIC_FIELDS)
    }
    period_groups: dict[
        tuple[UUID, str, str, str, str, date, date], list[PerformanceObservation]
    ] = defaultdict(list)
    compatible_groups: dict[tuple[UUID, str, str, str, str, int], set[tuple[date, date]]] = (
        defaultdict(set)
    )
    for item in exact:
        start, end = _period(item)
        scope_key = canonical_scope_key(item.report_scope)
        period_groups[(item.page_id, *_source_key(item), scope_key, start, end)].append(item)
        compatible_groups[(item.page_id, *_source_key(item), scope_key, (end - start).days)].add(
            (start, end)
        )
    revisions = [
        items
        for _, items in sorted(period_groups.items())
        if len({snapshot_import_ids[item.id] for item in items if item.id in snapshot_import_ids})
        > 1
    ]
    counts = {
        "total_snapshots": len(ordered),
        "exact_date_snapshots": len(exact),
        "unknown_date_snapshots": len(unknown),
        "snapshots_with_missing_metrics": len(missing),
        "distinct_exact_periods": len(period_groups),
        "revision_periods": len(revisions),
        "compatible_exact_periods": max(map(len, compatible_groups.values()), default=0),
    }
    comparison = outcome.comparison
    by_id = {item.id: item for item in ordered}
    selected_ids = (
        [comparison.previous_snapshot_id, comparison.current_snapshot_id] if comparison else []
    )
    selected = [by_id[item] for item in selected_ids]
    quality: list[QualityObservation] = []
    reasons: list[str] = []
    if comparison is None:
        reasons.append("insufficient_history")
        quality.append(
            _page_observation(
                "insufficient_history",
                "blocking",
                "No compatible comparison is available from the stored history. / "
                "已存储历史中没有可用的兼容对比。",
                ordered,
                snapshot_import_ids,
                {"comparison_unavailable_reason": outcome.unavailable_reason, **counts},
            )
        )
    unknown_scopes = [item for item in ordered if _report_scope(item).status == "unknown"]
    if unknown_scopes:
        quality.append(
            _page_observation(
                "unknown_report_scope",
                "warning",
                f"Report scope is not fully proven for {len(unknown_scopes)} snapshots. / "
                f"{len(unknown_scopes)} 个快照的报告范围未得到完整证明。",
                unknown_scopes,
                snapshot_import_ids,
                {
                    "snapshot_count": len(unknown_scopes),
                    "snapshots": [
                        _snapshot_evidence(item, snapshot_import_ids) for item in unknown_scopes
                    ],
                    "selected_scope_compatibility": (
                        comparison.scope_compatibility if comparison else None
                    ),
                },
            )
        )
    if comparison is not None and comparison.scope_compatibility == "unknown":
        reasons.append("unknown_report_scope")
    if outcome.scope_conflicts:
        affected = [
            by_id[snapshot_id]
            for conflict in outcome.scope_conflicts
            for snapshot_id in (conflict.previous_snapshot_id, conflict.current_snapshot_id)
        ]
        quality.append(
            _page_observation(
                "incompatible_report_scope",
                "warning",
                "Explicitly conflicting report scopes were excluded from comparison selection. / "
                "已明确冲突的报告范围被排除在对比选择之外。",
                affected,
                snapshot_import_ids,
                {
                    "conflicts": [
                        {
                            "previous_snapshot": _snapshot_evidence(
                                by_id[conflict.previous_snapshot_id], snapshot_import_ids
                            ),
                            "current_snapshot": _snapshot_evidence(
                                by_id[conflict.current_snapshot_id], snapshot_import_ids
                            ),
                            "dimensions": list(conflict.dimensions),
                        }
                        for conflict in outcome.scope_conflicts
                    ]
                },
            )
        )
    for status, code, message in (
        (
            "partial",
            "incomplete_date_coverage",
            "Observed dates do not establish complete consecutive 28-day coverage. / "
            "已观察日期未证明完整连续的 28 天覆盖。",
        ),
        (
            "unknown",
            "unknown_date_coverage",
            "Reliable observed reporting-date coverage is unavailable. / "
            "缺少可靠的已观察报告日期覆盖证据。",
        ),
    ):
        affected = [item for item in ordered if item.coverage_status == status]
        if affected:
            quality.append(
                _page_observation(
                    code,
                    "warning",
                    message,
                    affected,
                    snapshot_import_ids,
                    {
                        "snapshot_count": len(affected),
                        "snapshots": [
                            _snapshot_evidence(item, snapshot_import_ids) for item in affected
                        ],
                    },
                )
            )
        if any(item.coverage_status == status for item in selected):
            reasons.append(code)
    if unknown:
        quality.append(
            _page_observation(
                "unknown_reporting_dates",
                "warning",
                f"Exact reporting dates are unavailable for {len(unknown)} snapshots. / "
                f"{len(unknown)} 个快照缺少准确报告日期。",
                unknown,
                snapshot_import_ids,
                {
                    "snapshot_count": len(unknown),
                    "snapshots": [
                        _snapshot_evidence(item, snapshot_import_ids) for item in unknown
                    ],
                },
            )
        )
    if missing:
        affected = [item for item in ordered if item.id in missing]
        quality.append(
            _page_observation(
                "missing_metrics",
                "warning",
                f"Metrics are missing from {len(affected)} snapshots. / "
                f"{len(affected)} 个快照存在缺失指标。",
                affected,
                snapshot_import_ids,
                {
                    "snapshot_count": len(affected),
                    "missing_fields_by_snapshot": {
                        str(item): fields for item, fields in missing.items()
                    },
                },
            )
        )
        if any(item.id in missing for item in selected):
            reasons.append("missing_metrics")
    if comparison is not None:
        if comparison.periods_overlap:
            reasons.append("overlapping_comparison_periods")
            quality.append(
                _page_observation(
                    "overlapping_comparison_periods",
                    "warning",
                    "The selected comparison uses overlapping reporting periods. / "
                    "所选对比使用重叠的报告时间段。",
                    selected,
                    snapshot_import_ids,
                    {
                        "previous_period_start": comparison.previous_period_start.isoformat(),
                        "previous_period_end": comparison.previous_period_end.isoformat(),
                        "current_period_start": comparison.current_period_start.isoformat(),
                        "current_period_end": comparison.current_period_end.isoformat(),
                        "overlap_start": max(
                            comparison.previous_period_start, comparison.current_period_start
                        ).isoformat(),
                        "overlap_end": min(
                            comparison.previous_period_end, comparison.current_period_end
                        ).isoformat(),
                    },
                )
            )
        previous, current = selected
        zero_metrics = {
            field: {"previous": 0, "current": getattr(current, field)}
            for field in ("clicks", "impressions")
            if getattr(previous, field) == 0 and getattr(current, field) is not None
        }
        if zero_metrics:
            reasons.append("zero_percentage_baseline")
            quality.append(
                _page_observation(
                    "zero_percentage_baseline",
                    "warning",
                    "A known zero previous count makes percentage change unavailable. / "
                    "已知的前期零计数使百分比变化无法计算。",
                    selected,
                    snapshot_import_ids,
                    {"metrics": zero_metrics},
                )
            )
    if revisions:
        affected = [item for items in revisions for item in items]
        quality.append(
            _page_observation(
                "same_period_revisions",
                "info",
                f"Multiple imports represent {len(revisions)} exact reporting periods. / "
                f"{len(revisions)} 个准确报告时间段具有多个导入版本。",
                affected,
                snapshot_import_ids,
                {
                    "revision_period_count": len(revisions),
                    "groups": [
                        {
                            **_source_evidence(items[0]),
                            "page_id": str(items[0].page_id),
                            "scope_compatibility": compare_report_scopes(
                                items[0].report_scope, items[-1].report_scope
                            ).status,
                            "snapshot_ids": [str(item.id) for item in items],
                            "import_run_ids": sorted(
                                {
                                    str(snapshot_import_ids[item.id])
                                    for item in items
                                    if item.id in snapshot_import_ids
                                }
                            ),
                        }
                        for items in revisions
                    ],
                },
            )
        )
    chronology = _out_of_order_snapshots(exact)
    if chronology:
        affected = [item for pair in chronology for item in pair]
        quality.append(
            _page_observation(
                "out_of_order_import",
                "warning",
                f"Older reporting periods were imported after newer evidence in {len(chronology)} "
                f"snapshots. / {len(chronology)} 个快照在较新报告证据之后导入了较早报告时间段。",
                affected,
                snapshot_import_ids,
                {
                    "affected_snapshot_count": len(chronology),
                    "cases": [
                        {
                            "older_period_snapshot": _snapshot_evidence(item, snapshot_import_ids),
                            "earlier_imported_newer_period": _snapshot_evidence(
                                witness, snapshot_import_ids
                            ),
                            "scope_compatibility": compare_report_scopes(
                                item.report_scope, witness.report_scope
                            ).status,
                        }
                        for item, witness in chronology
                    ],
                },
            )
        )
        if any(item.id in selected_ids for item, _ in chronology):
            reasons.append("out_of_order_import")
    readiness = "insufficient" if comparison is None else "limited" if reasons else "ready"
    return PageQuality(
        readiness=readiness,
        observations=_ordered_observations(quality),
        counts=counts,
        comparison_exists=comparison is not None,
        selected_snapshot_ids=selected_ids,
        readiness_reasons=sorted(reasons, key=CODE_ORDER.index),
    )


def analyse_import_quality(
    target: ImportEvidence, context: Sequence[ImportEvidence]
) -> ImportQuality:
    """Describe one run against same-source/type/window history without judging its metrics.
    将一个导入与同来源、类型及窗口的历史比较，不判断其指标。
    """
    by_id = {item.id: item for item in context if _source_key(item) == _source_key(target)}
    by_id[target.id] = target
    runs = sorted(by_id.values(), key=lambda item: (item.imported_at, item.id.int))
    exact = [item for item in runs if _period(item) is not None]
    target_period = _period(target)
    other = [
        item
        for item in exact
        if item.id != target.id
        and item.file_hash != target.file_hash
        and canonical_scope_key(item.report_scope) == canonical_scope_key(target.report_scope)
    ]
    revisions = [
        item for item in other if target_period is not None and _period(item) == target_period
    ]
    overlapping = [
        item
        for item in other
        if target_period is not None
        and _period(item) != target_period
        and max(target.period_start, item.period_start) <= min(target.period_end, item.period_end)
    ]
    chronology = [
        item
        for item in other
        if target_period is not None
        and item.imported_at < target.imported_at
        and item.period_end > target.period_end
    ]
    counts = {
        "total_imports": len(runs),
        "exact_date_imports": len(exact),
        "unknown_date_imports": len(runs) - len(exact),
        "same_period_revision_imports": len(revisions),
        "overlapping_imports": len(overlapping),
        "earlier_imported_newer_periods": len(chronology),
    }
    quality: list[QualityObservation] = []

    def add(
        code: str,
        severity: Literal["info", "warning"],
        message: str,
        affected: Sequence[ImportEvidence],
        evidence: dict[str, Any],
    ) -> None:
        quality.append(
            QualityObservation(
                code,
                severity,
                "import",
                message,
                [],
                sorted({item.id for item in affected}, key=lambda item: item.int),
                {"target": _import_evidence(target), **evidence},
            )
        )

    if _report_scope(target).status == "unknown":
        add(
            "unknown_report_scope",
            "warning",
            "This import's property, search type, or complete filter scope is unknown. / "
            "此导入的属性、搜索类型或完整筛选范围未知。",
            [target],
            {"import_count": 1},
        )
    incompatible = [
        (item, compare_report_scopes(target.report_scope, item.report_scope))
        for item in runs
        if item.id != target.id
        and compare_report_scopes(target.report_scope, item.report_scope).status == "incompatible"
    ]
    if incompatible:
        add(
            "incompatible_report_scope",
            "warning",
            "Other stored reports have explicitly conflicting scope dimensions. / "
            "其他已存储报告具有明确冲突的范围维度。",
            [target, *(item for item, _ in incompatible)],
            {
                "conflicts": [
                    {
                        "import": _import_evidence(item),
                        "dimensions": list(compatibility.conflicts),
                    }
                    for item, compatibility in incompatible
                ]
            },
        )
    if target.coverage_status != "complete":
        add(
            (
                "incomplete_date_coverage"
                if target.coverage_status == "partial"
                else "unknown_date_coverage"
            ),
            "warning",
            (
                "Observed dates do not establish complete consecutive 28-day coverage. / "
                "已观察日期未证明完整连续的 28 天覆盖。"
                if target.coverage_status == "partial"
                else "Reliable observed reporting-date coverage is unavailable. / "
                "缺少可靠的已观察报告日期覆盖证据。"
            ),
            [target],
            {"import_count": 1},
        )
    if target_period is None:
        add(
            "unknown_reporting_dates",
            "warning",
            "Exact reporting dates are unavailable for this import. / 此导入缺少准确报告日期。",
            [target],
            {"import_count": 1},
        )
    if revisions:
        add(
            "same_period_revisions",
            "info",
            f"{len(revisions)} other files share the same exact reporting date bounds. / "
            f"另外 {len(revisions)} 个文件具有相同的准确报告日期范围。",
            [target, *revisions],
            {
                "revision_import_count": len(revisions),
                "revisions": [_import_evidence(item) for item in revisions],
            },
        )
    if overlapping:
        add(
            "overlapping_reporting_periods",
            "warning",
            f"This reporting period overlaps {len(overlapping)} other imported periods. / "
            f"此报告时间段与另外 {len(overlapping)} 个已导入时间段重叠。",
            [target, *overlapping],
            {
                "overlapping_import_count": len(overlapping),
                "overlapping_imports": [_import_evidence(item) for item in overlapping],
            },
        )
    if chronology:
        add(
            "out_of_order_import",
            "warning",
            "This older reporting period was imported after newer reporting evidence. / "
            "此较早报告时间段在较新报告证据之后被导入。",
            [target, *chronology],
            {
                "earlier_imported_newer_period_count": len(chronology),
                "earlier_imported_newer_periods": [_import_evidence(item) for item in chronology],
            },
        )
    return ImportQuality(_ordered_observations(quality), counts)
