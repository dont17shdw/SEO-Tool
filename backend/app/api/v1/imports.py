from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.schemas import ImportResult
from app.db.session import get_session
from app.imports.gsc.parser import (
    MAX_FILE_SIZE,
    ImportFileError,
    ImportPreview,
    ParsedImport,
    parse_gsc_pages,
)
from app.imports.gsc.persistence import persist_gsc_pages
from app.normalization.report_scope import ScopeDeclaration

router = APIRouter(prefix="/imports/gsc/pages", tags=["GSC imports"])


def import_scope(
    scope: Annotated[str | None, Form(max_length=8192)] = None,
) -> ScopeDeclaration | None:
    """Accept structured declarations without guessing missing report evidence.
    接受结构化声明，不猜测缺失的报告证据。
    """
    if scope is None:
        return None
    try:
        return ScopeDeclaration.model_validate_json(scope)
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_report_scope",
                "message": (
                    "Provide a valid structured scope declaration. / 请提供有效的结构化范围声明。"
                ),
            },
        ) from None


def parse_upload(file: UploadFile, scope: ScopeDeclaration | None = None) -> ParsedImport:
    """Read a bounded, ephemeral upload and return deterministic normalized data.
    读取有大小限制的临时上传文件，并返回确定性的标准化数据。
    """
    content = file.file.read(MAX_FILE_SIZE + 1)
    try:
        return parse_gsc_pages(content, file.filename or "", scope)
    except ImportFileError as error:
        status_code = 413 if error.code in {"file_too_large", "too_many_rows"} else 422
        raise HTTPException(
            status_code=status_code, detail={"code": error.code, "message": error.message}
        ) from None


def confirmed_import(
    file: Annotated[UploadFile, File()],
    confirmed: Annotated[bool, Form()],
    preview_hash: Annotated[str, Form(min_length=64, max_length=64, pattern="^[0-9a-f]{64}$")],
    scope: Annotated[ScopeDeclaration | None, Depends(import_scope)],
) -> ParsedImport:
    """Revalidate the exact previewed file before a database dependency is resolved.
    在解析数据库依赖之前，重新校验与预览完全相同的文件。
    """
    if not confirmed:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "confirmation_required",
                "message": "Confirm the preview before importing. / 导入前请确认预览。",
            },
        )
    parsed = parse_upload(file, scope)
    if parsed.preview.preview_hash != preview_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "preview_changed",
                "message": (
                    "The file or report scope changed. Preview it again. / "
                    "文件或报告范围已变更，请重新预览。"
                ),
            },
        )
    if not parsed.preview.can_apply:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_import",
                "message": (
                    "Correct every invalid or duplicate row before importing. / "
                    "导入前请修正所有无效或重复的行。"
                ),
            },
        )
    return parsed


@router.post(
    "/preview",
    response_model=ImportPreview,
    summary="Preview GSC pages without database writes / 预览 GSC 页面且不写入数据库",
)
def preview_pages(
    file: Annotated[UploadFile, File()],
    scope: Annotated[ScopeDeclaration | None, Depends(import_scope)],
) -> ImportPreview:
    """Preview parsing and validation independently of PostgreSQL.
    独立于 PostgreSQL 预览解析和校验结果。
    """
    return parse_upload(file, scope).preview


@router.post(
    "/apply",
    response_model=ImportResult,
    summary="Confirm and import validated GSC pages / 确认并导入已校验的 GSC 页面",
)
def apply_pages(
    parsed: Annotated[ParsedImport, Depends(confirmed_import)],
    session: Annotated[Session, Depends(get_session)],
) -> ImportResult:
    """Persist only after confirmation and validation, using one transaction.
    仅在确认并完成校验后，使用一个事务持久化数据。
    """
    try:
        return ImportResult.model_validate(persist_gsc_pages(session, parsed), from_attributes=True)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "database_unavailable",
                "message": (
                    "The import could not be saved. No changes were committed; try again. / "
                    "无法保存导入，未提交任何变更；请重试。"
                ),
            },
        ) from None
