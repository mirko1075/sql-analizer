# DBPower AI Analyzer

**Standalone microservice for SQL query performance analysis using AI models.**

Supports both **cloud models** (OpenAI, Anthropic) and **on-premise models** (Ollama) for maximum flexibility.

## Features

- 🤖 **Multiple AI Providers**: OpenAI (cloud), Ollama (on-premise)
- 🔒 **API Key Authentication**: Secure access control
- 📊 **Detailed Analysis**: Performance issues, missing indexes, query optimization
- 🚀 **Batch Processing**: Analyze multiple queries in parallel
- 📈 **Statistics Tracking**: Monitor analysis performance
- 🐳 **Docker Ready**: Production-ready containers
- 🔐 **Privacy First**: Option to not log SQL queries
- ⚡ **Fast API**: Built with FastAPI for high performance

---

## Quick Start

### Using Docker Compose (Cloud - OpenAI)

```bash
# Copy environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env

# Start service
docker-compose --profile cloud up -d

# View logs
docker-compose logs -f ai-analyzer-cloud
```

### Using Docker Compose (On-Premise - Ollama)

```bash
# Copy environment file
cp .env.example .env

# Edit .env (no API key needed for Ollama)
nano .env

# Start services (analyzer + ollama)
docker-compose --profile local up -d

# Pull model (first time only)
docker exec ollama ollama pull codellama:13b

# View logs
docker-compose logs -f ai-analyzer-local
```

Service will be available at: `http://localhost:8001`

API Documentation: `http://localhost:8001/docs`

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| **Service** |
| `ANALYZER_HOST` | Service host | `0.0.0.0` | No |
| `ANALYZER_PORT` | Service port | `8001` | No |
| `ANALYZER_WORKERS` | Number of workers | `1` | No |
| **AI Model** |
| `MODEL_PROVIDER` | Provider: `openai`, `ollama`, `anthropic` | `openai` | Yes |
| `MODEL_NAME` | Model name (e.g., `gpt-4`, `codellama:13b`) | `gpt-4` | Yes |
| `MODEL_API_KEY` | API key (for cloud providers) | - | For OpenAI |
| `MODEL_API_BASE_URL` | API endpoint (for Ollama) | - | For Ollama |
| `MODEL_TEMPERATURE` | Sampling temperature (0.0-2.0) | `0.7` | No |
| `MODEL_MAX_TOKENS` | Max tokens in response | `2000` | No |
| `MODEL_TIMEOUT` | Request timeout (seconds) | `60` | No |
| **Analysis** |
| `MAX_QUERY_LENGTH` | Max SQL query length | `10000` | No |
| `ENABLE_CACHING` | Enable result caching | `true` | No |
| `CACHE_TTL` | Cache TTL (seconds) | `3600` | No |
| **Security** |
| `REQUIRE_AUTHENTICATION` | Require API key | `true` | No |
| `ALLOWED_API_KEYS` | Comma-separated API keys | - | If auth enabled |
| **Logging** |
| `LOG_LEVEL` | Log level | `INFO` | No |
| `LOG_QUERIES` | Log SQL queries (privacy) | `false` | No |

### Generate API Keys

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## API Usage

### 1. Analyze Single Query

**Request**:
```bash
curl -X POST "http://localhost:8001/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "sql_query": "SELECT * FROM users WHERE email LIKE '\''%@example.com%'\'' ORDER BY created_at DESC",
    "database_type": "postgresql",
    "execution_time_ms": 2500.5,
    "rows_examined": 100000,
    "rows_returned": 50
  }'
```

**Response**:
```json
{
  "query_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "analyzed_at": "2024-01-15T10:30:00Z",
  "issues_found": 2,
  "issues": [
    {
      "severity": "high",
      "category": "full_table_scan",
      "title": "Full table scan with LIKE pattern",
      "description": "Using LIKE with leading wildcard prevents index usage",
      "suggestion": "Use full-text search or reconsider query pattern",
      "estimated_impact": "80% performance improvement"
    },
    {
      "severity": "medium",
      "category": "missing_index",
      "title": "Missing index on email column",
      "description": "Email filtering without index causes table scan",
      "suggestion": "CREATE INDEX idx_users_email ON users(email);",
      "estimated_impact": "50% faster filtering"
    }
  ],
  "overall_assessment": "Query has significant performance issues that should be addressed",
  "optimization_priority": "high",
  "estimated_improvement": "80% faster execution",
  "ai_model_used": "gpt-4",
  "analysis_time_ms": 1250.5
}
```

### 2. Batch Analysis

**Request**:
```bash
curl -X POST "http://localhost:8001/api/v1/analyze/batch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key": your-api-key" \
  -d '{
    "queries": [
      {
        "sql_query": "SELECT * FROM users WHERE id = 1",
        "database_type": "postgresql"
      },
      {
        "sql_query": "SELECT * FROM orders WHERE user_id IN (SELECT id FROM users)",
        "database_type": "mysql"
      }
    ],
    "parallel": true
  }'
```

### 3. Health Check

```bash
curl "http://localhost:8001/api/v1/health"
```

### 4. Statistics

```bash
curl "http://localhost:8001/api/v1/stats" \
  -H "X-API-Key: your-api-key"
```

---

## Deployment Options

### Option 1: Cloud (OpenAI)

**Pros:**
- State-of-the-art AI models (GPT-4)
- No local GPU required
- Fast inference
- Automatically updated models

**Cons:**
- Requires internet connection
- API costs per request
- Data sent to OpenAI servers

**Setup:**
```bash
docker-compose --profile cloud up -d
```

### Option 2: On-Premise (Ollama)

**Pros:**
- Complete data privacy
- No API costs
- Works offline
- Full control

**Cons:**
- Requires CPU/GPU resources
- Slower inference
- Manual model management

**Setup:**
```bash
# Start services
docker-compose --profile local up -d

# Pull model (first time)
docker exec ollama ollama pull codellama:13b

# Optional: Pull other models
docker exec ollama ollama pull llama2:13b
docker exec ollama ollama pull mistral
```

**Recommended Models for SQL Analysis:**
- `codellama:13b` - Best for code/SQL (13GB)
- `llama2:13b` - General purpose (7GB)
- `mistral:7b` - Fast, efficient (4GB)

### Option 3: Hybrid

Run both cloud and on-premise, switch based on requirements:

```bash
# Start both
docker-compose --profile cloud --profile local up -d

# Use cloud for critical queries
curl -X POST "http://localhost:8001/analyze" ...

# Use on-premise for sensitive data
# (configure analyzer to use Ollama)
```

---

## Manual Installation

### Prerequisites

- Python 3.11+
- pip

### Steps

```bash
# Clone repository
git clone <repo-url>
cd ai-analyzer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env

# Run service
python main.py
```

Service will start on `http://0.0.0.0:8001`

---

## Testing

### Run All Tests

```bash
# With virtual environment activated
cd ai-analyzer
source venv/bin/activate

# Run tests
python -m pytest tests/ -v
```

### Run Specific Test Class

```bash
python -m pytest tests/test_api.py::TestAnalyzeEndpoint -v
```

### Test with Docker

```bash
# Build test image
docker build -t dbpower-ai-analyzer-test .

# Run tests
docker run --rm dbpower-ai-analyzer-test pytest tests/ -v
```

---

## Production Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-analyzer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-analyzer
  template:
    metadata:
      labels:
        app: ai-analyzer
    spec:
      containers:
      - name: ai-analyzer
        image: dbpower-ai-analyzer:latest
        ports:
        - containerPort: 8001
        env:
        - name: MODEL_PROVIDER
          value: "openai"
        - name: MODEL_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-analyzer-secrets
              key: openai-api-key
        - name: ALLOWED_API_KEYS
          valueFrom:
            secretKeyRef:
              name: ai-analyzer-secrets
              key: allowed-api-keys
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

### Environment Best Practices

1. **Never commit API keys** - use environment variables or secrets management
2. **Enable authentication** in production (`REQUIRE_AUTHENTICATION=true`)
3. **Don't log queries** for privacy (`LOG_QUERIES=false`)
4. **Use HTTPS** in production
5. **Set appropriate rate limits** (via API gateway)
6. **Monitor resource usage** (especially for on-premise models)

---

## Monitoring

### Metrics to Track

- **Request rate** (requests/second)
- **Analysis time** (average ms)
- **Error rate** (%)
- **Model provider health**
- **Resource usage** (CPU, memory)

### Health Checks

```bash
# Kubernetes liveness probe
curl -f http://localhost:8001/api/v1/health || exit 1

# Check model availability (Ollama)
curl http://localhost:11434/api/tags
```

---

## Troubleshooting

### Issue: "Cannot connect to local model"

**Solution:**
```bash
# Check if Ollama is running
docker ps | grep ollama

# Start Ollama
docker-compose --profile local up -d ollama

# Check Ollama health
curl http://localhost:11434/api/tags
```

### Issue: "OpenAI API timeout"

**Solution:**
- Increase `MODEL_TIMEOUT` in environment
- Check internet connection
- Verify API key is valid
- Check OpenAI service status

### Issue: "Analysis too slow with Ollama"

**Solution:**
- Use smaller model (e.g., `mistral:7b` instead of `codellama:13b`)
- Reduce `MODEL_MAX_TOKENS`
- Allocate more CPU/GPU resources
- Consider cloud provider for faster inference

### Issue: "Invalid API key"

**Solution:**
```bash
# Verify API key in .env file
cat .env | grep ALLOWED_API_KEYS

# Generate new API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update environment and restart
docker-compose restart ai-analyzer-cloud
```

---

## Architecture

```
┌─────────────────────────────────────────────┐
│          FastAPI Application                │
│                                             │
│  ┌──────────┐    ┌──────────┐             │
│  │   API    │────│  Routes  │             │
│  │ Gateway  │    │          │             │
│  └──────────┘    └─────┬────┘             │
│                        │                   │
│                  ┌─────▼─────┐             │
│                  │ Analyzer  │             │
│                  │ Factory   │             │
│                  └─────┬─────┘             │
│                        │                   │
│         ┌──────────────┴──────────────┐    │
│         │                             │    │
│  ┌──────▼──────┐           ┌──────────▼───┐│
│  │   OpenAI    │           │    Ollama    ││
│  │  Analyzer   │           │   Analyzer   ││
│  └──────┬──────┘           └──────────┬───┘│
└─────────┼─────────────────────────────┼────┘
          │                             │
          ▼                             ▼
  ┌───────────────┐            ┌───────────────┐
  │  OpenAI API   │            │ Ollama Local  │
  │   (Cloud)     │            │   (Docker)    │
  └───────────────┘            └───────────────┘
```

---

## API Reference

Full API documentation available at: `http://localhost:8001/docs`

Interactive API testing: `http://localhost:8001/redoc`

---

## License

See main project LICENSE file.

---

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Contact: support@dbpower.ai

---

## Changelog

### v1.0.0 (2024-01-15)
- Initial release
- OpenAI and Ollama support
- Batch analysis
- API key authentication
- Docker deployment
- Comprehensive testing

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
