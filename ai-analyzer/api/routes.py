"""
FastAPI routes for AI Analyzer service.
"""
import time
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
import asyncio

from models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    HealthResponse
)
from analyzer.factory import get_analyzer
from config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()

# Service start time for uptime calculation
service_start_time = time.time()


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key from request header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        Validated API key

    Raises:
        HTTPException: If authentication is required and key is invalid
    """
    config = get_config()

    if not config.require_authentication:
        return "no-auth-required"

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header."
        )

    if x_api_key not in config.allowed_api_keys:
        logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return x_api_key


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and configuration.
    """
    config = get_config()
    uptime = time.time() - service_start_time

    return HealthResponse(
        status="healthy",
        service=config.service_name,
        version="1.0.0",
        model_provider=config.model.provider.value,
        model_name=config.model.model_name,
        uptime_seconds=uptime
    )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_query(
    request: AnalysisRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Analyze single SQL query for performance issues.

    Args:
        request: Analysis request with SQL query and metadata
        api_key: Validated API key

    Returns:
        Analysis response with issues and suggestions

    Raises:
        HTTPException: If analysis fails
    """
    try:
        config = get_config()

        # Validate query length
        if len(request.sql_query) > config.max_query_length:
            raise HTTPException(
                status_code=400,
                detail=f"Query too long. Maximum length: {config.max_query_length}"
            )

        # Log request (if enabled and privacy-safe)
        if config.log_queries:
            logger.info(f"Analyzing query: {request.sql_query[:100]}...")
        else:
            logger.info("Analyzing query (content not logged for privacy)")

        # Get analyzer and perform analysis
        analyzer = get_analyzer()
        result = analyzer.analyze(request)

        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def analyze_batch(
    request: BatchAnalysisRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Analyze multiple SQL queries in batch.

    Args:
        request: Batch analysis request
        api_key: Validated API key

    Returns:
        Batch analysis response

    Raises:
        HTTPException: If batch analysis fails
    """
    start_time = time.time()

    try:
        logger.info(f"Analyzing batch of {len(request.queries)} queries")

        analyzer = get_analyzer()
        results: List[AnalysisResponse] = []
        errors: List[dict] = []

        if request.parallel:
            # Process queries in parallel (with asyncio)
            tasks = []
            for idx, query_request in enumerate(request.queries):
                task = analyze_single_async(analyzer, query_request, idx)
                tasks.append(task)

            completed_results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(completed_results):
                if isinstance(result, Exception):
                    errors.append({
                        "query_index": idx,
                        "error": str(result)
                    })
                else:
                    results.append(result)
        else:
            # Process queries sequentially
            for idx, query_request in enumerate(request.queries):
                try:
                    result = analyzer.analyze(query_request)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Query {idx} analysis failed: {e}")
                    errors.append({
                        "query_index": idx,
                        "error": str(e)
                    })

        total_time_ms = (time.time() - start_time) * 1000

        return BatchAnalysisResponse(
            total_queries=len(request.queries),
            successful=len(results),
            failed=len(errors),
            results=results,
            errors=errors,
            total_analysis_time_ms=total_time_ms
        )

    except Exception as e:
        logger.error(f"Batch analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch analysis failed: {str(e)}"
        )


async def analyze_single_async(analyzer, request: AnalysisRequest, index: int) -> AnalysisResponse:
    """
    Analyze single query asynchronously.

    Args:
        analyzer: Analyzer instance
        request: Analysis request
        index: Query index for logging

    Returns:
        Analysis response

    Raises:
        Exception: If analysis fails
    """
    try:
        # Run blocking analyzer.analyze in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyzer.analyze, request)
        return result
    except Exception as e:
        logger.error(f"Query {index} analysis failed: {e}")
        raise


@router.get("/stats")
async def get_statistics(api_key: str = Depends(verify_api_key)):
    """
    Get analyzer statistics.

    Returns:
        Statistics including total analyses, issues found, average time
    """
    try:
        analyzer = get_analyzer()
        stats = analyzer.get_stats()

        return JSONResponse(content={
            "status": "success",
            "statistics": stats
        })

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats/reset")
async def reset_statistics(api_key: str = Depends(verify_api_key)):
    """
    Reset analyzer statistics.

    Returns:
        Success message
    """
    try:
        analyzer = get_analyzer()
        analyzer.reset_stats()

        return JSONResponse(content={
            "status": "success",
            "message": "Statistics reset successfully"
        })

    except Exception as e:
        logger.error(f"Failed to reset statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
