# Query Status Management - Feature Documentation

## 📋 Overview

DBPower now includes a complete query lifecycle management system. Queries flow through different states, preventing duplicates and allowing you to track which queries have been reviewed.

## 🔄 Query Lifecycle

```
┌──────────┐
│ PENDING  │  ← New queries start here
└────┬─────┘
     │
     ├──→ ┌──────────┐
     │    │ ANALYZED │  ← After analysis complete
     │    └──────────┘
     │
     ├──→ ┌──────────┐
     │    │ ARCHIVED │  ← Not interesting / ignore
     │    └──────────┘
     │
     └──→ ┌──────────┐
          │ RESOLVED │  ← Fixed or acknowledged OK
          └──────────┘
```

### Status Definitions

- **pending**: Query just collected, needs review
- **analyzed**: Analysis completed, waiting for action
- **archived**: Marked as not interesting (won't show in default view)
- **resolved**: Issue fixed or acknowledged as acceptable

## 🚫 Duplicate Prevention

Queries are deduplicated using:
- SQL fingerprint (MD5 hash of normalized query)
- Start time from MySQL slow_log

**Result**: Same query at the same time = skipped on collection

## 📡 API Endpoints

### List Queries with Filtering

```bash
# Default: show pending and analyzed only
GET /api/v1/slow-queries

# Filter by specific status
GET /api/v1/slow-queries?status=pending
GET /api/v1/slow-queries?status=analyzed
GET /api/v1/slow-queries?status=archived
GET /api/v1/slow-queries?status=resolved
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/slow-queries?status=pending&limit=10"
```

**Response:**
```json
{
  "queries": [
    {
      "id": 1,
      "status": "pending",
      "sql_text": "SELECT * FROM users WHERE email = '...'",
      "query_time": 1.23,
      "detected_at": "2025-11-03T20:00:00"
    }
  ],
  "total": 1,
  "has_more": false
}
```

---

### Update Query Status

```bash
# General update
PATCH /api/v1/slow-queries/{id}/status
Body: {"status": "archived"}

# Quick shortcuts
POST /api/v1/slow-queries/{id}/archive   # Set to archived
POST /api/v1/slow-queries/{id}/resolve   # Set to resolved
```

**Examples:**
```bash
# Archive a query (not interesting)
curl -X POST http://localhost:8000/api/v1/slow-queries/5/archive

# Resolve a query (fixed or OK)
curl -X POST http://localhost:8000/api/v1/slow-queries/7/resolve

# Custom status update
curl -X PATCH http://localhost:8000/api/v1/slow-queries/3/status \
  -H "Content-Type: application/json" \
  -d '{"status": "analyzed"}'
```

**Response:**
```json
{
  "id": 5,
  "old_status": "pending",
  "new_status": "archived",
  "message": "Query status updated to archived"
}
```

---

### Collection with Duplicate Detection

```bash
POST /api/v1/analyze/collect
```

**Response:**
```json
{
  "collected": 5,
  "skipped_duplicates": 3,
  "message": "Successfully collected 5 slow queries"
}
```

---

## 🎨 Frontend Integration

### Filter Dropdown

Add status filter to your query list:

```typescript
const [statusFilter, setStatusFilter] = useState<string>('');

// Fetch queries
const params = new URLSearchParams();
if (statusFilter) {
  params.append('status', statusFilter);
}

fetch(`/api/v1/slow-queries?${params}`);
```

### Status Badge Component

```tsx
const StatusBadge = ({ status }: { status: string }) => {
  const colors = {
    pending: 'bg-yellow-100 text-yellow-800',
    analyzed: 'bg-blue-100 text-blue-800',
    archived: 'bg-gray-100 text-gray-800',
    resolved: 'bg-green-100 text-green-800'
  };
  
  return (
    <span className={`px-2 py-1 rounded ${colors[status]}`}>
      {status}
    </span>
  );
};
```

### Action Buttons

```tsx
<button onClick={() => archiveQuery(queryId)}>
  📦 Archive
</button>

<button onClick={() => resolveQuery(queryId)}>
  ✅ Resolve
</button>
```

---

## 🔄 Typical Workflow

### 1. New queries arrive (pending)
```bash
curl -X POST http://localhost:8000/api/v1/analyze/collect
```

### 2. Review pending queries
```bash
curl "http://localhost:8000/api/v1/slow-queries?status=pending"
```

### 3. Analyze interesting ones
```bash
curl -X POST http://localhost:8000/api/v1/analyze/5
```
(Status automatically becomes "analyzed")

### 4. Take action

**Option A: Not interesting → Archive**
```bash
curl -X POST http://localhost:8000/api/v1/slow-queries/5/archive
```

**Option B: Fixed → Resolve**
```bash
curl -X POST http://localhost:8000/api/v1/slow-queries/5/resolve
```

### 5. Next collection ignores duplicates
```bash
curl -X POST http://localhost:8000/api/v1/analyze/collect
# Same queries won't be collected again
```

---

## 🗄️ Database Schema Changes

New fields in `slow_queries` table:

```sql
ALTER TABLE slow_queries ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
CREATE INDEX idx_status ON slow_queries(status);
CREATE INDEX idx_status_collected ON slow_queries(status, collected_at);
```

Unique constraint prevents duplicates:
```sql
UNIQUE CONSTRAINT (sql_fingerprint, start_time)
```

---

## 🔧 Migration

To upgrade existing databases:

```bash
docker exec dbpower-backend python scripts/migrate_add_status.py
```

This will:
- Add `status` column
- Update existing records (analyzed=true → 'analyzed', else 'pending')
- Create necessary indexes

---

## 📊 Statistics

Updated stats endpoint includes status breakdown:

```bash
curl http://localhost:8000/api/v1/stats
```

```json
{
  "total_queries": 100,
  "by_status": {
    "pending": 25,
    "analyzed": 30,
    "archived": 20,
    "resolved": 25
  },
  "average_query_time": 1.23
}
```

---

## 🎯 Use Cases

### Daily Workflow
1. Morning: Check pending queries
2. Analyze critical ones
3. Archive noise (test queries, expected slow queries)
4. Fix issues and mark as resolved

### Reporting
```bash
# What's still pending?
curl "http://localhost:8000/api/v1/slow-queries?status=pending"

# What did we fix this week?
curl "http://localhost:8000/api/v1/slow-queries?status=resolved"

# What's just noise?
curl "http://localhost:8000/api/v1/slow-queries?status=archived"
```

---

## ⚠️ Important Notes

1. **Default view excludes archived/resolved**
   - Only shows pending + analyzed
   - Must explicitly filter to see archived/resolved

2. **Duplicates based on fingerprint + time**
   - Same query at different times = different entries
   - Same query at same time = duplicate (skipped)

3. **Status is independent of analysis**
   - Can archive without analyzing
   - Can mark resolved even if not analyzed

4. **Backward compatibility**
   - Old `analyzed` boolean still works
   - New `status` field is preferred
