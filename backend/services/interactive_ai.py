"""
Interactive AI Analyzer with DB Query Capability.
AI can request data from DB before providing analysis.
"""
import json
import re
import mysql.connector
from typing import Dict, Any, List, Optional
import logging

from core.config import settings
from services.ai import get_ai_provider, AIAnalysisRequest, AIAnalysisResponse

logger = logging.getLogger(__name__)


class InteractiveAIAnalyzer:
    """
    AI analyzer that can request and execute DB queries during analysis.
    Implements a multi-step conversation with the AI.
    """
    
    def __init__(self):
        self.ai_provider = get_ai_provider()
        self.conversation_history = []
        self.db_queries_executed = []
        self.max_iterations = 5  # Prevent infinite loops
        
    async def analyze_with_db_access(
        self,
        sql_query: str,
        explain_plan: Optional[str] = None,
        schema_info: Optional[Dict[str, Any]] = None,
        table_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze query with AI having DB access.
        
        Process:
        1. Send query info to AI
        2. AI responds with analysis OR requests more data
        3. If AI requests data, execute queries and send results back
        4. Repeat until AI provides final analysis
        
        Args:
            sql_query: SQL query to analyze
            explain_plan: EXPLAIN output
            schema_info: Table schema information
            table_stats: Table statistics
            
        Returns:
            Dict with analysis and metadata
        """
        logger.info("🤖 Starting interactive AI analysis with DB access...")
        
        iteration = 0
        final_analysis = None
        
        # Initial prompt
        initial_prompt = self._build_initial_prompt(
            sql_query, explain_plan, schema_info, table_stats
        )
        
        self.conversation_history.append({
            "role": "user",
            "content": initial_prompt
        })
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"🔄 AI Iteration {iteration}/{self.max_iterations}")
            
            # Send to AI
            ai_request = AIAnalysisRequest(
                sql_query=sql_query,
                explain_plan=explain_plan,
                schema_info=schema_info,
                table_stats=table_stats
            )
            
            # Build conversation prompt
            conversation_prompt = self._build_conversation_prompt()
            ai_request.sql_query = conversation_prompt  # Override with full conversation
            
            response = await self.ai_provider.analyze_query(ai_request)
            
            if response.error:
                logger.error(f"AI error: {response.error}")
                return {
                    "success": False,
                    "error": response.error,
                    "iterations": iteration
                }
            
            logger.info(f"📥 AI Response received ({len(response.analysis)} chars)")
            
            # Add AI response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response.analysis
            })
            
            # Check if AI is requesting DB queries
            db_requests = self._extract_db_requests(response.analysis)
            
            if db_requests:
                logger.info(f"🗄️  AI requested {len(db_requests)} database queries")
                
                # Execute requested queries
                query_results = await self._execute_db_requests(db_requests)
                
                # Send results back to AI
                results_message = self._format_query_results(query_results)
                self.conversation_history.append({
                    "role": "user",
                    "content": results_message
                })
                
                logger.info(f"✅ Sent query results back to AI")
                
            else:
                # No more queries requested - this is the final analysis
                logger.info("✅ AI provided final analysis")
                final_analysis = response.analysis
                break
        
        if not final_analysis:
            logger.warning(f"⚠️  Max iterations ({self.max_iterations}) reached")
            final_analysis = self.conversation_history[-1]["content"] if self.conversation_history else "Analysis incomplete"
        
        return {
            "success": True,
            "analysis": final_analysis,
            "iterations": iteration,
            "db_queries_executed": len(self.db_queries_executed),
            "conversation_history": self.conversation_history,
            "provider": response.provider,
            "model": response.model,
            "total_tokens": response.tokens_used,
            "total_duration_ms": response.duration_ms
        }
    
    def _build_initial_prompt(
        self,
        sql_query: str,
        explain_plan: Optional[str],
        schema_info: Optional[Dict[str, Any]],
        table_stats: Optional[Dict[str, Any]]
    ) -> str:
        """Build the initial prompt for AI."""
        
        prompt = """You are a MySQL performance expert with DATABASE QUERY ACCESS.

Your task is to analyze this slow query and provide optimization recommendations.

IMPORTANT: You can request additional data from the database to aid your analysis.

To request data, use this format:
```sql
-- Request: [Brief description of why you need this data]
SELECT ...
```

You can request:
- Table statistics (SELECT COUNT(*), AVG(column), etc.)
- Index information (SHOW INDEXES FROM table)
- Sample data (SELECT * FROM table LIMIT 10)
- Distribution analysis (SELECT column, COUNT(*) GROUP BY column)
- Foreign key relationships
- Any other query that helps you understand the problem

I will execute your queries and send the results back to you.

Once you have all the information you need, provide your final analysis with:
1. Root cause of performance issue
2. Specific optimization recommendations
3. Expected performance improvement
4. Priority level (CRITICAL/HIGH/MEDIUM/LOW)

---

**QUERY TO ANALYZE:**
```sql
{}
```
""".format(sql_query)
        
        if explain_plan:
            prompt += f"\n**EXPLAIN PLAN:**\n```\n{explain_plan}\n```\n"
        
        if schema_info:
            prompt += f"\n**SCHEMA INFO:**\n```\n{json.dumps(schema_info, indent=2)}\n```\n"
        
        if table_stats:
            prompt += f"\n**QUERY STATS:**\n```\n{json.dumps(table_stats, indent=2)}\n```\n"
        
        prompt += "\n\nWhat additional information do you need from the database? Or provide your analysis if you have enough information."
        
        return prompt
    
    def _build_conversation_prompt(self) -> str:
        """Build full conversation for AI context."""
        messages = []
        for msg in self.conversation_history:
            role_label = "USER" if msg["role"] == "user" else "ASSISTANT"
            messages.append(f"[{role_label}]\n{msg['content']}\n")
        
        return "\n---\n\n".join(messages)
    
    def _extract_db_requests(self, ai_response: str) -> List[Dict[str, str]]:
        """
        Extract DB query requests from AI response.
        
        Looks for SQL blocks with comments indicating requests.
        
        Returns:
            List of dicts with 'query' and 'reason' keys
        """
        requests = []
        
        # Pattern: ```sql ... ```
        sql_blocks = re.findall(r'```sql\s*(.*?)\s*```', ai_response, re.DOTALL | re.IGNORECASE)
        
        for block in sql_blocks:
            # Check if this is a request (not an example/suggestion)
            if '-- Request:' in block or '-- EXECUTE:' in block:
                # Extract reason
                reason_match = re.search(r'--\s*(?:Request|EXECUTE):\s*(.+)', block)
                reason = reason_match.group(1).strip() if reason_match else "Additional data needed"
                
                # Clean up query (remove comments)
                query_lines = []
                for line in block.split('\n'):
                    if not line.strip().startswith('--'):
                        query_lines.append(line)
                
                query = '\n'.join(query_lines).strip()
                
                if query:
                    requests.append({
                        'query': query,
                        'reason': reason
                    })
                    logger.info(f"📋 Extracted query request: {reason}")
        
        return requests
    
    async def _execute_db_requests(self, requests: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Execute DB queries requested by AI.
        
        Safety checks:
        - Only allow SELECT and SHOW queries
        - Limit result set size
        - Add timeout
        
        Returns:
            List of query results
        """
        results = []
        
        conn = None
        try:
            # Use monitoring user for safety
            conn = mysql.connector.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.dbpower_user,
                password=settings.dbpower_password,
                database=settings.mysql_db if settings.mysql_db else None,
                connection_timeout=10
            )
            
            cursor = conn.cursor(dictionary=True)
            
            for req in requests:
                query = req['query']
                reason = req['reason']
                
                # Safety check: only SELECT and SHOW
                query_upper = query.upper().strip()
                if not (query_upper.startswith('SELECT') or query_upper.startswith('SHOW') or query_upper.startswith('EXPLAIN')):
                    logger.warning(f"⚠️  Rejected unsafe query: {query[:50]}")
                    results.append({
                        'query': query,
                        'reason': reason,
                        'error': 'Only SELECT and SHOW queries are allowed',
                        'rows': []
                    })
                    continue
                
                try:
                    logger.info(f"🗄️  Executing: {query[:100]}")
                    
                    # Add LIMIT if not present (safety)
                    if 'LIMIT' not in query_upper and query_upper.startswith('SELECT'):
                        query += ' LIMIT 1000'
                    
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    
                    logger.info(f"✅ Query returned {len(rows)} rows")
                    
                    # Log execution
                    self.db_queries_executed.append({
                        'query': query,
                        'reason': reason,
                        'rows_returned': len(rows),
                        'success': True
                    })
                    
                    results.append({
                        'query': query,
                        'reason': reason,
                        'rows': rows,
                        'row_count': len(rows)
                    })
                    
                except mysql.connector.Error as e:
                    logger.error(f"❌ Query error: {e}")
                    self.db_queries_executed.append({
                        'query': query,
                        'reason': reason,
                        'error': str(e),
                        'success': False
                    })
                    
                    results.append({
                        'query': query,
                        'reason': reason,
                        'error': str(e),
                        'rows': []
                    })
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"❌ DB connection error: {e}")
            for req in requests:
                results.append({
                    'query': req['query'],
                    'reason': req['reason'],
                    'error': f'DB connection failed: {str(e)}',
                    'rows': []
                })
        
        finally:
            if conn:
                conn.close()
        
        return results
    
    def _format_query_results(self, results: List[Dict[str, Any]]) -> str:
        """Format query results for sending back to AI."""
        
        message = "**DATABASE QUERY RESULTS:**\n\n"
        
        for i, result in enumerate(results, 1):
            message += f"**Query {i}:** {result['reason']}\n"
            message += f"```sql\n{result['query']}\n```\n\n"
            
            if 'error' in result:
                message += f"❌ **Error:** {result['error']}\n\n"
            else:
                rows = result.get('rows', [])
                row_count = result.get('row_count', 0)
                
                message += f"**Rows returned:** {row_count}\n\n"
                
                if rows:
                    # Format as table (first 10 rows)
                    sample_rows = rows[:10]
                    
                    message += "**Results:**\n```\n"
                    message += json.dumps(sample_rows, indent=2, default=str)
                    message += "\n```\n"
                    
                    if len(rows) > 10:
                        message += f"\n_(Showing first 10 of {len(rows)} rows)_\n"
                else:
                    message += "_(No rows returned)_\n"
            
            message += "\n---\n\n"
        
        message += "\nBased on these results, please provide your final analysis and recommendations."
        
        return message


async def analyze_query_interactive(
    sql_query: str,
    explain_plan: Optional[str] = None,
    schema_info: Optional[Dict[str, Any]] = None,
    table_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function for interactive AI analysis.
    
    Returns:
        Dict with analysis results and metadata
    """
    analyzer = InteractiveAIAnalyzer()
    return await analyzer.analyze_with_db_access(
        sql_query=sql_query,
        explain_plan=explain_plan,
        schema_info=schema_info,
        table_stats=table_stats
    )
