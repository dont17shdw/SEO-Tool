"""Parse GSC Pages exports without persistence or SEO interpretation.
解析 GSC 网页导出文件，不进行持久化或 SEO 解读。
"""

from app.imports.gsc.parser import ImportFileError, parse_gsc_pages
from app.imports.gsc.schemas import ImportPreview, NormalizedGSCRow, ParsedImport

__all__ = [
    "ImportFileError",
    "ImportPreview",
    "NormalizedGSCRow",
    "ParsedImport",
    "parse_gsc_pages",
]
