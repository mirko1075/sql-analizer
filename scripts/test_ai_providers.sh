#!/bin/bash
# Test AI Provider System
# Tests all three providers (LLaMA, OpenAI, Anthropic) with health checks

set -e

echo "================================================"
echo "AI Provider System Test"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test SQL query
TEST_QUERY="SELECT * FROM users WHERE email LIKE '%@gmail.com' AND created_at > '2024-01-01'"

# Function to test a provider
test_provider() {
    local provider=$1
    local api_key_var=$2
    
    echo -e "${YELLOW}Testing $provider provider...${NC}"
    
    # Set environment variable
    export AI_PROVIDER=$provider
    
    # Check if API key is required and present
    if [ ! -z "$api_key_var" ]; then
        if [ -z "${!api_key_var}" ]; then
            echo -e "${RED}  ✗ Skipped: $api_key_var not set${NC}"
            return 1
        fi
    fi
    
    # Run Python test
    python3 - <<EOF
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, '/app')

from services.ai import get_ai_provider, check_provider_health, AIAnalysisRequest

async def test():
    try:
        # Health check
        print("  Checking provider health...")
        healthy = await check_provider_health()
        
        if not healthy:
            print("  ✗ Provider health check failed")
            return False
        
        print("  ✓ Provider is healthy")
        
        # Test analysis
        print("  Running test query analysis...")
        provider = get_ai_provider()
        
        request = AIAnalysisRequest(
            sql_query="$TEST_QUERY",
            explain_plan="type: ALL, rows: 100000, key: NULL",
            schema_info={"users": {"columns": ["id", "email", "created_at"]}},
            table_stats={"query_time": 5.2, "rows_examined": 100000, "rows_sent": 50},
        )
        
        response = await provider.analyze_query(request)
        
        if response.error:
            print(f"  ✗ Analysis failed: {response.error}")
            return False
        
        print(f"  ✓ Analysis successful")
        print(f"    Provider: {response.provider}")
        print(f"    Model: {response.model}")
        print(f"    Duration: {response.duration_ms:.2f}ms")
        print(f"    Tokens: {response.tokens_used or 'N/A'}")
        print(f"    Analysis length: {len(response.analysis)} chars")
        
        # Show first 200 chars of analysis
        preview = response.analysis[:200] + "..." if len(response.analysis) > 200 else response.analysis
        print(f"    Preview: {preview}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run test
result = asyncio.run(test())
sys.exit(0 if result else 1)
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ $provider test passed${NC}"
        return 0
    else
        echo -e "${RED}  ✗ $provider test failed${NC}"
        return 1
    fi
}

# Change to backend directory
cd /app

# Load environment variables
if [ -f ../.env ]; then
    export $(grep -v '^#' ../.env | xargs)
fi

echo "Current AI_PROVIDER: ${AI_PROVIDER:-llama}"
echo ""

# Test each provider
echo "================================================"
echo "1. Testing LLaMA Provider (Local)"
echo "================================================"
test_provider "llama" ""
LLAMA_RESULT=$?
echo ""

echo "================================================"
echo "2. Testing OpenAI Provider (Cloud)"
echo "================================================"
test_provider "openai" "OPENAI_API_KEY"
OPENAI_RESULT=$?
echo ""

echo "================================================"
echo "3. Testing Anthropic Provider (Cloud)"
echo "================================================"
test_provider "anthropic" "ANTHROPIC_API_KEY"
ANTHROPIC_RESULT=$?
echo ""

# Summary
echo "================================================"
echo "Test Summary"
echo "================================================"
echo -e "LLaMA:     $([ $LLAMA_RESULT -eq 0 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo -e "OpenAI:    $([ $OPENAI_RESULT -eq 0 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${YELLOW}⊘ SKIPPED${NC}")"
echo -e "Anthropic: $([ $ANTHROPIC_RESULT -eq 0 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${YELLOW}⊘ SKIPPED${NC}")"
echo ""

# Overall result
if [ $LLAMA_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Core functionality working (LLaMA provider operational)${NC}"
    exit 0
else
    echo -e "${RED}✗ Core functionality broken (LLaMA provider failed)${NC}"
    exit 1
fi
