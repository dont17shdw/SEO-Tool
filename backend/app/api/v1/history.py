from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.analysis.current_provenance import RecordedMetricSource, analyse_current_provenance
from app.analysis.data_quality import (
    ImportEvidence,
    PageQuality,
    analyse_import_quality,
    analyse_page_quality,
)
from app.analysis.opportunity_engine import analyse_page_opportunities
from app.analysis.performance_comparison import (
    ComparisonOutcome,
    PerformanceObservation,
    compare_performance,
)
from app.api.v1.schemas import (
    ImportQualityResponse,
    ImportRunList,
    ImportRunResponse,
    PageOpportunityAnalysisResponse,
    PagePerformanceHistory,
    PageProvenanceResponse,
    PageQualityCounts,
    PageQualityResponse,
    PerformanceComparisonResponse,
    PerformanceSnapshotResponse,
    QualityObservationResponse,
    WebsitePageResponse,
)
from app.db.session import get_session
from app.models import ImportRun, PageMetricProvenance, PagePerformanceSnapshot, WebsitePage

router = APIRouter(tags=["performance history"])


@dataclass(frozen=True)
class LoadedPageHistory:
    page: WebsitePage
    records: list[tuple[PagePerformanceSnapshot, ImportRun]]
    comparison: ComparisonOutcome
    quality: PageQualityResponse
    provenance: PageProvenanceResponse | None
    observations: list[PerformanceObservation]
    analysed_quality: PageQuality


def _database_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "database_unavailable",
            "message": "History is unavailable. Try again. / 历史记录暂时不可用，请重试。",
        },
    )


def _load_page_history(
    session: Session, page_id: UUID, *, include_provenance: bool = False
) -> LoadedPageHistory:
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
        sources = (
            session.scalars(
                select(PageMetricProvenance).where(PageMetricProvenance.page_id == page_id)
            ).all()
            if include_provenance
            else []
        )
    except SQLAlchemyError:
        raise _database_unavailable() from None
    return _analyse_page_history(website_page, records, sources if include_provenance else None)


def _analyse_page_history(
    website_page: WebsitePage,
    records: list[tuple[PagePerformanceSnapshot, ImportRun]],
    sources: list[PageMetricProvenance] | None = None,
) -> LoadedPageHistory:
    """Share comparison and readiness analysis between individual and grouped reads.
    在单页与分组读取之间共享比较和就绪度分析。
    """
    page_id = website_page.id
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
            report_scope=run.report_scope,
            coverage_status=run.coverage_status,
            observed_date_count=run.observed_date_count,
            dates_consecutive=run.dates_consecutive,
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
    provenance = None
    if sources is not None:
        analysed_provenance = analyse_current_provenance(
            page_id=page_id,
            current_values={
                "clicks_28d": website_page.clicks_28d,
                "impressions_28d": website_page.impressions_28d,
                "ctr": website_page.ctr,
                "average_position": website_page.average_position,
            },
            observations=observations,
            snapshot_import_ids={snapshot.id: run.id for snapshot, run in records},
            recorded_sources=[
                RecordedMetricSource(item.page_id, item.metric_name, item.snapshot_id)
                for item in sources
            ],
        )
        provenance = PageProvenanceResponse.model_validate(analysed_provenance)
    return LoadedPageHistory(
        website_page, records, outcome, quality, provenance, observations, analysed
    )


def _load_grouped_page_histories(
    session: Session, *, site_id: UUID | None = None
) -> list[LoadedPageHistory]:
    """Batch page histories in two reads without paginating pages before candidate detection.
    使用两次读取批量载入页面历史，不在候选检测前对页面分页。

    Full histories remain in memory for development scale; no candidate cache is stored.
    开发规模下完整历史保留于内存中，不存储候选缓存。
    """
    pages_statement = select(WebsitePage).order_by(WebsitePage.url, WebsitePage.id)
    records_statement = (
        select(PagePerformanceSnapshot, ImportRun)
        .join(ImportRun, ImportRun.id == PagePerformanceSnapshot.import_run_id)
        .join(WebsitePage, WebsitePage.id == PagePerformanceSnapshot.page_id)
        .order_by(
            PagePerformanceSnapshot.page_id, ImportRun.imported_at, PagePerformanceSnapshot.id
        )
    )
    if site_id is not None:
        pages_statement = pages_statement.where(WebsitePage.site_id == site_id)
        records_statement = records_statement.where(WebsitePage.site_id == site_id)
    try:
        website_pages = session.scalars(pages_statement).all()
        grouped = {website_page.id: [] for website_page in website_pages}
        for snapshot, run in session.execute(records_statement):
            # Concurrent newly created pages are omitted from this request's page set.
            # 并发新建页面不加入本次请求已载入的页面集合。
            if snapshot.page_id in grouped:
                grouped[snapshot.page_id].append((snapshot, run))
    except SQLAlchemyError:
        raise _database_unavailable() from None
    return [
        _analyse_page_history(website_page, grouped[website_page.id])
        for website_page in website_pages
    ]


def _page_opportunities(loaded: LoadedPageHistory) -> PageOpportunityAnalysisResponse:
    """Reuse the exact selected comparison and quality facts without another database read.
    复用完全相同的所选比较与质量事实，不增加数据库读取。
    """
    return PageOpportunityAnalysisResponse.model_validate(
        analyse_page_opportunities(
            page_id=loaded.page.id,
            site_id=loaded.page.site_id,
            url=loaded.page.url,
            observations=loaded.observations,
            outcome=loaded.comparison,
            quality=loaded.analysed_quality,
        )
    )


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
    "/imports/{import_run_id}",
    response_model=ImportRunResponse,
    summary="Read report scope and observed coverage / 读取报告范围及已观察覆盖",
)
def import_details(
    import_run_id: UUID, session: Annotated[Session, Depends(get_session)]
) -> ImportRunResponse:
    """Inspect one stored report without inferring missing ownership or coverage.
    检查一个已存储报告，不推断缺失的归属或覆盖。
    """
    try:
        record = session.get(ImportRun, import_run_id)
    except SQLAlchemyError:
        raise _database_unavailable() from None
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "import_not_found", "message": "Import not found. / 未找到导入记录。"},
        )
    return ImportRunResponse.model_validate(record)


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
    loaded = _load_page_history(session, page_id, include_provenance=True)
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
            site_id=import_run.site_id,
            report_scope=import_run.report_scope,
            observed_date_count=import_run.observed_date_count,
            dates_consecutive=import_run.dates_consecutive,
            coverage_status=import_run.coverage_status,
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
        provenance=loaded.provenance,
        opportunities=_page_opportunities(loaded),
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
    "/pages/{page_id}/provenance",
    response_model=PageProvenanceResponse,
    summary="Read recorded current-metric sources / 读取已记录的当前指标来源",
)
def page_provenance(
    page_id: UUID, session: Annotated[Session, Depends(get_session)]
) -> PageProvenanceResponse:
    """Return proven current metric sources, separate from comparison readiness.
    返回已证明的当前指标来源，与对比就绪度相互独立。
    """
    loaded = _load_page_history(session, page_id, include_provenance=True)
    assert loaded.provenance is not None
    return loaded.provenance


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
            report_scope=run.report_scope,
            observed_date_count=run.observed_date_count,
            dates_consecutive=run.dates_consecutive,
            coverage_status=run.coverage_status,
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
