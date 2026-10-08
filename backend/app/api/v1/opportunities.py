"""Expose deterministic evidence-backed candidates without changing stored opportunities.
公开由证据支持的确定性候选，不修改已存储机会。
"""

from dataclasses import asdict
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analysis.data_quality import CODE_ORDER
from app.analysis.opportunity_engine import PageOpportunityAnalysis
from app.analysis.opportunity_prioritization import prioritize_candidates
from app.api.v1.history import (
    LoadedPageHistory,
    _load_grouped_page_histories,
    _load_page_history,
    _page_opportunities,
    _page_opportunity_analysis,
)
from app.api.v1.schemas import (
    OpportunityCandidateList,
    OpportunityEligibilitySummary,
    PageOpportunityAnalysisResponse,
    PrioritizedOpportunityCandidateList,
    PrioritizedOpportunityCandidateResponse,
)
from app.db.session import get_session

router = APIRouter(tags=["opportunity candidates"])


def _eligibility_summary(
    pages: list[tuple[LoadedPageHistory, PageOpportunityAnalysis]],
) -> OpportunityEligibilitySummary:
    """Explain unavailable evidence without changing selected readiness or detection gates.
    解释不可用证据，不改变所选就绪度或检测门槛。

    When no pair exists, recorded scope/date/coverage facts supplement the broad history code.
    当不存在快照对时，已记录范围、日期及覆盖事实补充宽泛的历史代码。
    Counts overlap; unrelated historical warnings never label an eligible page blocked.
    计数可重叠；无关历史警告绝不将合格页面标为受阻。
    """
    counts = dict.fromkeys(CODE_ORDER, 0)
    eligible = detected_pages = detected_candidates = 0
    unavailable_evidence_codes = {
        "unknown_report_scope",
        "incompatible_report_scope",
        "unknown_reporting_dates",
        "incomplete_date_coverage",
        "unknown_date_coverage",
    }
    for loaded, analysis in pages:
        eligible += int(analysis.eligible)
        detected_pages += int(bool(analysis.candidates))
        detected_candidates += len(analysis.candidates)
        if analysis.eligible:
            continue
        reasons = set(analysis.gate_reasons)
        if analysis.comparison is None:
            reasons.update(
                item.code
                for item in loaded.analysed_quality.observations
                if item.code in unavailable_evidence_codes
            )
        for reason in reasons:
            counts[reason] += 1
    return OpportunityEligibilitySummary(
        analyzed_pages=len(pages),
        eligible_pages=eligible,
        ineligible_pages=len(pages) - eligible,
        pages_with_candidates=detected_pages,
        ready_pages_without_candidates=eligible - detected_pages,
        detected_candidates=detected_candidates,
        gate_reason_counts=counts,
    )


@router.get(
    "/opportunities/prioritized",
    response_model=PrioritizedOpportunityCandidateList,
    summary="Read transparent priority tiers and eligibility / 读取透明优先级与证据资格",
)
def list_prioritized_opportunities(
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    site_id: Annotated[UUID | None, Query()] = None,
    priority_tier: Annotated[Literal["high", "medium", "low"] | None, Query()] = None,
) -> PrioritizedOpportunityCandidateList:
    """Prioritize existing signals with two grouped reads and one analysis per page.
    使用两次分组读取及每页一次分析，对已有信号分配优先级。

    Summary describes the selected site's evidence before tier filtering and pagination.
    摘要在级别筛选及分页之前描述所选站点的证据。
    Candidate totals and pages describe the filtered list, independently of page counts.
    候选总数与分页描述筛选后的列表，独立于页面计数。
    """
    analysed = [
        (loaded, _page_opportunity_analysis(loaded))
        for loaded in _load_grouped_page_histories(session, site_id=site_id)
    ]
    wrappers = prioritize_candidates(
        [candidate for _, analysis in analysed for candidate in analysis.candidates]
    )
    filtered = [
        item for item in wrappers if priority_tier is None or item.priority_tier == priority_tier
    ]
    total = len(filtered)
    offset = (page - 1) * page_size
    items = []
    for item in filtered[offset : offset + page_size]:
        metadata = asdict(item)
        candidate = metadata.pop("candidate")
        items.append(PrioritizedOpportunityCandidateResponse(**candidate, **metadata))
    return PrioritizedOpportunityCandidateList(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
        summary=_eligibility_summary(analysed),
    )


@router.get(
    "/pages/{page_id}/opportunities",
    response_model=PageOpportunityAnalysisResponse,
    summary="Read page opportunity candidates and evidence gate / 读取页面机会候选与证据门槛",
)
def page_opportunities(
    page_id: UUID, session: Annotated[Session, Depends(get_session)]
) -> PageOpportunityAnalysisResponse:
    """Reuse full-history comparison and readiness, independently of current applied metrics.
    复用完整历史的比较与就绪度，独立于当前应用指标。
    """
    return _page_opportunities(_load_page_history(session, page_id))


@router.get(
    "/opportunities",
    response_model=OpportunityCandidateList,
    summary="List runtime opportunity candidates with pagination / 分页列出运行时机会候选",
)
def list_opportunities(
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    site_id: Annotated[UUID | None, Query()] = None,
) -> OpportunityCandidateList:
    """Paginate actual candidates after neutral URL/type/page-ID ordering, without ranking.
    按中立的 URL、类型及页面 ID 排序后对实际候选分页，不进行优先级排名。

    A site filter follows stored page ownership; a missing site yields an empty result.
    站点筛选遵循已存储页面归属；不存在的站点返回空结果。
    """
    candidates = [
        candidate
        for loaded in _load_grouped_page_histories(session, site_id=site_id)
        for candidate in _page_opportunities(loaded).candidates
    ]
    candidates.sort(key=lambda item: (item.url, item.opportunity_type, item.page_id.int))
    total = len(candidates)
    offset = (page - 1) * page_size
    return OpportunityCandidateList(
        items=candidates[offset : offset + page_size],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )
