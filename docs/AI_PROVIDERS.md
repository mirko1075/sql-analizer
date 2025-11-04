# AI Provider System Documentation

## Overview

DBPower Base supports multiple AI providers for query analysis. You can choose between local and cloud-based providers depending on your privacy, performance, and cost requirements.

## Supported Providers

### 1. LLaMA (via Ollama) - **Recommended for Privacy**

**Type:** Local inference  
**Privacy:** ✅ 100% Local - No data leaves your network  
**Cost:** Free  
**Performance:** Medium (depends on hardware)

**Configuration:**
```bash
AI_PROVIDER=llama
LLAMA_BASE_URL=http://ai-llama:11434
LLAMA_MODEL=llama3.1:8b
```

**Pros:**
- Complete data privacy
- No API costs
- No rate limits
- Works offline

**Cons:**
- Requires GPU for best performance
- Slower than cloud providers
- Model quality depends on hardware

---

### 2. OpenAI (GPT) - **Best Quality**

**Type:** Cloud API  
**Privacy:** ⚠️ Data sent to external API  
**Cost:** $$$  
**Performance:** High

**Configuration:**
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MAX_TOKENS=2000
```

**Pros:**
- Highest quality analysis
- Fast response times
- No infrastructure needed
- Latest models

**Cons:**
- SQL queries sent to OpenAI servers
- API costs per request
- Requires internet connection
- Rate limits apply

**Privacy Impact:**
- Your SQL queries are sent to `https://api.openai.com`
- Database schema information is transmitted
- Query performance metrics are included
- Data processed in OpenAI's cloud infrastructure

---

### 3. Anthropic (Claude) - **Balanced**

**Type:** Cloud API  
**Privacy:** ⚠️ Data sent to external API  
**Cost:** $$  
**Performance:** High

**Configuration:**
```bash
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-sonnet-20240229
ANTHROPIC_BASE_URL=https://api.anthropic.com/v1
ANTHROPIC_MAX_TOKENS=2000
```

**Pros:**
- High quality analysis
- Good reasoning capabilities
- Competitive pricing
- Strong safety features

**Cons:**
- SQL queries sent to Anthropic servers
- API costs per request
- Requires internet connection
- Rate limits apply

**Privacy Impact:**
- Your SQL queries are sent to `https://api.anthropic.com`
- Database schema information is transmitted
- Query performance metrics are included
- Data processed in Anthropic's cloud infrastructure

---

## Privacy Comparison

| Provider | Data Location | External API | Sensitive Data |
|----------|--------------|--------------|----------------|
| **LLaMA** | 100% Local | ❌ No | ✅ Safe |
| **OpenAI** | Cloud (USA) | ✅ Yes | ⚠️ Transmitted |
| **Anthropic** | Cloud (USA) | ✅ Yes | ⚠️ Transmitted |

### What Data is Sent?

When using cloud providers (OpenAI/Anthropic), the following information is transmitted:

1. **SQL Query Text** - The exact query being analyzed
2. **EXPLAIN Plan** - Query execution plan details
3. **Schema Information** - Table structures and columns
4. **Index Information** - Current indexes on tables
5. **Performance Metrics** - Query time, rows examined, etc.
6. **Lock Information** - Database locking status

**Example of transmitted data:**
```json
{
  "sql_query": "SELECT * FROM users WHERE email LIKE '%@gmail.com'",
  "explain_plan": "type: ALL, rows: 100000, key: NULL",
  "schema_info": {
    "users": {
      "columns": ["id", "email", "password", "created_at"]
    }
  },
  "table_stats": {
    "query_time": 5.2,
    "rows_examined": 100000
  }
}
```

---

## Configuration Guide

### Step 1: Choose Your Provider

Edit `.env` file:

```bash
# For local privacy (recommended)
AI_PROVIDER=llama

# For cloud-based with OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-key-here

# For cloud-based with Anthropic
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Step 2: Configure General Settings

```bash
# Enable/disable request logging
AI_LOG_REQUESTS=true

# Request timeout (seconds)
AI_TIMEOUT=120.0

# Max retry attempts
AI_MAX_RETRIES=3
```

### Step 3: Provider-Specific Configuration

**For LLaMA:**
```bash
LLAMA_BASE_URL=http://ai-llama:11434
LLAMA_MODEL=llama3.1:8b  # or llama3, codellama, etc.
```

**For OpenAI:**
```bash
OPENAI_API_KEY=sk-proj-...           # Required
OPENAI_MODEL=gpt-4-turbo-preview     # or gpt-3.5-turbo, gpt-4, etc.
OPENAI_BASE_URL=https://api.openai.com/v1  # Azure: https://your-resource.openai.azure.com
OPENAI_MAX_TOKENS=2000
```

**For Anthropic:**
```bash
ANTHROPIC_API_KEY=sk-ant-...                    # Required
ANTHROPIC_MODEL=claude-3-sonnet-20240229        # or claude-3-opus, claude-3-haiku
ANTHROPIC_BASE_URL=https://api.anthropic.com/v1
ANTHROPIC_MAX_TOKENS=2000
```

### Step 4: Restart Services

```bash
docker-compose down
docker-compose up -d backend
```

---

## Privacy Warnings

When using cloud providers, you'll see warnings at startup:

```
================================================================================
⚠️  PRIVACY WARNING: Using OPENAI provider
================================================================================
SQL queries and database schema information will be sent to external APIs:
  - OpenAI: https://api.openai.com

This data will be transmitted over the internet and processed by third-party services.
Ensure compliance with your organization's data privacy policies.

For complete privacy, use AI_PROVIDER=llama (100% local processing).
================================================================================
```

---

## Testing Providers

Test all configured providers:

```bash
# From project root
docker-compose exec backend /app/scripts/test_ai_providers.sh
```

Or test individual providers:

```bash
# Test LLaMA
docker-compose exec backend python -c "
import asyncio
from services.ai import check_provider_health
print(asyncio.run(check_provider_health()))
"

# With specific provider
docker-compose exec backend bash -c "
export AI_PROVIDER=openai
python -c '
import asyncio
from services.ai import check_provider_health
print(asyncio.run(check_provider_health()))
'
"
```

---

## Cost Estimation

### Cloud Provider Costs

**OpenAI (GPT-4 Turbo):**
- Input: ~$0.01 per 1K tokens
- Output: ~$0.03 per 1K tokens
- Typical analysis: ~2K input + 1K output = $0.05 per query
- 1000 queries/month ≈ **$50/month**

**Anthropic (Claude 3 Sonnet):**
- Input: ~$0.003 per 1K tokens
- Output: ~$0.015 per 1K tokens
- Typical analysis: ~2K input + 1K output = $0.021 per query
- 1000 queries/month ≈ **$21/month**

**LLaMA (Local):**
- One-time hardware cost (GPU recommended)
- Electricity costs
- No per-query costs
- **$0/month** API fees

---

## Compliance Considerations

### When to Use LLaMA (Local)

✅ Use local provider if:
- Handling sensitive data (PII, financial, healthcare)
- Subject to GDPR, HIPAA, or similar regulations
- Company policy prohibits cloud AI
- Need complete audit trail
- Want zero per-query costs

### When Cloud Providers are Acceptable

✅ Use cloud providers if:
- Analyzing non-sensitive, public schemas
- Organization approves cloud AI usage
- Need highest quality analysis
- Have budget for API costs
- Legal/compliance approved

### Best Practices

1. **Review Data Sensitivity**
   - Audit what queries contain (PII, secrets, etc.)
   - Classify data sensitivity levels
   - Choose provider based on highest sensitivity

2. **Compliance Check**
   - Verify with legal/compliance team
   - Document provider choice rationale
   - Review cloud provider DPA/BAA if needed

3. **Hybrid Approach**
   - Use LLaMA for production databases
   - Use cloud providers for dev/test environments
   - Separate sensitive and non-sensitive workloads

4. **Monitoring**
   - Enable AI_LOG_REQUESTS=true
   - Monitor all API calls
   - Review logs for sensitive data leakage

---

## Troubleshooting

### LLaMA Provider Issues

**Problem:** "Model not found in Ollama"
```bash
# Pull the model
docker-compose exec ai-llama ollama pull llama3.1:8b

# List available models
docker-compose exec ai-llama ollama list
```

**Problem:** Slow responses
- Check GPU availability: `nvidia-smi`
- Try smaller model: `LLAMA_MODEL=llama3:8b`
- Increase timeout: `AI_TIMEOUT=300.0`

### OpenAI Provider Issues

**Problem:** "Invalid API key"
- Verify key in .env: `echo $OPENAI_API_KEY`
- Check key at: https://platform.openai.com/api-keys
- Ensure key starts with `sk-proj-` or `sk-`

**Problem:** Rate limit errors
- Reduce concurrent analysis requests
- Implement request queuing
- Upgrade API tier at OpenAI

### Anthropic Provider Issues

**Problem:** "Invalid API key"
- Verify key in .env: `echo $ANTHROPIC_API_KEY`
- Check key at: https://console.anthropic.com/
- Ensure key starts with `sk-ant-`

**Problem:** Model not available
- Check available models in Anthropic console
- Update ANTHROPIC_MODEL to supported version

---

## Advanced Configuration

### Using Azure OpenAI

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=your-azure-key
OPENAI_BASE_URL=https://your-resource.openai.azure.com
OPENAI_MODEL=gpt-4  # Your Azure deployment name
```

### Custom Ollama Models

```bash
# Use a custom fine-tuned model
LLAMA_MODEL=my-custom-model:latest

# Pull model first
docker-compose exec ai-llama ollama pull my-custom-model
```

### Multiple Environments

```bash
# .env.production - Use local
AI_PROVIDER=llama

# .env.development - Use cloud
AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-dev-key
```

---

## Logging and Monitoring

### Request Logging

When `AI_LOG_REQUESTS=true`, you'll see detailed logs:

```
INFO:services.ai.llama_provider:AI Request | Provider: llama | Model: llama3.1:8b | Query length: 156 chars | Has EXPLAIN: True | Has schema: True
INFO:services.ai.llama_provider:AI Response | Provider: llama | Model: llama3.1:8b | Duration: 2345.67ms | Tokens: 2341 | Analysis length: 1234 chars | Error: None
```

### Database Poll Logging

Collector logs every MySQL query:

```
INFO:services.collector:📡 DB Poll | Connecting to MySQL at 127.0.0.1:3306
INFO:services.collector:📊 DB Poll | Query: SELECT FROM mysql.slow_log WHERE start_time > 2024-01-15 AND user_host NOT LIKE 'dbpower_monitor@%' LIMIT 100
INFO:services.collector:✅ DB Poll Complete | Found: 5 queries | Duration: 0.123s
```

---

## Migration Guide

### From Old System to Multi-Provider

**Step 1:** Update configuration
```bash
# Old config
AI_BASE_URL=http://ai-llama:11434
AI_MODEL=llama3.1:8b

# New config (backward compatible)
AI_PROVIDER=llama
LLAMA_BASE_URL=http://ai-llama:11434
LLAMA_MODEL=llama3.1:8b
```

**Step 2:** Update dependencies
```bash
# Already done in requirements.txt
# httpx==0.27.0 added
```

**Step 3:** Restart services
```bash
docker-compose down
docker-compose up -d
```

**Step 4:** Verify
```bash
docker-compose exec backend python -c "
from services.ai import get_ai_provider
provider = get_ai_provider()
print(f'Using provider: {provider.__class__.__name__}')
"
```

---

## FAQ

**Q: Can I switch providers without losing data?**  
A: Yes, provider choice only affects new analyses. Historical analyses are preserved.

**Q: Which provider gives the best results?**  
A: Generally: GPT-4 > Claude 3 Opus > LLaMA 70B > Claude 3 Sonnet > LLaMA 13B

**Q: Can I use my own LLaMA model?**  
A: Yes, pull any Ollama-compatible model and set LLAMA_MODEL to its name.

**Q: Is my API key secure?**  
A: Keys are only stored in .env (never committed to git). They're passed to containers securely.

**Q: Can I use multiple providers simultaneously?**  
A: Not currently. You can only use one provider at a time per instance.

**Q: What happens if the AI provider is down?**  
A: Analysis will fail with error message. Query is still collected and can be re-analyzed later.

**Q: Can I run LLaMA without GPU?**  
A: Yes, but it will be much slower. Consider using smaller models (7B instead of 70B).

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs backend`
2. Test provider: `./scripts/test_ai_providers.sh`
3. Review this documentation
4. Open GitHub issue with logs and configuration

---

**Last Updated:** 2024
**Version:** 2.0.0
