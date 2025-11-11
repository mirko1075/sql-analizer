# Quick Start Guide - AI Provider Selection

## Current Status

✅ **System is fully operational with LLaMA (local AI)**

```bash
# Check current configuration
curl http://localhost:8000/health | jq '.ai'
```

**Output:**
```json
{
  "provider": "llama",
  "status": "healthy",
  "model": "llama3.1:8b",
  "privacy": "local"
}
```

---

## Switching AI Providers

### Option 1: LLaMA (Default - 100% Private)

**Privacy:** ✅ 100% Local - No data leaves your network  
**Cost:** Free  
**Quality:** Good

```bash
# Already configured! No changes needed.
# Or explicitly set:
echo "AI_PROVIDER=llama" >> .env
docker compose restart backend
```

**Verify:**
```bash
docker compose logs backend | grep "AI Provider"
# Should show: ✅ AI Provider LLaMA is healthy
#              Privacy: 🔒 100% Local
```

---

### Option 2: OpenAI (Best Quality)

**Privacy:** ⚠️ SQL queries sent to OpenAI servers  
**Cost:** ~$0.05 per query  
**Quality:** Excellent

**Step 1:** Get API key from https://platform.openai.com/api-keys

**Step 2:** Update `.env`:
```bash
# Add these lines to .env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

**Step 3:** Restart:
```bash
docker compose restart backend
```

**Step 4:** Check logs for privacy warning:
```bash
docker compose logs backend | grep "PRIVACY WARNING"
```

You should see:
```
⚠️  PRIVACY WARNING: Using OPENAI provider
SQL queries and database schema information will be sent to external APIs
```

---

### Option 3: Anthropic (Balanced)

**Privacy:** ⚠️ SQL queries sent to Anthropic servers  
**Cost:** ~$0.02 per query  
**Quality:** Excellent

**Step 1:** Get API key from https://console.anthropic.com/

**Step 2:** Update `.env`:
```bash
# Add these lines to .env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

**Step 3:** Restart:
```bash
docker compose restart backend
```

---

## Testing Your Provider

### Quick Health Check

```bash
curl http://localhost:8000/health | jq '.ai'
```

### Detailed Status

```bash
curl http://localhost:8000/api/v1/analyzer/status | jq '.ai_service'
```

**Expected output:**
```json
{
  "provider": "llama",
  "status": "healthy",
  "model": "llama3.1:8b",
  "base_url": "http://127.0.0.1:11434",
  "privacy": "local"
}
```

### Run Test Suite

```bash
docker compose exec backend bash -c "cd /app && ./scripts/test_ai_providers.sh"
```

---

## Troubleshooting

### LLaMA Issues

**Problem:** "LLaMA provider unhealthy"

**Solution 1:** Check if Ollama is running
```bash
docker compose ps | grep ai-llama
curl http://localhost:11434/api/tags
```

**Solution 2:** Pull the model
```bash
docker compose exec ai-llama ollama pull llama3.1:8b
docker compose restart backend
```

### OpenAI Issues

**Problem:** "Invalid API key"

**Check API key:**
```bash
docker compose exec backend printenv | grep OPENAI_API_KEY
```

**Verify key format:** Should start with `sk-proj-` or `sk-`

**Test key manually:**
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_KEY"
```

### Anthropic Issues

**Problem:** "Invalid API key"

**Check API key:**
```bash
docker compose exec backend printenv | grep ANTHROPIC_API_KEY
```

**Verify key format:** Should start with `sk-ant-`

---

## Viewing Logs

### All backend logs:
```bash
docker compose logs backend -f
```

### Filter for AI-specific logs:
```bash
docker compose logs backend | grep -E "AI Provider|AI Request|AI Response"
```

### Filter for DB poll logs:
```bash
docker compose logs backend | grep -E "DB Poll|Collection Complete"
```

---

## Privacy Comparison

| What Gets Sent | LLaMA | OpenAI | Anthropic |
|----------------|-------|--------|-----------|
| SQL Query Text | ❌ Stays Local | ✅ Sent to Cloud | ✅ Sent to Cloud |
| Database Schema | ❌ Stays Local | ✅ Sent to Cloud | ✅ Sent to Cloud |
| Table Stats | ❌ Stays Local | ✅ Sent to Cloud | ✅ Sent to Cloud |
| EXPLAIN Plan | ❌ Stays Local | ✅ Sent to Cloud | ✅ Sent to Cloud |

**Recommendation:**
- **Sensitive data?** Use LLaMA
- **Public/test data?** Use OpenAI or Anthropic for better analysis

---

## Cost Estimation

### LLaMA (Local)
- **Per query:** $0.00
- **1000 queries:** $0.00
- **Only cost:** Electricity

### OpenAI
- **Per query:** ~$0.05
- **1000 queries:** ~$50
- **Pricing:** https://openai.com/pricing

### Anthropic
- **Per query:** ~$0.02
- **1000 queries:** ~$20
- **Pricing:** https://www.anthropic.com/pricing

---

## Advanced: Multiple Environments

### Development (use cloud for quality)
```bash
# .env.dev
AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-dev-key
```

### Production (use local for privacy)
```bash
# .env.prod
AI_PROVIDER=llama
LLAMA_BASE_URL=http://127.0.0.1:11434
```

**Switch environments:**
```bash
cp .env.dev .env && docker compose restart backend
cp .env.prod .env && docker compose restart backend
```

---

## Monitoring

### Check what provider is running:
```bash
# Option 1: Via API
curl -s http://localhost:8000/health | jq -r '.ai.provider'

# Option 2: Via logs
docker compose logs backend | grep "AI Provider"
```

### Monitor API calls (when AI_LOG_REQUESTS=true):
```bash
docker compose logs backend -f | grep "AI Request\|AI Response"
```

**Example output:**
```
AI Request | Provider: llama | Model: llama3.1:8b | Query length: 156 chars
AI Response | Provider: llama | Duration: 2345.67ms | Tokens: 2341
```

---

## Summary

**Default Setup (No Changes Needed):**
- ✅ LLaMA provider
- ✅ 100% local, private
- ✅ Free to use
- ✅ Already working

**To Use Cloud Providers:**
1. Get API key from provider
2. Add to `.env` file
3. Restart backend
4. Check logs for privacy warning

**Documentation:**
- Full guide: `docs/AI_PROVIDERS.md`
- Configuration: `.env.example`
- Implementation: `IMPLEMENTATION_SUMMARY.md`

---

**Questions? Check:**
- Health endpoint: `http://localhost:8000/health`
- Status endpoint: `http://localhost:8000/api/v1/analyzer/status`
- Logs: `docker compose logs backend`
