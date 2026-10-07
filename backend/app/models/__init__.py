"""Persisted entities; calculations and recommendation rules live elsewhere.
持久化实体；计算和推荐规则位于其他模块。
"""

from app.models.seo_opportunity import SEOOpportunity
from app.models.website_page import WebsitePage

__all__ = ["SEOOpportunity", "WebsitePage"]
