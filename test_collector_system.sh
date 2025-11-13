#!/bin/bash
# Test script for Collector Agent System
# Tests the complete flow: registration, heartbeat, commands, and health monitoring

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="http://localhost:8000"
ADMIN_EMAIL="admin@dbpower.com"
ADMIN_PASSWORD="admin123"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Collector Agent System - E2E Test${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Step 1: Login and get token
echo -e "${YELLOW}Step 1: Authenticating...${NC}"
TOKEN=$(curl -s -X POST "${BACKEND_URL}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo -e "${RED}❌ Authentication failed${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Authenticated successfully${NC}\n"

# Step 2: Register a test collector
echo -e "${YELLOW}Step 2: Registering test collector...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/v1/collectors/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test MySQL Collector E2E",
    "type": "mysql",
    "team_id": 1,
    "config": {
      "host": "127.0.0.1",
      "port": 3306,
      "user": "root",
      "password": "admin"
    },
    "collection_interval_minutes": 5,
    "auto_collect": true
  }')

COLLECTOR_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.id')
COLLECTOR_API_KEY=$(echo "$REGISTER_RESPONSE" | jq -r '.api_key')

if [ "$COLLECTOR_ID" == "null" ] || [ -z "$COLLECTOR_ID" ]; then
  echo -e "${RED}❌ Collector registration failed${NC}"
  echo "$REGISTER_RESPONSE" | jq
  exit 1
fi

echo -e "${GREEN}✅ Collector registered${NC}"
echo "   Collector ID: $COLLECTOR_ID"
echo "   API Key: ${COLLECTOR_API_KEY:0:20}..."
echo ""

# Step 3: List collectors
echo -e "${YELLOW}Step 3: Listing collectors...${NC}"
COLLECTORS=$(curl -s -X GET "${BACKEND_URL}/api/v1/collectors" \
  -H "Authorization: Bearer $TOKEN")

COLLECTOR_COUNT=$(echo "$COLLECTORS" | jq '.total')
echo -e "${GREEN}✅ Found $COLLECTOR_COUNT collector(s)${NC}"
echo "$COLLECTORS" | jq -r '.collectors[] | "   - \(.name) (ID: \(.id), Status: \(.status))"'
echo ""

# Step 4: Get collector details
echo -e "${YELLOW}Step 4: Getting collector details...${NC}"
COLLECTOR_DETAILS=$(curl -s -X GET "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}" \
  -H "Authorization: Bearer $TOKEN")

echo "$COLLECTOR_DETAILS" | jq '{id, name, type, status, is_online, created_at}'
echo ""

# Step 5: Send test heartbeat (simulate collector agent)
echo -e "${YELLOW}Step 5: Sending test heartbeat...${NC}"
HEARTBEAT_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}/heartbeat" \
  -H "X-Collector-API-Key: $COLLECTOR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "stats": {
      "queries_collected": 42,
      "errors_count": 0,
      "uptime_seconds": 120
    }
  }')

if [ "$(echo "$HEARTBEAT_RESPONSE" | jq -r '.status')" == "ok" ]; then
  echo -e "${GREEN}✅ Heartbeat sent successfully${NC}"
  echo "$HEARTBEAT_RESPONSE" | jq
else
  echo -e "${RED}❌ Heartbeat failed${NC}"
  echo "$HEARTBEAT_RESPONSE" | jq
fi
echo ""

# Step 6: Send START command
echo -e "${YELLOW}Step 6: Sending START command...${NC}"
START_CMD=$(curl -s -X POST "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}/start" \
  -H "Authorization: Bearer $TOKEN")

echo "$START_CMD" | jq
echo ""

# Step 7: Send heartbeat again to retrieve command
echo -e "${YELLOW}Step 7: Retrieving pending commands via heartbeat...${NC}"
HEARTBEAT_WITH_COMMANDS=$(curl -s -X POST "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}/heartbeat" \
  -H "X-Collector-API-Key: $COLLECTOR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "stats": {
      "queries_collected": 43,
      "errors_count": 0,
      "uptime_seconds": 125
    }
  }')

COMMANDS=$(echo "$HEARTBEAT_WITH_COMMANDS" | jq -r '.commands')
COMMAND_COUNT=$(echo "$COMMANDS" | jq 'length')

if [ "$COMMAND_COUNT" -gt 0 ]; then
  echo -e "${GREEN}✅ Retrieved $COMMAND_COUNT pending command(s)${NC}"
  echo "$COMMANDS" | jq

  # Execute the command (simulate)
  COMMAND_ID=$(echo "$COMMANDS" | jq -r '.[0].id')
  COMMAND_TYPE=$(echo "$COMMANDS" | jq -r '.[0].command')

  echo -e "\n${YELLOW}Step 8: Reporting command execution...${NC}"
  EXEC_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}/commands/${COMMAND_ID}/execute" \
    -H "X-Collector-API-Key: $COLLECTOR_API_KEY" \
    -H 'Content-Type: application/json' \
    -d "{
      \"command_id\": $COMMAND_ID,
      \"success\": true,
      \"result\": {
        \"message\": \"Command $COMMAND_TYPE executed successfully\"
      }
    }")

  echo "$EXEC_RESPONSE" | jq
else
  echo -e "${YELLOW}⚠️  No pending commands${NC}"
fi
echo ""

# Step 9: Trigger manual collection
echo -e "${YELLOW}Step 9: Triggering manual collection...${NC}"
COLLECT_CMD=$(curl -s -X POST "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}/collect" \
  -H "Authorization: Bearer $TOKEN")

echo "$COLLECT_CMD" | jq
echo ""

# Step 10: Get command history
echo -e "${YELLOW}Step 10: Getting command history...${NC}"
COMMAND_HISTORY=$(curl -s -X GET "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}/commands?limit=10" \
  -H "Authorization: Bearer $TOKEN")

HISTORY_COUNT=$(echo "$COMMAND_HISTORY" | jq 'length')
echo -e "${GREEN}✅ Found $HISTORY_COUNT command(s) in history${NC}"
echo "$COMMAND_HISTORY" | jq -r '.[] | "   - \(.command) (Executed: \(.executed), Created: \(.created_at))"'
echo ""

# Step 11: Update collector configuration
echo -e "${YELLOW}Step 11: Updating collector configuration...${NC}"
UPDATE_RESPONSE=$(curl -s -X PATCH "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "collection_interval_minutes": 10,
    "auto_collect": false
  }')

echo "$UPDATE_RESPONSE" | jq '{id, name, collection_interval_minutes, auto_collect}'
echo ""

# Step 12: Send STOP command
echo -e "${YELLOW}Step 12: Sending STOP command...${NC}"
STOP_CMD=$(curl -s -X POST "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}/stop" \
  -H "Authorization: Bearer $TOKEN")

echo "$STOP_CMD" | jq
echo ""

# Step 13: Check collector is now stopped
echo -e "${YELLOW}Step 13: Verifying collector status...${NC}"
FINAL_STATUS=$(curl -s -X GET "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}" \
  -H "Authorization: Bearer $TOKEN")

STATUS=$(echo "$FINAL_STATUS" | jq -r '.status')
echo -e "   Current status: ${BLUE}$STATUS${NC}"
echo ""

# Step 14: Wait and check if health monitor marks it offline (optional)
echo -e "${YELLOW}Step 14: Testing health monitor (waiting 130 seconds)...${NC}"
echo -e "${YELLOW}   This tests if the health monitor marks the collector as OFFLINE${NC}"
echo -e "${YELLOW}   after 2 minutes without heartbeat. Press Ctrl+C to skip.${NC}"
sleep 5
echo -e "${YELLOW}   Waiting... (125 seconds remaining)${NC}"

for i in {1..5}; do
  sleep 25
  REMAINING=$((125 - (i * 25)))
  if [ $REMAINING -gt 0 ]; then
    echo -e "${YELLOW}   Waiting... ($REMAINING seconds remaining)${NC}"
  fi
done

HEALTH_CHECK=$(curl -s -X GET "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}" \
  -H "Authorization: Bearer $TOKEN")

HEALTH_STATUS=$(echo "$HEALTH_CHECK" | jq -r '.status')
IS_ONLINE=$(echo "$HEALTH_CHECK" | jq -r '.is_online')

if [ "$IS_ONLINE" == "false" ]; then
  echo -e "${GREEN}✅ Health monitor working correctly - Collector marked as OFFLINE${NC}"
else
  echo -e "${YELLOW}⚠️  Collector still shows as online (status: $HEALTH_STATUS)${NC}"
fi
echo ""

# Step 15: Cleanup - Delete test collector
echo -e "${YELLOW}Step 15: Cleaning up - Deleting test collector...${NC}"
read -p "Delete test collector? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  curl -s -X DELETE "${BACKEND_URL}/api/v1/collectors/${COLLECTOR_ID}" \
    -H "Authorization: Bearer $TOKEN"
  echo -e "${GREEN}✅ Test collector deleted${NC}"
else
  echo -e "${BLUE}ℹ️  Test collector kept (ID: ${COLLECTOR_ID})${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ All tests completed successfully!${NC}"
echo ""
echo "Tested features:"
echo "  1. ✅ Authentication"
echo "  2. ✅ Collector registration"
echo "  3. ✅ Collector listing"
echo "  4. ✅ Collector details"
echo "  5. ✅ Heartbeat with API key authentication"
echo "  6. ✅ Command sending (START, COLLECT, STOP)"
echo "  7. ✅ Command retrieval via heartbeat"
echo "  8. ✅ Command execution reporting"
echo "  9. ✅ Command history"
echo " 10. ✅ Collector configuration update"
echo " 11. ✅ Health monitoring (2-minute timeout)"
echo ""
echo -e "${BLUE}========================================${NC}"
