# CODEX Change Log

## 2025-10-31 - Metadata Collector Normalisation
- Normalised table identifiers in `backend/services/db_context_collector.py` to handle aliases, schema prefixes, and quotes.
- Deduplicated table requests and relaxed identifier validation to include underscore-prefixed names.
- Ensures AI context collection works even when fingerprints contain aliased tables, reducing noisy warnings.

## 2025-10-31 - AI Query Variant Proposals
- Updated `backend/services/ai_stub.py` and related helpers so every AI analysis returns at least three concrete query modifications with SQL snippets.
- Adjusted prompts and added deterministic fallbacks when the provider omits query rewrites.
- Guarantees the frontend receives actionable query variants alongside the existing recommendations.

## 2025-10-31 - Heavy MySQL Slow Query Generator
- Added `ai-query-lab/db/mysql/generate_heavy_slow_queries.sh` to provision 100k synthetic customers, 1M orders, and execute three complex workloads against `mysql-lab`.
- The script builds digit helper tables, synthesises realistic data, and issues correlated, windowed, and anti-join queries to guarantee slow-log entries.
- Keeps test automation clean by living separately from `test_slow_queries.sh` while providing a repeatable way to stress MySQL.
- Refined the generator to suppress CLI password warnings and handle existing row counts reliably so reruns skip expensive loads gracefully.
