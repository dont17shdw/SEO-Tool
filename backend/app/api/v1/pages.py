from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.schemas import WebsitePageList, WebsitePageResponse
from app.db.session import get_session
from app.models import WebsitePage

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get(
    "",
    response_model=WebsitePageList,
    summary="List imported pages with pagination / 分页列出已导入的页面",
)
def list_pages(
    session: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> WebsitePageList:
    """Return a stable read-only page list; an empty database has zero total pages.
    返回稳定排序的只读页面列表；空数据库的总页数为零。
    """
    try:
        total = session.scalar(select(func.count()).select_from(WebsitePage)) or 0
        pages = session.scalars(
            select(WebsitePage)
            .order_by(WebsitePage.created_at, WebsitePage.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "database_unavailable",
                "message": "Pages are unavailable. Try again. / 页面暂时不可用，请重试。",
            },
        ) from None
    return WebsitePageList(
        items=[WebsitePageResponse.model_validate(item) for item in pages],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )
