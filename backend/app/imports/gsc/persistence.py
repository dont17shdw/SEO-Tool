from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.imports.gsc.schemas import NormalizedGSCRow
from app.models import WebsitePage

GSC_FIELDS = ("clicks_28d", "impressions_28d", "ctr", "average_position")


@dataclass
class ImportCounts:
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0


def persist_gsc_pages(session: Session, rows: Sequence[NormalizedGSCRow]) -> ImportCounts:
    """Commit the complete validated file, preserving omitted and unrelated fields.
    一次提交整个已校验文件，保留未提供的字段及无关字段。

    PostgreSQL resolves concurrent URL inserts before a locked existing-row update.
    PostgreSQL 先处理并发 URL 插入，再锁定已存在的行进行更新。
    """
    result = ImportCounts()
    with session.begin():
        # Consistent URL ordering reduces deadlocks between overlapping imports.
        # 一致的 URL 排序减少导入内容重叠时发生死锁的可能。
        for row in sorted(rows, key=lambda item: item.url):
            supplied = {
                field: value for field in GSC_FIELDS if (value := getattr(row, field)) is not None
            }
            statement = (
                insert(WebsitePage)
                .values(url=row.url, **supplied)
                .on_conflict_do_nothing(index_elements=[WebsitePage.url])
                .returning(WebsitePage.id)
            )
            inserted_id = session.execute(statement).scalar_one_or_none()
            if inserted_id is not None:
                result.created_count += 1
                continue

            page = session.execute(
                select(WebsitePage).where(WebsitePage.url == row.url).with_for_update()
            ).scalar_one()
            changed = False
            for field, value in supplied.items():
                if getattr(page, field) != value:
                    setattr(page, field, value)
                    changed = True
            if changed:
                result.updated_count += 1
            else:
                result.skipped_count += 1
    return result
