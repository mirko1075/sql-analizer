# Frontend Integration - Collectors Page

## ✅ Completato!

Il frontend è ora completamente allineato con il backend per il sistema di Collector Agents.

## Modifiche Implementate

### 1. **TypeScript Types** ([types/index.ts](admin-panel/src/types/index.ts))

Aggiunti 3 nuovi tipi:

```typescript
export interface Collector {
  id: number;
  organization_id: number;
  team_id: number;
  name: string;
  type: 'mysql' | 'postgres';
  status: 'online' | 'offline' | 'stopped' | 'error' | 'starting';
  config: {...};
  stats: {...};
  is_online: boolean;
  // ... altri campi
}

export interface CollectorCommand {
  id: number;
  command: 'start' | 'stop' | 'collect' | 'update_config';
  // ... altri campi
}

export interface CollectorCreateRequest {
  name: string;
  type: 'mysql' | 'postgres';
  team_id: number;
  config: {...};
  // ... altri campi
}
```

### 2. **API Service** ([services/api.ts](admin-panel/src/services/api.ts))

Aggiunto `collectorsAPI` con 9 metodi:

```typescript
export const collectorsAPI = {
  list: () => api.get('/api/v1/collectors'),
  get: (id: number) => api.get(`/api/v1/collectors/${id}`),
  register: (data) => api.post('/api/v1/collectors/register', data),
  update: (id, data) => api.patch(`/api/v1/collectors/${id}`, data),
  delete: (id) => api.delete(`/api/v1/collectors/${id}`),
  start: (id) => api.post(`/api/v1/collectors/${id}/start`),
  stop: (id) => api.post(`/api/v1/collectors/${id}/stop`),
  collect: (id) => api.post(`/api/v1/collectors/${id}/collect`),
  getCommands: (id, limit) => api.get(`/api/v1/collectors/${id}/commands`, ...),
};
```

### 3. **Collectors Page** ([pages/Collectors.tsx](admin-panel/src/pages/Collectors.tsx))

Pagina completa con:

**Features Implementate:**

- ✅ **Lista Collectors** con status indicators (🟢 online / 🔴 offline)
- ✅ **Registrazione Nuovi Collectors** via form modale
- ✅ **Controlli Remoti**: Start, Stop, Collect Now buttons
- ✅ **Statistiche** per ogni collector:
  - Queries Collected
  - Errors Count
  - Uptime
  - Last Heartbeat
- ✅ **Status Badges** colorati per ogni stato
- ✅ **Modal con Dettagli** completi per ogni collector
- ✅ **API Key Display** dopo registrazione (mostrato una sola volta!)
- ✅ **Delete Collector** con conferma
- ✅ **Error Handling** con messaggi visualizzati
- ✅ **Loading States** con spinner
- ✅ **Empty State** quando non ci sono collectors

**UI/UX:**

- Responsive layout con grid
- Color coding per stati (verde=online, rosso=offline, giallo=stopped, etc.)
- Form di registrazione completo con validazione
- Modale per API key con warning prominente
- Bottoni disabilitati quando non applicabili (es. "Collect Now" se offline)

### 4. **Routing** ([App.tsx](admin-panel/src/App.tsx))

Aggiunta route:

```typescript
<Route path="collectors" element={<Collectors />} />
```

### 5. **Navigation** ([components/Layout.tsx](admin-panel/src/components/Layout.tsx))

Aggiunto link nella sidebar:

```typescript
<Link to="/collectors">
  <Database size={20} /> Collectors
</Link>
```

## Come Usare

### 1. Avviare il Frontend

```bash
cd admin-panel
npm install
npm run dev
```

### 2. Accedere alla Pagina Collectors

1. Login con `admin@dbpower.com` / `admin123`
2. Click su "Collectors" nella sidebar (icona Database 🗄️)

### 3. Registrare un Collector

1. Click su "+ Register Collector"
2. Compila il form:
   - **Name**: es. "Production MySQL Server"
   - **Type**: MySQL o PostgreSQL
   - **Team**: Seleziona team
   - **Host**: es. "127.0.0.1"
   - **Port**: 3306 (MySQL) o 5432 (PostgreSQL)
   - **User**: es. "monitoring"
   - **Password**: password del database
   - **Collection Interval**: minuti tra ogni raccolta (default: 5)
   - **Auto Collect**: Abilita/disabilita raccolta automatica
3. Click "Register"
4. **IMPORTANTE**: Copia l'API Key mostrato! Verrà mostrato solo una volta!

### 4. Configurare il Collector Agent

Crea il file di configurazione:

```json
{
  "collector_id": 1,
  "api_key": "collector_1_abc123xyz...",
  "backend_url": "http://localhost:8000",
  "db_type": "mysql",
  "db_config": {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "monitoring",
    "password": "password"
  }
}
```

Avvia l'agent:

```bash
cd collector_agent
python collector_agent.py --config config.json
```

### 5. Monitorare e Controllare

Dalla pagina Collectors puoi:

- **Vedere lo status** di ogni collector (online/offline)
- **Start/Stop** collectors
- **Trigger collection** manuale con "Collect Now"
- **Vedere statistiche**: queries raccolte, errori, uptime
- **Vedere dettagli** completi cliccando "Details"
- **Eliminare** collectors non più necessari

## Screenshots dello UI

### Lista Collectors

```
┌─────────────────────────────────────────────────────────────┐
│  Collectors                         [+ Register Collector]  │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Production MySQL Server          🟢 online            │  │
│  │ MYSQL • 127.0.0.1:3306                                │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Queries: 142  Errors: 0  Uptime: 2h 34m               │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ [Start] [Collect Now] [Details] [Delete]              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Staging PostgreSQL              🔴 offline            │  │
│  │ POSTGRES • staging.db:5432                            │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Queries: 58   Errors: 2  Uptime: 1h 12m               │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ [Start] [Collect Now] [Details] [Delete]              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Form Registrazione

```
┌─────────────────────────────────────┐
│ Register New Collector              │
├─────────────────────────────────────┤
│ Name: [Production MySQL Server___]  │
│ Type: [MySQL ▼]  Team: [Team 1 ▼]  │
│ Host: [127.0.0.1___] Port: [3306__] │
│ User: [monitoring_] Pass: [******_] │
│ Interval: [5] Auto: [Enabled ▼]     │
│                                      │
│         [Cancel]  [Register]         │
└─────────────────────────────────────┘
```

### API Key Display (Post-Registrazione)

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Collector Registered! Save this API Key:             │
├─────────────────────────────────────────────────────────┤
│ collector_1_abc123xyz789...                             │
├─────────────────────────────────────────────────────────┤
│ ⚠️ This key will only be shown once. Copy it now!       │
│                                              [Close]     │
└─────────────────────────────────────────────────────────┘
```

## Status Indicators

| Status | Color | Icon | Descrizione |
|--------|-------|------|-------------|
| **online** | Verde | 🟢 | Collector attivo e funzionante |
| **offline** | Grigio | 🔴 | Nessun heartbeat da >2 minuti |
| **stopped** | Giallo | ⏸️ | Fermato manualmente |
| **error** | Rosso | ❌ | In stato di errore |
| **starting** | Blu | ⏳ | In fase di avvio |

## Flusso Completo

```
User Action (Frontend)          →  Backend API               →  Collector Agent
──────────────────────────────────────────────────────────────────────────────

1. Register Collector           →  POST /collectors/register →  -
   Returns: API Key             ←  {id, api_key}              ←  -

2. Start Agent (CLI)            →  -                          →  Start Process
                                                                  Send Heartbeat

3. Heartbeat Loop               →  -                          →  POST /heartbeat
   Update Status                ←  GET /collectors            ←  {commands: []}

4. Click "Stop" (Frontend)      →  POST /collectors/1/stop   →  -
   Create Command               ←  {status: "ok"}             ←  -

5. Next Heartbeat               →  -                          →  POST /heartbeat
   Receive Command              ←  -                          ←  {commands: [{command: "stop"}]}
   Execute Stop                 →  -                          →  Stop Collection

6. Report Execution             →  -                          →  POST /commands/1/execute
                                ←  {status: "ok"}             ←  {success: true}

7. View Status (Frontend)       →  GET /collectors           →  -
   Show Updated Status          ←  {status: "stopped"}        ←  -
```

## Testing

### Test Manuale Completo

```bash
# 1. Verifica backend attivo
curl http://localhost:8000/health

# 2. Login frontend
# Apri http://localhost:5173
# Login con admin@dbpower.com / admin123

# 3. Vai su Collectors page
# Click su "Collectors" nella sidebar

# 4. Registra collector
# Click "+ Register Collector"
# Compila form e submit
# Copia API key mostrato

# 5. Avvia collector agent
cd collector_agent
# Crea config.json con API key copiato
python collector_agent.py --config config.json

# 6. Verifica nel frontend
# Refresh pagina Collectors
# Dovrebbe apparire collector con status "online" 🟢

# 7. Test controlli
# Click "Stop" → status diventa "stopped"
# Click "Start" → status torna "online"
# Click "Collect Now" → trigger raccolta immediata

# 8. Verifica heartbeat
# Lascia agent running
# Dopo 30s dovrebbe vedere "Last Heartbeat" aggiornato
# Stop agent → dopo 2 minuti status diventa "offline"
```

### Test Automatico

```bash
# Test backend API
./test_collector_system.sh

# Test frontend (con Cypress o Playwright - da implementare)
# npm run test:e2e
```

## Troubleshooting Frontend

### Collector non appare nella lista

1. Verifica che backend sia attivo: `curl http://localhost:8000/health`
2. Controlla console browser per errori API
3. Verifica token JWT valido (non scaduto)
4. Controlla che l'utente abbia permessi (ORG_ADMIN o SUPER_ADMIN)

### "Failed to load collectors"

- Controlla che le routes API siano configurate correttamente nel backend
- Verifica CORS settings nel backend
- Controlla network tab per vedere la risposta esatta

### Status sempre "offline"

- Verifica che collector agent stia inviando heartbeat
- Controlla logs backend: `docker logs ai-analyzer-backend`
- Verifica che health monitor sia attivo (cerca "CollectorHealthMonitor started")
- Controlla che API key sia corretta

### "Collect Now" non funziona

- Verifica che collector sia "online"
- Controlla che collector agent stia ricevendo comandi
- Guarda logs dell'agent per vedere se comando è eseguito

## Prossimi Miglioramenti Possibili

- [ ] **Real-time Updates**: WebSocket per status live senza refresh
- [ ] **Grafici Statistiche**: Chart.js per visualizzare trends
- [ ] **Filtri e Search**: Filtrare collectors per status, tipo, team
- [ ] **Bulk Operations**: Start/stop multipli collectors
- [ ] **Alert Configuration**: Configurare alerts quando collector va offline
- [ ] **Command History View**: Vedere storico comandi eseguiti
- [ ] **Edit Collector**: Modificare config senza ricreare
- [ ] **Collector Groups**: Raggruppare collectors per ambiente/progetto
- [ ] **Performance Metrics**: Grafici per queries/min, latenza, etc.
- [ ] **Export Data**: Esportare stats collectors in CSV/JSON

## Conclusioni

✅ **Frontend completamente integrato!**

- Pagina Collectors completa e funzionale
- Tutte le operazioni CRUD implementate
- UI/UX professionale con feedback visivo
- Error handling robusto
- Pronto per production testing

Il sistema è ora **end-to-end completo**: backend API + health monitoring + collector agents + frontend UI!

🚀 **Pronto per essere usato!**
