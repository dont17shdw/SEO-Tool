# SEO Tool - Agent Instructions

## Project Vision

Build an AI-powered SEO operations system.

Long-term workflow:

DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN

The system should determine the highest-value SEO action based on available website data.

It must not default to generating new articles.

Possible actions include:

- Update existing content
- Improve titles and meta descriptions
- Improve product pages
- Fix indexing issues
- Add internal links
- Detect keyword cannibalization
- Create new content
- Build backlinks
- Refresh old content
- Recommend no action

## V1 Scope

V1 should focus only on:

DATA → ANALYZE → PRIORITIZE → RECOMMEND

Do not implement autonomous SEO execution yet.

## Architecture Principles

- Keep data ingestion, analysis, decision-making and execution separate.
- Prefer deterministic code for calculations.
- Use AI mainly for semantic analysis and reasoning.
- Do not tightly couple the application to one AI model.
- Keep the architecture extensible.
- Avoid unnecessary complexity.
- Build and test incrementally.

## Initial Technology Stack

Frontend:
- Next.js
- React
- TypeScript

Backend:
- Python
- FastAPI

Database:
- PostgreSQL

## Development Rule

Before making major architectural changes:

1. Inspect the existing repository.
2. Explain the intended change.
3. Preserve existing architecture unless there is a strong reason to change it.
4. Implement the smallest complete step.
5. Test the result.
6. Update documentation when architecture changes.
