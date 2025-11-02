"""
AI-assisted query analysis stub.

Placeholder for future LLM integration (OpenAI, Anthropic, etc.)
for advanced query analysis and optimization suggestions.
"""
import json
import re
from typing import Dict, Any, Optional, List
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


class AIAnalyzer:
    """
    AI-powered query analyzer.

    This is currently a stub that returns mock responses.
    In production, this would integrate with:
    - OpenAI GPT-4
    - Anthropic Claude
    - Other LLM providers
    """

    def __init__(self, provider: str = "stub", api_key: Optional[str] = None):
        """
        Initialize AI analyzer.

        Args:
            provider: AI provider (stub, openai, anthropic, etc.)
            api_key: API key for the provider
        """
        self.provider = provider
        self.api_key = api_key or settings.ai_api_key

        if self.provider != "stub" and not self.api_key:
            logger.warning(f"AI provider '{provider}' requires API key")
            self.provider = "stub"

        logger.info(f"AI Analyzer initialized with provider: {self.provider}")

    def analyze_query(
        self,
        sql: str,
        explain_plan: Optional[Dict[str, Any]],
        db_type: str,
        duration_ms: float,
        rows_examined: Optional[int] = None,
        rows_returned: Optional[int] = None,
        db_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a query using AI.

        Args:
            sql: SQL query text
            explain_plan: Execution plan (if available)
            db_type: Database type (mysql, postgres)
            duration_ms: Query execution time in milliseconds
            rows_examined: Number of rows examined
            rows_returned: Number of rows returned
            db_context: Detailed database metadata (tables, indexes, stats)

        Returns:
            AI-generated analysis and suggestions
        """
        if self.provider == "stub":
            return self._stub_analysis(sql, explain_plan, db_type, db_context=db_context)
        elif self.provider == "openai":
            return self._openai_analysis(
                sql,
                explain_plan,
                db_type,
                duration_ms=duration_ms,
                rows_examined=rows_examined,
                rows_returned=rows_returned,
                db_context=db_context,
            )
        elif self.provider == "anthropic":
            return self._anthropic_analysis(sql, explain_plan, db_type, db_context=db_context)
        else:
            logger.error(f"Unknown AI provider: {self.provider}")
            return self._stub_analysis(sql, explain_plan, db_type, db_context=db_context)

    def _stub_analysis(
        self,
        sql: str,
        explain_plan: Optional[Dict[str, Any]],
        db_type: str,
        db_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Stub implementation returning mock AI analysis.

        Args:
            sql: SQL query
            explain_plan: Execution plan
            db_type: Database type
            db_context: Database metadata context

        Returns:
            Mock analysis results
        """
        logger.debug("Using stub AI analysis for %s query", db_type)

        sql_variants = _generate_query_variant_recommendations(
            sql=sql,
            existing_sqls=set(),
            needed=3,
            default_priority="HIGH",
        )

        recommendations = sql_variants + [
            {
                "type": "MONITORING",
                "priority": "LOW",
                "description": "Track execution metrics before and after applying query variants.",
                "sql": None,
                "estimated_impact": "Validates improvements and prevents regressions.",
                "rationale": "Ongoing monitoring ensures changes deliver expected gains.",
            },
        ]

        return {
            "summary": "Likely missing composite index and over-selecting columns.",
            "root_cause": "The query performs a wide scan due to absent covering indexes and broad projections.",
            "recommendations": recommendations,
            "improvement_level": "MEDIUM",
            "estimated_speedup": "2-5x",
            "confidence": 0.75,
            "provider": "stub",
            "model": "mock-v1",
            "metadata": {
                "notes": "Stubbed response — replace with real provider output.",
                "db_context_excerpt": list(db_context or {})[:3],
            },
        }

    def _openai_analysis(
        self,
        sql: str,
        explain_plan: Optional[Dict[str, Any]],
        db_type: str,
        duration_ms: float = 0,
        rows_examined: Optional[int] = None,
        rows_returned: Optional[int] = None,
        db_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        OpenAI GPT-4 analysis implementation.

        Args:
            sql: SQL query
            explain_plan: Execution plan
            db_type: Database type
            duration_ms: Query execution time
            rows_examined: Rows scanned
            rows_returned: Rows returned

        Returns:
            OpenAI analysis results
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            model_name = getattr(settings, "ai_model", "gpt-4o-mini")

            ratio = "unknown"
            if rows_examined and rows_returned:
                ratio = f"{rows_examined / max(rows_returned, 1):.1f}:1"

            rows_examined_str = f"{rows_examined:,}" if rows_examined is not None else "unknown"
            rows_returned_str = f"{rows_returned:,}" if rows_returned is not None else "unknown"
            context_blob = self._format_db_context(db_type, db_context or {})
            explain_plan_blob = json.dumps(explain_plan, indent=2) if explain_plan else "Not available"

            system_prompt = """
                You are a senior database performance engineer.

                Your task: given a SQL query and its execution plan, determine if it can be optimized.
                You must only propose **real, equivalent optimizations** that maintain the exact same logical result and use valid SQL syntax for the provided database type.

                Respond with RAW JSON ONLY (no markdown, no prose), following this schema:
                {
                "summary": "Short factual summary of what was found",
                "root_cause": "If slow, explain why (e.g. missing index, subquery, function on column, large scan)",
                "recommendations": [
                    {
                    "type": "QUERY_MODIFICATION|INDEX|NO_ACTION",
                    "priority": "LOW|MEDIUM|HIGH|CRITICAL",
                    "description": "What to change and why",
                    "sql": "Optimized query with same semantics, or null if not applicable",
                    "estimated_impact": "Expected speedup or 'None'"
                    }
                ],
                "improvement_level": "LOW|MEDIUM|HIGH|NONE",
                "estimated_speedup": "Text like '2-3x' or 'None'",
                "confidence": 0.0-1.0
                }

                STRICT RULES:
                - If the query cannot be improved without changing semantics, return ONE recommendation of type "NO_ACTION" with a short reason.
                - If optimization is possible, return up to THREE rewritten queries with minor improvements (e.g., removing unnecessary subqueries, adding joins, adding LIMIT, etc.).
                - NEVER propose random, fabricated, or semantically different SQL.
                - NEVER generate fake SELECTs or example data.
                - The returned SQL must be executable on the given DB type without modification.
                - CRITICAL: SQL strings must be on ONE LINE. DO NOT use string concatenation ("+") or line breaks in SQL values.
                - CRITICAL: Return ONLY valid JSON. Do not use string concatenation operators or multiline strings.
                """

            user_prompt = f"""Analyze the following slow query and return RAW JSON that follows the schema and requirements above. Do not add code fences or prose outside the JSON object.\n\nDATABASE: {db_type}\nDURATION: {duration_ms} ms\nROWS EXAMINED: {rows_examined_str}\nROWS RETURNED: {rows_returned_str}\nEFFICIENCY RATIO: {ratio}\n\nDATABASE CONTEXT:\n{context_blob}\n\nSQL QUERY:\n{sql}\n\nEXECUTION PLAN:\n{explain_plan_blob}\n"""

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=2000,
            )

            ai_response = response.choices[0].message.content
            logger.debug("OpenAI response: %s", ai_response)

            import json as json_module

            try:
                parsed = json_module.loads(ai_response)
            except json_module.JSONDecodeError:
                # Attempt to extract JSON block from fenced code
                fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", ai_response, re.DOTALL)
                if fenced_match:
                    sanitized = fenced_match.group(1).strip()
                    try:
                        parsed = json_module.loads(sanitized)
                        ai_response = sanitized  # use sanitized in metadata for traceability
                    except json_module.JSONDecodeError:
                        logger.warning("Failed to parse sanitized OpenAI JSON block")
                        parsed = None
                else:
                    parsed = None

                if parsed is None:
                    logger.warning("Could not parse OpenAI response as JSON, returning fallback payload")
                    return {
                        "summary": ai_response[:200],
                        "root_cause": "AI response was not valid JSON.",
                        "recommendations": [],
                        "improvement_level": "LOW",
                        "estimated_speedup": "unknown",
                        "confidence": 0.5,
                        "provider": "openai",
                        "model": model_name,
                        "metadata": {
                            "raw_response": ai_response,
                            "prompt_context_length": len(context_blob),
                        },
                    }

            normalized_recommendations = []
            for rec in parsed.get("recommendations", []):
                normalized_recommendations.append(
                    {
                        "type": rec.get("type") or "QUERY_MODIFICATION",
                        "priority": rec.get("priority") or "HIGH",
                        "description": rec.get("description"),
                        "sql": _ensure_semicolon(rec.get("sql")) if rec.get("sql") else None,
                        "estimated_impact": rec.get("estimated_impact"),
                        "rationale": rec.get("rationale"),
                    }
                )

            existing_sqls: set[str] = {
                (rec.get("sql") or "").strip()
                for rec in normalized_recommendations
                if rec.get("sql")
            }

            existing_sql_count = sum(1 for sql_text in existing_sqls if sql_text)

            if existing_sql_count < 3:
                needed = 3 - existing_sql_count
                normalized_recommendations.extend(
                    _generate_query_variant_recommendations(
                        sql=sql,
                        existing_sqls=existing_sqls,
                        needed=needed,
                    )
                )

            return {
                "summary": parsed.get("summary", ""),
                "root_cause": parsed.get("root_cause", ""),
                "recommendations": normalized_recommendations,
                "improvement_level": parsed.get("improvement_level"),
                "estimated_speedup": parsed.get("estimated_speedup"),
                "confidence": parsed.get("confidence"),
                "provider": "openai",
                "model": model_name,
                "metadata": {
                    "prompt_context_length": len(context_blob),
                    "explain_plan_present": bool(explain_plan),
                },
                "provider_response": {
                    "id": getattr(response, "id", None),
                    "model": response.model,
                },
            }

        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return self._stub_analysis(sql, explain_plan, db_type, db_context=db_context)
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            return self._stub_analysis(sql, explain_plan, db_type, db_context=db_context)

    def _anthropic_analysis(
        self,
        sql: str,
        explain_plan: Optional[Dict[str, Any]],
        db_type: str,
        db_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Anthropic Claude analysis implementation (placeholder).

        In production, this would:
        1. Format query and plan for Claude
        2. Call Anthropic API
        3. Parse and structure the response

        Args:
            sql: SQL query
            explain_plan: Execution plan
            db_type: Database type

        Returns:
            Claude analysis results
        """
        logger.info("Anthropic analysis not yet implemented, using stub")

        # TODO: Implement Anthropic integration
        # from anthropic import Anthropic
        # client = Anthropic(api_key=self.api_key)
        # response = client.messages.create(
        #     model="claude-3-sonnet-20240229",
        #     max_tokens=1024,
        #     messages=[
        #         {"role": "user", "content": f"Analyze this SQL query: {sql}"}
        #     ]
        # )

        return self._stub_analysis(sql, explain_plan, db_type, db_context=db_context)

    def enhance_analysis(
        self,
        rule_based_analysis: Dict[str, Any],
        sql: str,
        explain_plan: Optional[Dict[str, Any]],
        db_type: str,
        duration_ms: float = 0,
        rows_examined: Optional[int] = None,
        rows_returned: Optional[int] = None,
        db_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enhance rule-based analysis with AI insights.

        Combines static analysis with AI-generated suggestions
        for a more comprehensive analysis.

        Args:
            rule_based_analysis: Results from rule-based analyzer
            sql: SQL query
            explain_plan: Execution plan
            db_type: Database type
            duration_ms: Query execution time
            rows_examined: Rows scanned
            rows_returned: Rows returned
            db_context: Database metadata context

        Returns:
            Enhanced analysis with AI insights
        """
        # Get AI analysis with all context
        ai_result = self.analyze_query(
            sql=sql,
            explain_plan=explain_plan,
            db_type=db_type,
            duration_ms=duration_ms,
            rows_examined=rows_examined,
            rows_returned=rows_returned,
            db_context=db_context,
        )

        # Merge results
        enhanced = rule_based_analysis.copy()

        # If AI provided direct analysis (root_cause, problem), use it
        if 'root_cause' in ai_result and ai_result['root_cause']:
            enhanced['root_cause'] = ai_result['root_cause']
            enhanced['method'] = 'ai_assisted'

        if 'problem' in ai_result and ai_result['problem']:
            enhanced['problem'] = ai_result['problem']

        if 'suggestions' in ai_result and ai_result['suggestions']:
            # Replace with AI suggestions if they exist
            enhanced['suggestions'] = ai_result['suggestions']

        if 'improvement_level' in ai_result:
            enhanced['improvement_level'] = ai_result['improvement_level']

        if 'estimated_speedup' in ai_result:
            enhanced['estimated_speedup'] = ai_result['estimated_speedup']

        # Add AI insights to metadata
        if 'metadata' not in enhanced:
            enhanced['metadata'] = {}

        enhanced['metadata']['ai_insights'] = ai_result.get('ai_insights', [])
        enhanced['metadata']['ai_provider'] = ai_result.get('provider', 'stub')
        enhanced['metadata']['ai_model'] = ai_result.get('model', 'unknown')

        # Add additional AI suggestions if provided
        if 'additional_suggestions' in ai_result:
            enhanced['suggestions'].extend(ai_result['additional_suggestions'])

        # Update confidence
        ai_confidence = ai_result.get('confidence', 0)
        if ai_confidence > 0:
            enhanced['confidence'] = ai_confidence
            if enhanced.get('method') != 'ai_assisted':
                enhanced['method'] = 'hybrid'

        return enhanced

    def _format_db_context(self, db_type: str, context: Dict[str, Any]) -> str:
        """
        Convert DB metadata into a compact, readable prompt section.
        """
        if not context:
            return "No additional database metadata available."

        lines: List[str] = []
        config = context.get("configuration") or {}
        tables = context.get("tables") or {}
        indexes = context.get("indexes") or {}
        stats = context.get("statistics") or {}
        relations = context.get("relations") or {}

        lines.append(f"DATABASE TYPE: {db_type}")
        if config:
            lines.append("KEY CONFIGURATION:")
            for key, value in config.items():
                lines.append(f"- {key}: {value}")

        for table, columns in tables.items():
            lines.append(f"\nTable: {table}")
            if stats.get(table):
                stat = stats[table]
                est_rows = stat.get("estimated_rows") or stat.get("rows")
                lines.append(f"  Estimated Rows: {est_rows}")
            lines.append("  Columns:")
            for column in columns:
                col_desc = f"{column.get('column')} {column.get('type')}"
                if column.get("nullable") is False:
                    col_desc += " NOT NULL"
                if column.get("default") is not None:
                    col_desc += f" DEFAULT {column.get('default')}"
                lines.append(f"    - {col_desc}")

            if indexes.get(table):
                lines.append("  Indexes:")
                for index in indexes[table]:
                    parts = ", ".join(
                        col.get("column") if isinstance(col, dict) else str(col)
                        for col in index.get("columns", [])
                    )
                    definition = index.get("definition")
                    if definition:
                        lines.append(f"    - {definition}")
                    else:
                        lines.append(f"    - {index.get('name')}: {parts}")

            if relations.get(table):
                lines.append("  Foreign Keys:")
                for rel in relations[table]:
                    lines.append(
                        f"    - {rel.get('constraint')}: "
                        f"{rel.get('columns')} -> "
                        f"{rel.get('referenced_table')}({rel.get('referenced_columns')})"
                    )

        return "\n".join(lines)


def _ensure_semicolon(sql: str) -> str:
    if sql is None:
        return sql
    stripped = sql.rstrip()
    if not stripped:
        return stripped
    if stripped.endswith(";"):
        return stripped
    return stripped + ";"


def _indent_sql(sql: str, indent: str = "    ") -> str:
    return "\n".join(indent + line if line.strip() else line for line in sql.splitlines())


def _build_query_variants(sql: str) -> List[tuple[str, str, str, str]]:
    base = sql.strip()
    if not base:
        return []

    base_no_semicolon = base.rstrip(";")

    variants: List[tuple[str, str, str, str]] = []

    limit_variant = _ensure_semicolon(
        f"{base_no_semicolon}\nLIMIT 100 -- reduce rows scanned during optimisation"
    )
    variants.append(
        (
            limit_variant,
            "Add a LIMIT clause while tuning",
            "Limiting the result set during optimisation reduces buffer usage and highlights index efficiency.",
            "Substantially cuts scanned rows during exploratory tuning runs.",
        )
    )

    projection_candidate = re.sub(
        r"SELECT\s+\*",
        "SELECT /* specify explicit columns */ *",
        base_no_semicolon,
        count=1,
        flags=re.IGNORECASE,
    )
    if projection_candidate == base_no_semicolon:
        projection_candidate = re.sub(
            r"SELECT\s+",
            "SELECT /* specify explicit columns */ ",
            base_no_semicolon,
            count=1,
            flags=re.IGNORECASE,
        )
    if projection_candidate == base_no_semicolon:
        projection_candidate = f"/* Narrow projection */\n{base_no_semicolon}"
    projection_variant = _ensure_semicolon(projection_candidate)
    variants.append(
        (
            projection_variant,
            "Limit the projection to required columns",
            "Explicit projections lower I/O and enable covering indexes.",
            "Reduces payload size and CPU spent materialising unused columns.",
        )
    )

    cte_variant_body = _indent_sql(base_no_semicolon)
    cte_variant = (
        "WITH filtered AS (\n"
        f"{cte_variant_body}\n"
        ")\n"
        "SELECT *\n"
        "FROM filtered\n"
        "WHERE /* add selective predicate e.g. status = 'ACTIVE' */ 1 = 1;"
    )
    variants.append(
        (
            cte_variant,
            "Wrap the statement in a CTE and apply additional filters",
            "A CTE makes it easier to stage intermediate results and apply selective predicates.",
            "Improves maintainability and encourages predicate pushdown opportunities.",
        )
    )

    if re.search(r"\bWHERE\b", base_no_semicolon, re.IGNORECASE):
        filtered_variant = re.sub(
            r"\bWHERE\b",
            "WHERE /* tighten predicate, e.g. date >= CURRENT_DATE - INTERVAL '7 days' */",
            base_no_semicolon,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        filtered_variant = f"{base_no_semicolon}\nWHERE /* add selective predicate e.g. status = 'ACTIVE' */"
    filtered_variant = _ensure_semicolon(filtered_variant)
    variants.append(
        (
            filtered_variant,
            "Add highly selective predicates",
            "Targeted filters dramatically reduce the number of rows that need to be scanned.",
            "Improves selectivity and lowers buffer churn.",
        )
    )

    return variants


def _generate_query_variant_recommendations(
    sql: str,
    existing_sqls: set[str],
    needed: int,
    default_priority: str = "MEDIUM",
) -> List[Dict[str, Any]]:
    if needed <= 0:
        return []
    variants: List[Dict[str, Any]] = []
    for variant_sql, description, rationale, impact in _build_query_variants(sql):
        normalized_sql = variant_sql.strip()
        if not normalized_sql or normalized_sql in existing_sqls:
            continue
        variants.append(
            {
                "type": "QUERY_MODIFICATION",
                "priority": default_priority,
                "description": description,
                "sql": variant_sql,
                "estimated_impact": impact,
                "rationale": rationale,
            }
        )
        existing_sqls.add(normalized_sql)
        if len(variants) >= needed:
            break
    return variants


# Factory function
def get_ai_analyzer() -> AIAnalyzer:
    """
    Get AI analyzer instance configured from settings.

    Returns:
        Configured AIAnalyzer instance
    """
    provider = getattr(settings, 'ai_provider', 'stub')
    api_key = getattr(settings, 'ai_api_key', None)

    return AIAnalyzer(provider=provider, api_key=api_key)


# Example usage
if __name__ == "__main__":
    analyzer = get_ai_analyzer()

    result = analyzer.analyze_query(
        sql="SELECT * FROM users WHERE status = 'active'",
        explain_plan=None,
        db_type="mysql",
        duration_ms=1500.0
    )

    print("AI Analysis Result:")
    print(f"  Provider: {result.get('provider')}")
    print(f"  Confidence: {result.get('confidence')}")
    print(f"  Insights: {result.get('ai_insights')}")
