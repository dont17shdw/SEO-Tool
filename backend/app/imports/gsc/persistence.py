from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.imports.gsc.schemas import ParsedImport
from app.models import ImportRun, PageMetricProvenance, PagePerformanceSnapshot, Site, WebsitePage

GSC_FIELDS = ("clicks_28d", "impressions_28d", "ctr", "average_position")
PROVENANCE_BATCH_SIZE = 1000


@dataclass
class ImportCounts:
    import_run_id: UUID
    already_processed: bool = False
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0


def persist_gsc_pages(session: Session, parsed: ParsedImport) -> ImportCounts:
    """Atomically commit site ownership, scoped history, metrics and explicit sources.
    原子提交站点归属、带范围的历史、指标及明确来源。

    A file-and-scope reservation serializes retries before any page or provenance writes.
    文件与范围联合预留会在写入任何页面或来源之前串行化重试。
    """
    preview = parsed.preview
    if not preview.can_apply or preview.total_rows != len(parsed.rows):
        raise ValueError("Only a complete, validated import can be persisted")

    with session.begin():
        # Only explicit property evidence establishes ownership; URLs never assign legacy pages.
        # 仅明确属性证据建立归属；绝不根据 URL 分配旧页面。
        property_id = preview.report_scope.property_id
        site_id = None
        if property_id is not None:
            site_id = session.execute(
                insert(Site)
                .values(identifier=property_id, display_name=property_id)
                .on_conflict_do_nothing(index_elements=[Site.identifier])
                .returning(Site.id)
            ).scalar_one_or_none()
            if site_id is None:
                site_id = session.scalar(select(Site.id).where(Site.identifier == property_id))

        # Counts are provisional inside this transaction and finalized before commit.
        # 统计值在事务内部是临时值，会在提交前更新为最终结果。
        run_id = session.execute(
            insert(ImportRun)
            .values(
                source="gsc",
                source_type="pages_performance",
                file_hash=preview.file_hash,
                scope_fingerprint=preview.report_scope.fingerprint,
                report_scope=preview.report_scope.model_dump(mode="json"),
                site_id=site_id,
                filename=parsed.filename,
                reporting_window=preview.reporting_window,
                period_start=preview.period_start,
                period_end=preview.period_end,
                observed_date_count=preview.observed_date_count,
                dates_consecutive=preview.dates_consecutive,
                coverage_status=preview.coverage_status,
                total_rows=preview.total_rows,
                skipped_count=preview.total_rows,
                status="completed",
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ImportRun.source,
                    ImportRun.source_type,
                    ImportRun.file_hash,
                    ImportRun.scope_fingerprint,
                ]
            )
            .returning(ImportRun.id)
        ).scalar_one_or_none()
        if run_id is None:
            existing = session.execute(
                select(ImportRun.id, ImportRun.total_rows).where(
                    ImportRun.source == "gsc",
                    ImportRun.source_type == "pages_performance",
                    ImportRun.file_hash == preview.file_hash,
                    ImportRun.scope_fingerprint == preview.report_scope.fingerprint,
                    ImportRun.status == "completed",
                )
            ).one()
            return ImportCounts(
                import_run_id=existing.id,
                already_processed=True,
                skipped_count=existing.total_rows,
            )

        result = ImportCounts(import_run_id=run_id)
        snapshots: list[PagePerformanceSnapshot] = []
        provenance_rows: list[dict[str, UUID | str]] = []
        # Consistent URL ordering reduces deadlocks between overlapping imports.
        # 一致的 URL 排序减少导入内容重叠时发生死锁的可能。
        for row in sorted(parsed.rows, key=lambda item: item.url):
            supplied = {
                field: value for field in GSC_FIELDS if (value := getattr(row, field)) is not None
            }
            statement = (
                insert(WebsitePage)
                .values(site_id=site_id, url=row.url, **supplied)
                .on_conflict_do_nothing(index_elements=[WebsitePage.site_id, WebsitePage.url])
                .returning(WebsitePage.id)
            )
            inserted_id = session.execute(statement).scalar_one_or_none()
            if inserted_id is not None:
                result.created_count += 1
                page_id = inserted_id
            else:
                page = session.execute(
                    select(WebsitePage)
                    .where(
                        WebsitePage.url == row.url,
                        WebsitePage.site_id == site_id
                        if site_id is not None
                        else WebsitePage.site_id.is_(None),
                    )
                    .with_for_update()
                ).scalar_one()
                page_id = page.id
                changed = False
                for field, value in supplied.items():
                    if getattr(page, field) != value:
                        setattr(page, field, value)
                        changed = True
                if changed:
                    result.updated_count += 1
                else:
                    result.skipped_count += 1

            # History stores supplied observations, never values retained from older uploads.
            # 历史记录仅保存本次提供的观测值，不使用旧上传中保留的值。
            snapshot = PagePerformanceSnapshot(
                id=uuid4(),
                import_run_id=run_id,
                page_id=page_id,
                url=row.url,
                clicks=row.clicks_28d,
                impressions=row.impressions_28d,
                ctr=row.ctr,
                average_position=row.average_position,
                period_start=preview.period_start,
                period_end=preview.period_end,
            )
            snapshots.append(snapshot)
            # Explicit observations refresh their source even when the current value is unchanged.
            # 明确提供的观测值即使与当前值相同，也会刷新其来源。
            provenance_rows.extend(
                {"page_id": page_id, "metric_name": field, "snapshot_id": snapshot.id}
                for field in supplied
            )
        session.add_all(snapshots)
        # Referenced snapshots must exist before links; page locks last until the same commit.
        # 创建关联之前，被引用的快照必须已存在；页面锁持续到同一次提交完成。
        session.flush()
        # Bound parameters per statement even for an accepted 10,000-row upload.
        # 即使上传包含允许的 10,000 行，也限制每条语句的参数数量。
        for offset in range(0, len(provenance_rows), PROVENANCE_BATCH_SIZE):
            provenance_insert = insert(PageMetricProvenance).values(
                provenance_rows[offset : offset + PROVENANCE_BATCH_SIZE]
            )
            session.execute(
                provenance_insert.on_conflict_do_update(
                    index_elements=[PageMetricProvenance.page_id, PageMetricProvenance.metric_name],
                    set_={"snapshot_id": provenance_insert.excluded.snapshot_id},
                )
            )
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == run_id)
            .values(
                created_count=result.created_count,
                updated_count=result.updated_count,
                skipped_count=result.skipped_count,
            )
        )
    return result
