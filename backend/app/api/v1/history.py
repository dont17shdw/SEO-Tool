from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.analysis.data_quality import ImportEvidence, analyse_import_quality, analyse_page_quality
from app.analysis.performance_comparison import (
    ComparisonOutcome,
    PerformanceObservation,
    compare_performance,
)
from app.api.v1.schemas import (
    ImportQualityResponse,
    ImportRunList,
    ImportRunResponse,
    PagePerformanceHistory,
    PageQualityCounts,
    PageQualityResponse,
    PerformanceComparisonResponse,
    PerformanceSnapshotResponse,
    QualityObservationResponse,
    WebsitePageResponse,
)
from app.db.session import get_session
from app.models import ImportRun, PagePerformanceSnapshot, WebsitePage

router = APIRouter(tags=["performance history"])


@dataclass(frozen=True)
class LoadedPageHistory:
    page: WebsitePage
    records: list[tuple[PagePerformanceSnapshot, ImportRun]]
    comparison: ComparisonOutcome
    quality: PageQualityResponse


def _database_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "database_unavailable",
            "message": "History is unavailable. Try again. / 历史记录暂时不可用，请重试。",
        },
    )


def _load_page_history(session: Session, page_id: UUID) -> LoadedPageHistory:
    """Load page evidence once and reuse one comparison for history and quality.
    一次读取页面证据，为历史与质量复用一次比较结果。
    """
    try:
        website_page = session.get(WebsitePage, page_id)
        if website_page is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "page_not_found", "message": "Page not found. / 未找到页面。"},
            )
        statement = (
            select(PagePerformanceSnapshot, ImportRun)
            .join(ImportRun, ImportRun.id == PagePerformanceSnapshot.import_run_id)
            .where(PagePerformanceSnapshot.page_id == page_id)
            .order_by(ImportRun.imported_at, PagePerformanceSnapshot.id)
        )
        records = [(snapshot, run) for snapshot, run in session.execute(statement)]
    except SQLAlchemyError:
        raise _database_unavailable() from None
    observations = [
        PerformanceObservation(
            id=snapshot.id,
            page_id=snapshot.page_id,
            source=run.source,
            source_type=run.source_type,
            reporting_window=run.reporting_window,
            period_start=snapshot.period_start,
            period_end=snapshot.period_end,
            imported_at=run.imported_at,
            clicks=snapshot.clicks,
            impressions=snapshot.impressions,
            ctr=snapshot.ctr,
            average_position=snapshot.average_position,
        )
        for snapshot, run in records
    ]
    outcome = compare_performance(observations)
    analysed = analyse_page_quality(
        observations, outcome, {snapshot.id: run.id for snapshot, run in records}
    )
    quality = PageQualityResponse(
        page_id=page_id,
        readiness=analysed.readiness,
        observations=[
            QualityObservationResponse.model_validate(item) for item in analysed.observations
        ],
        counts=PageQualityCounts.model_validate(analysed.counts),
        comparison_exists=analysed.comparison_exists,
        selected_snapshot_ids=analysed.selected_snapshot_ids,
        readiness_reasons=analysed.readiness_reasons,
    )
    return LoadedPageHistory(website_page, records, outcome, quality)


@router.get(
    "/imports",
    response_model=ImportRunList,
    summary="List completed imports newest first / 按从新到旧的顺序列出已完成导入",
)
def list_imports(
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ImportRunList:
    """Expose read-only import provenance with stable offset pagination.
    通过稳定的偏移量分页提供只读导入来源记录。
    """
    try:
        total = session.scalar(select(func.count()).select_from(ImportRun)) or 0
        imports = session.scalars(
            select(ImportRun)
            .order_by(ImportRun.imported_at.desc(), ImportRun.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    except SQLAlchemyError:
        raise _database_unavailable() from None
    return ImportRunList(
        items=[ImportRunResponse.model_validate(item) for item in imports],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/pages/{page_id}/performance",
    response_model=PagePerformanceHistory,
    summary="Read page snapshots and compatible-period comparison / 读取页面快照与兼容周期比较",
)
def page_performance(
    page_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PagePerformanceHistory:
    """Keep import chronology, latest-applied metrics, and report-period comparison distinct.
    明确区分导入时间顺序、最新应用的指标与报告周期比较。

    Comparison uses all page history, independently of the displayed snapshot page.
    比较使用全部页面历史记录，不依赖当前展示的快照页。
    """
    loaded = _load_page_history(session, page_id)
    records = loaded.records
    outcome = loaded.comparison
    offset = (page - 1) * page_size
    items = [
        PerformanceSnapshotResponse(
            id=snapshot.id,
            import_run_id=snapshot.import_run_id,
            page_id=snapshot.page_id,
            url=snapshot.url,
            source=import_run.source,
            source_type=import_run.source_type,
            reporting_window=import_run.reporting_window,
            period_start=snapshot.period_start,
            period_end=snapshot.period_end,
            imported_at=import_run.imported_at,
            created_at=snapshot.created_at,
            clicks=snapshot.clicks,
            impressions=snapshot.impressions,
            ctr=snapshot.ctr,
            average_position=snapshot.average_position,
        )
        for snapshot, import_run in records[offset : offset + page_size]
    ]
    total = len(records)
    return PagePerformanceHistory(
        current_page=WebsitePageResponse.model_validate(loaded.page),
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
        comparison=(
            PerformanceComparisonResponse.model_validate(outcome.comparison)
            if outcome.comparison is not None
            else None
        ),
        comparison_unavailable_reason=outcome.unavailable_reason,
        quality=loaded.quality,
    )


@router.get(
    "/pages/{page_id}/quality",
    response_model=PageQualityResponse,
    summary="Read page evidence quality and readiness / 读取页面证据质量与就绪状态",
)
def page_quality(
    page_id: UUID, session: Annotated[Session, Depends(get_session)]
) -> PageQualityResponse:
    """Return the same full-history quality summary embedded in page performance.
    返回与页面性能响应内嵌结果一致的完整历史质量摘要。
    """
    return _load_page_history(session, page_id).quality


@router.get(
    "/imports/{import_run_id}/quality",
    response_model=ImportQualityResponse,
    summary="Read factual import evidence observations / 读取导入证据的事实性观察",
)
def import_quality(
    import_run_id: UUID, session: Annotated[Session, Depends(get_session)]
) -> ImportQualityResponse:
    """Inspect one import against its source/type/window context without database writes.
    根据同来源、类型与窗口的上下文检查一个导入，不写入数据库。
    """
    try:
        target = session.get(ImportRun, import_run_id)
        if target is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "import_not_found",
                    "message": "Import not found. / 未找到导入记录。",
                },
            )
        records = session.scalars(
            select(ImportRun)
            .where(
                ImportRun.source == target.source,
                ImportRun.source_type == target.source_type,
                ImportRun.reporting_window == target.reporting_window,
            )
            .order_by(ImportRun.imported_at, ImportRun.id)
        ).all()
    except SQLAlchemyError:
        raise _database_unavailable() from None
    evidence = [
        ImportEvidence(
            id=run.id,
            source=run.source,
            source_type=run.source_type,
            reporting_window=run.reporting_window,
            period_start=run.period_start,
            period_end=run.period_end,
            imported_at=run.imported_at,
            file_hash=run.file_hash,
        )
        for run in records
    ]
    target_evidence = next(item for item in evidence if item.id == import_run_id)
    analysed = analyse_import_quality(target_evidence, evidence)
    return ImportQualityResponse(
        import_run_id=import_run_id,
        observations=[
            QualityObservationResponse.model_validate(item) for item in analysed.observations
        ],
        counts=analysed.counts,
    )
