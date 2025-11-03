# 🧠 DBPower Base - LLaMA Edition

**AI-Powered MySQL Query Analyzer with Local LLaMA Model**

A simplified, on-premise solution for monitoring and analyzing slow MySQL queries using rule-based detection combined with local LLaMA AI (no external API calls required).

---

## ✨ Features

- 🔍 **Real-time Slow Query Detection** - Monitors MySQL `slow_log` table
- 📊 **Smart Analysis** - Combines rule-based checks with AI insights
- 🧠 **Local AI with LLaMA** - Uses Ollama for on-premise AI analysis (no OpenAI/Claude)
- 💡 **Index Suggestions** - Automatically recommends missing indexes
- 🚀 **Easy Deployment** - Everything runs in Docker Compose
- 🎯 **No Authentication** - Simple internal tool (add auth if needed)
- 📈 **Performance Metrics** - Track query time, rows examined, efficiency ratios

---

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │ (React + Vite)
│   Port 3000 │
└──────┬──────┘
       │
┌──────▼──────┐
│   Backend   │ (FastAPI)
│   Port 8000 │
└──┬───────┬──┘
   │       │
   │   ┌───▼────────┐
   │   │  AI LLaMA  │ (Ollama)
   │   │ Port 11434 │
   │   └────────────┘
   │
┌──▼──────────┐
│  MySQL Lab  │ (Test Database)
│  Port 3307  │
└─────────────┘
```

**Components:**
- **mysql-lab**: MySQL 8.0 with slow query logging enabled
- **backend**: FastAPI app (collector + analyzer + API)
- **ai-llama**: Ollama container with LLaMA 3.1:8b model
- **frontend**: React dashboard to view and analyze queries

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- ~8GB disk space (for LLaMA model)
- 4GB RAM minimum

### Installation

1. **Clone or copy this project:**
```bash
cd dbpower-base
```

2. **Create `.env` file** (copy from `.env.example`):
```bash
cp .env.example .env
```

3. **Start everything:**
```bash
docker compose up -d
```

**First startup will take 5-10 minutes** to download the LLaMA model (~5GB).

4. **Check logs:**
```bash
# Watch backend logs (shows when AI model is ready)
docker compose logs -f backend

# You should see: "✅ Model ready for analysis"
```

5. **Access the dashboard:**
```
http://localhost:3000
```

---

## 📚 Usage

### 1. Load Demo Data
The `mysql-lab` container automatically loads demo data on first startup:
- 10,000 users
- 50,000 orders
- 1,000 products
- **Intentionally missing indexes** to generate slow queries

### 2. Generate Slow Queries
Run the simulator inside the MySQL container:

```bash
# Enter the mysql-lab container
docker compose exec mysql-lab bash

# Install Python (needed for simulator)
apt-get update && apt-get install -y python3 python3-pip
pip3 install mysql-connector-python

# Run the simulator
python3 /docker-entrypoint-initdb.d/simulate_slow_queries.py
```

The simulator will continuously run slow queries to populate the `slow_log` table.

### 3. View & Analyze Queries

1. Open **http://localhost:3000**
2. Click **"🔄 Collect Now"** to import slow queries from MySQL
3. Click on any query to see details
4. Click **"🚀 Analyze with LLaMA AI"** to get AI-powered insights

---

## 🔧 Configuration

Edit `.env` file:

```env
# MySQL Configuration
MYSQL_HOST=mysql-lab
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=rootpassword
MYSQL_DATABASE=labdb

# AI Configuration
AI_BASE_URL=http://ai-llama:11434
AI_MODEL=llama3.1:8b

# Backend Settings
API_PORT=8000
LOG_LEVEL=INFO
COLLECTION_INTERVAL=300  # seconds (5 minutes)
```

### Change LLaMA Model

To use a different model:
1. Edit `.env`: `AI_MODEL=llama3.2:latest`
2. Restart: `docker compose restart backend`
3. The new model will be pulled automatically

Available models: https://ollama.ai/library

---

## 🗂️ Project Structure

```
dbpower-base/
├── docker-compose.yml       # All services
├── .env.example             # Configuration template
├── backend/                 # FastAPI application
│   ├── core/                # Config & logging
│   ├── db/                  # SQLite models
│   ├── services/            # Collector, Analyzer, AI client
│   ├── api/routes/          # API endpoints
│   └── main.py              # FastAPI app
├── frontend/                # React dashboard
│   └── src/
│       ├── pages/           # Dashboard & QueryDetail
│       └── services/        # API client
├── mysql-lab/               # Test MySQL database
│   ├── init.sql             # Demo data
│   └── simulate_slow_queries.py
└── README.md
```

---

## 🐛 Troubleshooting

### Backend fails to start
```bash
# Check if AI service is ready
docker compose logs ai-llama

# Restart backend after AI is ready
docker compose restart backend
```

### LLaMA model download is slow
The first startup downloads ~5GB. Be patient. Check progress:
```bash
docker compose logs -f ai-llama
```

### No slow queries appearing
1. Make sure MySQL slow query log is enabled:
```sql
SHOW VARIABLES LIKE 'slow_query_log';
-- Should show: ON
```

2. Run the query simulator (see "Generate Slow Queries" above)

3. Manually trigger collection from the dashboard

### Frontend shows "Failed to load data"
```bash
# Check backend health
curl http://localhost:8000/health

# Check backend logs
docker compose logs backend
```

---

## 📊 API Endpoints

### Slow Queries
- `GET /api/v1/slow-queries` - List all slow queries
- `GET /api/v1/slow-queries/{id}` - Get query details
- `GET /api/v1/slow-queries/stats/summary` - Get statistics

### Analysis
- `POST /api/v1/analyze/{id}` - Analyze a specific query
- `GET /api/v1/analyze/{id}` - Get analysis results
- `POST /api/v1/analyze/collect` - Manually trigger collection

### Health
- `GET /health` - Backend + AI health check
- `GET /` - API info

**Interactive docs:** http://localhost:8000/docs

---

## 🎯 Using with Your Own MySQL

To monitor your production MySQL:

1. **Enable slow query log** on your MySQL server:
```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.5;  -- Queries taking >0.5s
SET GLOBAL log_output = 'TABLE';   -- Log to mysql.slow_log table
```

2. **Update `.env`**:
```env
MYSQL_HOST=your-mysql-host
MYSQL_PORT=3306
MYSQL_USER=your-user
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=mysql  # Database containing slow_log table
```

3. **Restart backend**:
```bash
docker compose restart backend
```

4. **Remove mysql-lab** from `docker-compose.yml` (optional)

---

## 🔒 Security Notes

⚠️ **This is an internal tool with NO authentication!**

For production use:
- Add authentication (JWT, OAuth, etc.)
- Restrict network access (firewall, VPN)
- Use read-only MySQL user
- Enable HTTPS
- Review CORS settings in `backend/main.py`

---

## 🚦 Performance Tips

- **Collection Interval**: Adjust `COLLECTION_INTERVAL` in `.env` (default: 300s)
- **Batch Size**: Collector fetches 100 queries per run (adjust in `collector.py`)
- **LLaMA Model**: Smaller models = faster analysis (e.g., `llama3.1:7b` vs `llama3.1:70b`)
- **SQLite Storage**: Analysis results stored in `/app/cache/dbpower.db` (persistent)

---

## 📝 License

MIT License - Free to use and modify

---

## 🤝 Contributing

This is a simplified version. Feel free to extend:
- Add PostgreSQL support
- Multi-database monitoring
- Email alerts for critical queries
- Query comparison (before/after optimization)
- Integration with Grafana

---

## 📞 Support

For issues or questions:
1. Check logs: `docker compose logs`
2. Verify configuration in `.env`
3. Ensure all containers are running: `docker compose ps`

---

**Built with ❤️ using FastAPI, React, and LLaMA 3.1**
