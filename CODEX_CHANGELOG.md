# CODEX Change Log

## 2025-10-31 - Metadata Collector Normalisation
- Normalised table identifiers in `backend/services/db_context_collector.py` to handle aliases, schema prefixes, and quotes.
- Deduplicated table requests and relaxed identifier validation to include underscore-prefixed names.
- Ensures AI context collection works even when fingerprints contain aliased tables, reducing noisy warnings.

## 2025-10-31 - AI Query Variant Proposals
- Updated `backend/services/ai_stub.py` and related helpers so every AI analysis returns at least three concrete query modifications with SQL snippets.
- Adjusted prompts and added deterministic fallbacks when the provider omits query rewrites.
- Guarantees the frontend receives actionable query variants alongside the existing recommendations.
