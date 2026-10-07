from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.analysis.performance_comparison import PerformanceObservation, compare_performance
from app.api.v1.schemas import (
    ImportRunList,
    ImportRunResponse,
    PagePerformanceHistory,
    PerformanceComparisonResponse,
    PerformanceSnapshotResponse,
    WebsitePageResponse,
)
from app.db.session import get_session
from app.models import ImportRun, PagePerformanceSnapshot, WebsitePage

router = APIRouter(tags=["performance history"])


def _database_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "database_unavailable",
            "message": "History is unavailable. Try again. / 历史记录暂时不可用，请重试。",
        },
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
        # All observations are required for pagination-independent comparison selection.
        # 需要全部观测记录，才能使比较选择独立于分页。
        records = session.execute(statement).all()
    except SQLAlchemyError:
        raise _database_unavailable() from None
    observations = [
        PerformanceObservation(
            id=snapshot.id,
            page_id=snapshot.page_id,
            source=import_run.source,
            source_type=import_run.source_type,
            reporting_window=import_run.reporting_window,
            period_start=snapshot.period_start,
            period_end=snapshot.period_end,
            imported_at=import_run.imported_at,
            clicks=snapshot.clicks,
            impressions=snapshot.impressions,
            ctr=snapshot.ctr,
            average_position=snapshot.average_position,
        )
        for snapshot, import_run in records
    ]
    outcome = compare_performance(observations)
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
        current_page=WebsitePageResponse.model_validate(website_page),
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
    )
