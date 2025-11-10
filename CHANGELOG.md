# 🎉 DBPower Updates - Query Lifecycle & Test Suite

## ✨ What's New

### 1. Query Status Management

Le query ora hanno un **ciclo di vita completo**:

```
PENDING → ANALYZED → ARCHIVED/RESOLVED
```

#### Stati disponibili:
- **pending**: Query appena raccolta, da rivedere
- **analyzed**: Analisi completata, in attesa di azione
- **archived**: Non interessante, nascosta di default
- **resolved**: Problema risolto o accettato come OK

#### Prevenzione duplicati:
✅ Le query con lo stesso fingerprint e timestamp **non vengono più duplicate**

---

### 2. Nuovi Endpoint API

```bash
# Filtra per stato
GET /api/v1/slow-queries?status=pending
GET /api/v1/slow-queries?status=archived
GET /api/v1/slow-queries?status=resolved

# Cambia stato
PATCH /api/v1/slow-queries/{id}/status
Body: {"status": "archived"}

# Shortcut veloci
POST /api/v1/slow-queries/{id}/archive    # Archivia
POST /api/v1/slow-queries/{id}/resolve    # Risolvi
```

---

### 3. Test Suite Completo

Nuova cartella `tests/` con **12 scenari di test** per ogni problema comune:

| Test | Problema | Dimensione DB |
|------|----------|---------------|
| 01-03 | Missing Indexes | 50K users, 5K products |
| 04-05 | N+1 e Join Problems | 100K orders |
| 06 | Subquery lente | 150K reviews |
| 07 | Partitioning | 500K analytics events |
| 08 | Text Search | Full table scans |
| 09-12 | SELECT *, ORDER BY, GROUP BY | Vari |

---

## 🚀 Come Usare

### Workflow Quotidiano

#### 1. Raccogli nuove query
```bash
curl -X POST http://localhost:8000/api/v1/analyze/collect
```

#### 2. Vedi le pending
```bash
curl "http://localhost:8000/api/v1/slow-queries?status=pending"
```

#### 3. Analizza quelle interessanti
```bash
curl -X POST http://localhost:8000/api/v1/analyze/5
```

#### 4. Archivia il rumore
```bash
# Query di test, expected slow queries, etc.
curl -X POST http://localhost:8000/api/v1/slow-queries/5/archive
```

#### 5. Risolvi i problemi
```bash
# Dopo aver fixato il problema
curl -X POST http://localhost:8000/api/v1/slow-queries/7/resolve
```

---

### Test Suite

#### Setup iniziale (una volta sola):
```bash
cd tests
./setup-test-env.sh
```

Questo crea:
- Database `dbpower_test`
- ~1.1M righe di dati di test
- Tabelle con problemi intenzionali

#### Esegui tutti i test:
```bash
./run-all-tests.sh
```

#### Esegui un test specifico:
```bash
./run-test.sh 01    # Missing index
./run-test.sh 05    # Join senza FK index
./run-test.sh 07    # Partitioning needs
```

#### Quick Start (tutto in un comando):
```bash
./quick-start.sh
```

---

## 📁 Struttura File

```
backend/
├── db/models.py                    # ✅ Aggiunto campo status
├── services/
│   └── collector.py                # ✅ Prevenzione duplicati
├── api/routes/
│   └── slow_queries.py             # ✅ Nuovi endpoint status
├── scripts/
│   └── migrate_add_status.py       # Script migrazione
└── docs/
    └── QUERY_STATUS_MANAGEMENT.md  # Documentazione completa

tests/
├── setup-test-env.sh               # Setup DB di test
├── run-test.sh                     # Esegui test singolo
├── run-all-tests.sh                # Esegui tutti i test
├── quick-start.sh                  # Setup + run tutto
├── 01-missing-index-email.sql      # Test 1
├── 02-full-table-scan-country.sql  # Test 2
├── ... (12 test totali)
└── README.md                       # Doc completa

data/mysql-lab/
├── test-schema.sql                 # Schema DB test
└── generate-test-data.py           # Generatore dati
```

---

## 🔧 Migrazione Database Esistente

Se hai già delle query raccolte:

```bash
docker exec dbpower-backend python scripts/migrate_add_status.py
```

Questo:
- Aggiunge campo `status`
- Imposta `analyzed` → 'analyzed', altri → 'pending'
- Crea indici per performance

---

## 📊 Esempi Pratici

### Vedere solo le query da analizzare
```bash
curl "http://localhost:8000/api/v1/slow-queries?status=pending&limit=10" | jq
```

### Archiviare query di test
```bash
# Esempio: archiviare tutte le query di SLEEP (test queries)
for id in $(curl -s "http://localhost:8000/api/v1/slow-queries" | jq '.queries[] | select(.sql_text | contains("SLEEP")) | .id'); do
  curl -X POST "http://localhost:8000/api/v1/slow-queries/$id/archive"
done
```

### Statistiche per stato
```bash
for status in pending analyzed archived resolved; do
  count=$(curl -s "http://localhost:8000/api/v1/slow-queries?status=$status" | jq '.total')
  echo "$status: $count"
done
```

---

## 🎨 Frontend (TODO)

Il backend è pronto, manca solo il frontend:

### Componenti da aggiungere:

1. **Dropdown filtro stato**
   ```tsx
   <select onChange={e => setStatus(e.target.value)}>
     <option value="">All</option>
     <option value="pending">Pending</option>
     <option value="analyzed">Analyzed</option>
     <option value="archived">Archived</option>
     <option value="resolved">Resolved</option>
   </select>
   ```

2. **Status badge**
   ```tsx
   <StatusBadge status={query.status} />
   ```

3. **Action buttons**
   ```tsx
   <button onClick={() => archiveQuery(id)}>Archive</button>
   <button onClick={() => resolveQuery(id)}>Resolve</button>
   ```

---

## 🧪 Test Rapido

```bash
# 1. Raccogli query esistenti
curl -X POST http://localhost:8000/api/v1/analyze/collect

# 2. Vedi quante sono pending
curl -s "http://localhost:8000/api/v1/slow-queries?status=pending" | jq '.total'

# 3. Archivia la prima
ID=$(curl -s "http://localhost:8000/api/v1/slow-queries?status=pending" | jq '.queries[0].id')
curl -X POST "http://localhost:8000/api/v1/slow-queries/$ID/archive"

# 4. Verifica: ora dovrebbe essere una in meno
curl -s "http://localhost:8000/api/v1/slow-queries?status=pending" | jq '.total'

# 5. Verifica che sia in archived
curl -s "http://localhost:8000/api/v1/slow-queries?status=archived" | jq '.total'
```

---

## 📚 Documentazione Completa

- **Query Status**: `backend/docs/QUERY_STATUS_MANAGEMENT.md`
- **Test Suite**: `tests/README.md`
- **Quick Reference**: `tests/QUICK_REFERENCE.md`
- **Troubleshooting**: `backend/scripts/TROUBLESHOOTING.md`

---

## ✅ Checklist

Backend:
- [x] Campo status aggiunto al modello
- [x] Prevenzione duplicati nel collector
- [x] Endpoint PATCH /status
- [x] Endpoint POST /archive
- [x] Endpoint POST /resolve
- [x] Filtro ?status=... nel GET
- [x] Default view (pending + analyzed)
- [x] Script migrazione
- [x] Documentazione

Test Suite:
- [x] 12 test SQL completi
- [x] Schema DB con problemi intenzionali
- [x] Generatore dati (~1.1M righe)
- [x] Script setup
- [x] Script run singolo test
- [x] Script run tutti test
- [x] Script quick-start
- [x] Documentazione

Frontend:
- [ ] Dropdown filtro stato
- [ ] Status badge component
- [ ] Action buttons (archive/resolve)
- [ ] Update UI dopo cambio stato

---

## 🎯 Prossimi Passi

1. **Testa il workflow**:
   ```bash
   cd tests
   ./quick-start.sh
   ```

2. **Prova i nuovi endpoint** (vedi esempi sopra)

3. **Implementa il frontend** quando pronto

4. **Usa in produzione**:
   - Raccogli query giornalmente
   - Analizza pending
   - Archivia rumore
   - Risolvi problemi
