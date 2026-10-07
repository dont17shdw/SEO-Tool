# SEO Tool - Agent Instructions
# SEO Tool - 代理开发指南

## Project Vision
## 项目愿景

Build an AI-powered SEO operations system.
构建由 AI 辅助的 SEO 运营系统。

Long-term workflow:
长期工作流程：

DATA → ANALYZE → DECIDE → ACT → MEASURE → LEARN

The system should determine the highest-value SEO action based on available website data.
系统应根据可用的网站数据确定最有价值的 SEO 行动。

It must not default to generating new articles.
系统不得默认选择生成新文章。

Possible actions include:
未来可能的行动包括：

- Update existing content
  更新现有内容
- Improve titles and meta descriptions
  改进标题和元描述
- Improve product pages
  改进产品页面
- Fix indexing issues
  修复索引问题
- Add internal links
  添加内部链接
- Detect keyword cannibalization
  检测关键词竞争
- Create new content
  创建新内容
- Build backlinks
  建立外部链接
- Refresh old content
  更新旧内容
- Recommend no action
  建议无需行动

## V1 Scope
## V1 范围

V1 should focus only on:
V1 仅关注：

DATA → ANALYZE → PRIORITIZE → RECOMMEND

Do not implement autonomous SEO execution yet.
现阶段不要实现自主 SEO 执行。

## Architecture Principles
## 架构原则

- Keep data ingestion, analysis, decision-making and execution separate.
  将数据导入、分析、决策和执行分开。
- Prefer deterministic code for calculations.
  计算优先使用确定性的代码。
- Use AI mainly for semantic analysis and reasoning.
  AI 主要用于语义分析和推理。
- Do not tightly couple the application to one AI model.
  不要将应用与单一 AI 模型紧密耦合。
- Keep the architecture extensible.
  保持架构可扩展。
- Avoid unnecessary complexity.
  避免不必要的复杂性。
- Build and test incrementally.
  逐步构建和测试。

## Initial Technology Stack
## 初始技术栈

Frontend:
前端：
- Next.js
- React
- TypeScript

Backend:
后端：
- Python
- FastAPI

Database:
数据库：
- PostgreSQL

## Development Rule
## 开发规则

Before making major architectural changes:
进行重大架构变更之前：

1. Inspect the existing repository.
   检查现有仓库。
2. Explain the intended change.
   解释计划的变更。
3. Preserve existing architecture unless there is a strong reason to change it.
   除非有充分理由，否则保留现有架构。
4. Implement the smallest complete step.
   实现最小但完整的一步。
5. Test the result.
   测试结果。
6. Update documentation when architecture changes.
   架构变更时更新文档。

## Bilingual Code Documentation
## 双语代码文档

All important code comments and documentation must be bilingual: English first, Chinese second.
所有重要的代码注释和文档必须使用双语：英文在前，中文在后。

Use bilingual docstrings for functions and classes with non-trivial logic. Document architecture boundaries, database semantics, normalization, scoring, SEO rules, AI reasoning, API behavior, and non-obvious implementation details where they improve understanding.
对包含非简单逻辑的函数和类使用双语文档字符串。在有助于理解时，说明架构边界、数据库语义、标准化、评分、SEO 规则、AI 推理、API 行为和不明显的实现细节。

Do not add comments to every trivial line. Keep variable names, function names, class names, database fields, filenames, and API paths in English.
不要给每一行简单代码添加注释。变量名、函数名、类名、数据库字段、文件名和 API 路径保持英文。

```python
def normalize_metrics(metrics):
    """
    Normalize imported SEO metrics before storing them.
    在写入数据库之前标准化导入的 SEO 指标。
    """
```
