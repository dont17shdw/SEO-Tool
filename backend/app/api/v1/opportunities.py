"""Expose deterministic evidence-backed candidates without changing stored opportunities.
公开由证据支持的确定性候选，不修改已存储机会。
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.history import (
    _load_grouped_page_histories,
    _load_page_history,
    _page_opportunities,
)
from app.api.v1.schemas import OpportunityCandidateList, PageOpportunityAnalysisResponse
from app.db.session import get_session

router = APIRouter(tags=["opportunity candidates"])


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
