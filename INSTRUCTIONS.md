Perfetto Mirko 🔥
Ti preparo un **documento d’istruzioni completo** che puoi dare direttamente a **Claude Code** (o a un dev AI assistant) nella cartella del progetto, per fargli generare *tutto il setup: Docker, schema, dati, query lente e traffico simulato*.

Questo file lo puoi chiamare ad esempio `INSTRUCTIONS.md`.

---

## 🧾 `INSTRUCTIONS.md`

### 🎯 Obiettivo

Costruire un ambiente Docker completo per simulare un database MySQL con query lente, mal ottimizzate e con casi di indici mancanti o errati.
Questo ambiente servirà come **sandbox di testing** per sviluppare e validare un agente AI di ottimizzazione SQL.

---

### 🧩 Struttura del progetto

```
ai-query-lab/
│
├── docker-compose.yml
├── mysql/
│   ├── init.sql             # Schema e seed data
│   └── simulate_slow_queries.py  # Script di traffico finto
│
├── README.md                # Spiega come avviare e usare il lab
└── .env                     # Credenziali e configurazioni
```

---

### ⚙️ 1. Configurazione Docker Compose

Claude deve creare un `docker-compose.yml` con **un solo container MySQL 8.0**, configurato per:

* porta host `3307`;
* database `labdb`;
* utente root/password `root`;
* `slow_query_log` attivo.

Esempio desiderato:

```yaml
version: '3.8'

services:
  mysql-lab:
    image: mysql:8.0
    container_name: mysql-lab
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: labdb
    ports:
      - "3307:3306"
    command: >
      --slow_query_log=1
      --long_query_time=0.5
      --log_output=TABLE
      --default-authentication-plugin=mysql_native_password
    volumes:
      - ./mysql/init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./data/mysql-lab:/var/lib/mysql
```

---

### ⚙️ 2. File `mysql/init.sql`

Claude deve creare uno script SQL che:

1. Crea le tabelle:

   * `users(id, name, email, country, created_at)`
   * `orders(id, user_id, product, price, status, created_at)`

2. Inserisce:

   * ~200.000 utenti
   * ~500.000 ordini

3. Non deve creare indici inizialmente (eccetto le PK).

4. Crea **una stored procedure** per popolare rapidamente i dati (`fill_data()`).

5. Alla fine può aggiungere **query di esempio lente** (commentate) per test manuale:

   ```sql
   -- SELECT * FROM orders WHERE product LIKE '%phone%' AND status='PAID';
   -- SELECT u.name, o.product FROM users u JOIN orders o ON u.id=o.user_id WHERE u.country='IT';
   ```

---

### ⚙️ 3. File `.env`

```bash
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DB=labdb
```

---

### ⚙️ 4. File `mysql/simulate_slow_queries.py`

Claude deve creare uno script Python che:

* si connette al DB usando i parametri di `.env`;
* esegue ciclicamente 2–3 query volutamente lente (come quelle sopra);
* dorme 0.5–2 secondi tra le query;
* genera traffico continuo per popolare `mysql.slow_log`.

Esempio logica base:

```python
import mysql.connector, random, time, os

conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=os.getenv("MYSQL_PORT", 3307),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", "root"),
    database=os.getenv("MYSQL_DB", "labdb")
)
cur = conn.cursor()

queries = [
    "SELECT * FROM orders WHERE product LIKE '%phone%' AND status='PAID'",
    "SELECT u.name, o.product, o.price FROM users u JOIN orders o ON u.id=o.user_id WHERE u.country='IT' AND o.status='SHIPPED'",
    "SELECT country, COUNT(*) FROM users GROUP BY country ORDER BY COUNT(*) DESC"
]

while True:
    q = random.choice(queries)
    t0 = time.time()
    cur.execute(q)
    cur.fetchall()
    elapsed = time.time() - t0
    print(f"Executed in {elapsed:.2f}s: {q[:80]}...")
    time.sleep(random.uniform(0.5, 2.0))
```

---

### ⚙️ 5. File `README.md`

Claude deve scrivere un README con:

#### 🔧 Setup

```bash
docker compose up -d
```

#### 🧠 Popola i dati

MySQL esegue automaticamente `init.sql` al primo avvio.
Puoi controllare i dati:

```bash
docker exec -it mysql-lab mysql -uroot -proot -e "USE labdb; SHOW TABLES;"
```

#### 🚀 Simula query lente

Esegui:

```bash
python3 mysql/simulate_slow_queries.py
```

#### 📊 Controlla le query lente

```bash
docker exec -it mysql-lab mysql -uroot -proot -e "SELECT start_time, query_time, sql_text FROM mysql.slow_log ORDER BY query_time DESC LIMIT 10;"
```

---

### ⚙️ 6. Bonus (facoltativo per Claude)

Claude può aggiungere:

* un comando `Makefile` tipo `make run-lab` che fa partire tutto;
* o un piccolo script `query_examples.sql` con più query “rotte”;
* o un Dockerfile Python separato per lanciare lo script di simulazione come container.

---

### 🎯 Output finale desiderato

Dopo che Claude ha completato i file:

1. `docker compose up -d` → crea e popola il DB.
2. `python3 mysql/simulate_slow_queries.py` → genera traffico lento.
3. `SELECT * FROM mysql.slow_log` → mostra le query lente reali.
4. Questi dati serviranno poi come input per l’agente AI di analisi.


***ARCHITETTURA e PIANO PER IMPLEMENTAZIONE
Perfetto Mirko ❤️‍🔥
Adesso ti do il prompt “master” che puoi dare a Claude Code per farti generare tutto passo dopo passo.
Questo prompt definisce: obiettivo, architettura, stack, ordine di esecuzione e criteri di qualità.
È pensato perché Claude non inventi ma lavori in modo incrementale e modulare.

Ti consiglio di salvarlo in un file tipo `BUILD_PLAN.md` nella root e poi incollarlo a Claude a blocchi (o tutto intero se regge).
Io ora te lo do già ottimizzato.

---

## PROMPT MASTER PER CLAUDE CODE

**CONTESTO PROGETTO**
Stiamo costruendo una piattaforma chiamata `AI Query Analyzer`.
Questa piattaforma deve:

1. Collegarsi a vari database SQL (MySQL 8, PostgreSQL 15, Oracle XE, SQL Server 2022).
2. Individuare query lente.
3. Ottenere e normalizzare il piano di esecuzione di quella query.
4. Analizzare il piano e la struttura del database (tabelle, indici, cardinalità).
5. Generare suggerimenti di ottimizzazione (nuovi indici, riscrittura query, partizionamento, ecc.), usando sia regole statiche che un modello AI LLM.
6. Esporre tutto in una dashboard web (UI) e in API REST.

La piattaforma avrà una versione demo in locale, con database “di laboratorio” popolati con dati realistici e query lente simulate.

---

## ARCHITETTURA LOGICA (ALTA LIVELLO)

1. **db_lab/**

   * Contiene docker-compose per simulare i database (MySQL lab, Postgres lab, ecc.).
   * Ogni DB viene popolato con dati (users, orders), senza indici ottimali all’inizio, così le query sono lente.
   * Esistono script per generare traffico e riempire lo slow log.

2. **backend/**

   * FastAPI (Python).
   * Espone API REST:

     * `/slow-queries` → elenco query lente note
     * `/slow-queries/{id}` → dettagli, piano di esecuzione, suggerimenti
     * `/stats` → statistiche aggregate
   * Fornisce endpoint interni per il collector e l’analyzer.

3. **worker/**

   * Processi periodici (scheduler/cron style) che fanno due cose:

     * **collector**: interroga i database target, legge le query lente (es. `mysql.slow_log`, `pg_stat_statements`, ecc.), genera l’`EXPLAIN` e salva tutto nel DB interno dell’app.
     * **analyzer**: prende le query raccolte, aggiunge il contesto di schema/indici, applica regole statiche, chiama il modello AI e salva il risultato come raccomandazione.

4. **internal-db (PostgreSQL interno)**

   * DB interno dell’app.
   * Serve a salvare:

     * query lente osservate
     * piani di esecuzione normalizzati
     * suggerimenti dell’AI
     * snapshot di metadati dei DB esterni (schema, indici)

5. **frontend/**

   * React + Tailwind.
   * Mostra lista query lente, livello criticità, durata media, etc.
   * Mostra i suggerimenti di ottimizzazione generati dall’AI, e il piano di esecuzione in forma leggibile.

---

## TECH STACK OBBLIGATORIO

* **Collector / Analyzer / API backend** → Python 3.12, FastAPI, SQLAlchemy.
* **Scheduler per job periodici** → APScheduler o Celery (con Redis). Preferire APScheduler per MVP se più semplice.
* **DB interno dell’app** → PostgreSQL 15.
* **Frontend** → React 18 + Vite + TailwindCSS.
* **Autenticazione** → nessuna per MVP.
* **AI model client** → lasciare interfaccia astratta (es. `ai_provider.py`) con funzione `analyze_query(plan, schema, stats)`. Non mettere direttamente chiavi API o provider hardcoded.
* **Containerization** → docker-compose multilayer.

---

## REQUISITI DI QUALITÀ

* Il codice deve essere modulare e production-style (file separati, niente monoblocco da 1000 righe).
* Tutto il codice deve essere eseguibile senza modifiche manuali ambigue (es: se serve una variabile d’ambiente, deve essere definita in `.env.example`).
* Commenti chiari e brevi sul “perché”, non solo sul “cosa”.
* Quando crei uno script o un servizio, devi anche aggiornare la documentazione (README o commento nel BUILD_PLAN).
* Tutti gli accessi ai DB esterni devono essere parametrizzati (host, porta, user, pass, dbname) e NON hardcodati nel codice. Usa un piccolo file `config.py` che legge la config da env.

---

## ROADMAP DI IMPLEMENTAZIONE (STEP OPERATIVI)

Claude, implementa nell’ordine seguente.
Dopo aver completato uno step, passa allo step successivo.

---

### STEP 1. Setup laboratorio database (`db_lab/`)

Obiettivo: avere ambienti SQL realistici su cui girano query lente.

1. Crea cartella `db_lab/` con sottocartelle:

   * `db_lab/db/mysql/`
   * `db_lab/db/postgres/`
   * `db_lab/db/oracle/`
   * `db_lab/db/sqlserver/`
   * `db_lab/scripts/`
   * `db_lab/data/` (vuota, per i volumi)

2. Crea `db_lab/docker-compose.yml` che avvia:

   * `mysql-lab` su porta host 3307
   * `postgres-lab` su porta host 5433
     (Oracle e SQL Server li possiamo aggiungere dopo, ma lascia placeholder commentati nel file)

   Requisiti:

   * `mysql-lab` deve montare `init.sql` all’avvio per creare tabelle `users` e `orders` e popolarle (200k users, 500k orders).
   * deve abilitare slow query log (`--slow_query_log=1`, `--long_query_time=0.5`, `--log_output=TABLE`).
   * `postgres-lab` deve montare un `init.sql` che crea tabelle simili e inserisce dati (anche meno record va bene, tipo 50k users / 150k orders).

3. In `db_lab/db/mysql/init.sql`:

   * Crea `users` e `orders`.
   * Inserisci dati massivi senza indici ottimali (solo PK e qualche index basic).
   * Lascia commentate alcune query lente di esempio.
   * NON creare ancora indici “buoni” (tipo `idx_orders_user_status`) perché ci servono i casi lenti.

4. Crea script Python `db_lab/db/mysql/simulate_slow_queries.py`:

   * Si connette al MySQL lab (usa `.env` alla root del repo principale, fare riferimento a `MYSQL_HOST`, `MYSQL_PORT`, etc.).
   * Esegue in loop alcune query volutamente inefficienti (JOIN grossa, LIKE con `%`, GROUP BY senza indice).
   * Stampa tempi di esecuzione.
   * Serve a riempire `mysql.slow_log`.

5. Aggiungi in `db_lab/scripts/`:

   * `setup_mysql.sh`: alza solo MySQL (docker compose up -d sul servizio MySQL), aspetta un po’, e poi fa `SET GLOBAL slow_query_log...`.
   * `setup_postgres.sh`: alza solo Postgres e abilita logging di query lente (es. `log_min_duration_statement`).
   * `setup_all.sh`: chiama entrambi.

Output atteso di questo step:

* possiamo eseguire `docker compose up -d` dentro `db_lab/`, poi `python3 db/mysql/simulate_slow_queries.py`, e vedere dati nello `slow_log` MySQL.

---

### STEP 2. DB interno dell’app e modello dati

Obiettivo: definire lo storage centrale di tutto quello che raccogliamo.

1. Crea nella root del progetto un servizio Postgres interno (es. `internal-db`) nel docker-compose principale (NON quello di `db_lab/`).

   * Porta host: 5440 (per non scontrarsi con 5433 del lab).
   * DB name: `ai_core`
   * user/pass: `ai_core/ai_core`

2. Definisci schema SQL (o modello SQLAlchemy) per queste tabelle:

   * `slow_queries_raw`:

     * id (uuid)
     * source_db_type (`mysql`, `postgres`, …)
     * source_db_host
     * fingerprint (query parametrizzata)
     * full_sql (query completa originale)
     * duration_ms
     * rows_examined
     * rows_returned
     * captured_at (timestamp)
     * plan_json (JSON/text)
     * status (`NEW`, `ANALYZED`)

   * `db_metadata`:

     * id
     * source_db_type
     * captured_at
     * tables (JSON) → nome tabella, righe stimate
     * indexes (JSON) → tabella, colonne, unique
     * relations (JSON)

   * `analysis_result`:

     * id (uuid)
     * slow_query_id (fk → slow_queries_raw.id)
     * problem (text)
     * root_cause (text)
     * suggestions (JSON array)
     * improvement_level (`low` | `medium` | `high`)
     * analyzed_at (timestamp)

3. Claude deve generare i modelli SQLAlchemy corrispondenti e un file `backend/db/session.py` per gestire connessione a questo Postgres interno via env vars.

---

### STEP 3. Backend FastAPI (`backend/`)

Obiettivo: API REST per visualizzare e servire i dati alla UI.

1. Crea cartella `backend/` con struttura:

   * `backend/main.py` → crea l’app FastAPI e monta le route
   * `backend/api/routes/slow_queries.py`
   * `backend/api/routes/stats.py`
   * `backend/services/collector_service.py`
   * `backend/services/analyzer_service.py`
   * `backend/services/rules.py`
   * `backend/core/config.py` → legge variabili ambiente (.env) e fornisce settings
   * `backend/core/logger.py`

2. Implementa endpoint base:

   * `GET /slow-queries`
     Ritorna lista di query lente (group by fingerprint, con durata media e count).
   * `GET /slow-queries/{id}`
     Ritorna dettaglio di una query lenta specifica, incluso piano e suggerimenti se esistono.
   * `GET /stats/top-tables`
     Ritorna le tabelle che compaiono più spesso nei piani lenti (derivato da `plan_json` o da `analysis_result.suggestions`).

3. Gli endpoint devono leggere dal DB interno (Postgres interno) usando SQLAlchemy.

4. Aggiungi un Dockerfile per il backend (python:3.12-slim) + requirements.txt con:

   * fastapi
   * uvicorn[standard]
   * sqlalchemy
   * psycopg2-binary
   * python-dotenv
   * pydantic
   * mysql-connector-python
   * psycopg2
   * (non ancora: oracle + sqlserver drivers; lasciali TODO)

---

### STEP 4. Collector (prima versione)

Obiettivo: pescare le query lente da MySQL lab e buttarle nel DB interno.

1. Crea `backend/services/collector_service.py` con funzioni:

   * `collect_mysql_slow_queries()`:

     * Connette al MySQL lab usando env vars `MYSQL_HOST`, ecc.
     * Legge le query lente da `mysql.slow_log` (`start_time`, `query_time`, `sql_text`, `rows_sent`, `rows_examined` se disponibile).
     * Per ogni query:

       * calcola `fingerprint` banalmente sostituendo valori numerici/stringhe con `?`. (per ora semplice regex)
       * esegue `EXPLAIN FORMAT=JSON <query>`, salva il piano.
       * inserisce una riga in `slow_queries_raw` (status = `NEW`) se non esiste già una riga identica di recente.

   Nota: se la query non è una `SELECT` sicura (es. UPDATE/DELETE), per ora saltala.

2. Aggiungi endpoint interno admin:

   * `POST /collect/mysql`
     Chiama `collect_mysql_slow_queries()` e ritorna quante nuove query lente ha salvato.

Questo è importante perché ci serve la pipeline end-to-end.

---

### STEP 5. Analyzer (prima versione)

Obiettivo: generare suggerimenti.

1. Crea `backend/services/rules.py` con alcune euristiche statiche, ad esempio:

   * Se il piano dice `access_type: "ALL"` su tabella con >100k righe → suggerisci “manca indice sul filtro WHERE”.
   * Se c’è `JOIN` tra tabelle grandi e tipo join è `Nested Loop` → suggerisci di valutare indice sulle colonne di join.
   * Se c’è `filesort` / `Using temporary` → suggerisci indice su colonne di `ORDER BY`.

2. Crea `backend/services/analyzer_service.py`:

   * Funzione `analyze_pending_queries()`:

     * Prende da `slow_queries_raw` tutte le righe con `status = 'NEW'`.
     * Recupera lo schema del DB sorgente (tabelle, indici) e allegalo al contesto.

       * Per MySQL: usa `information_schema.tables`, `information_schema.statistics`, `information_schema.key_column_usage`.
     * Applica le regole statiche (rules.py) per produrre una prima bozza “spiegazione + suggerimenti”.
     * (Stub per AI LLM): prepara un payload tipo
       `{"problem": "...", "root_cause": "...", "suggestions": [...], "improvement_level": "high"}`
     * Salva tutto in `analysis_result`.
     * Aggiorna `slow_queries_raw.status = 'ANALYZED'`.

3. Aggiungi endpoint interno admin:

   * `POST /analyze/run`
     Esegue `analyze_pending_queries()` e ritorna quante query sono state analizzate.

Questo ci dà il loop minimo funzionante.

---

### STEP 6. Frontend React

Obiettivo: visualizzare quello che abbiamo.

1. Crea cartella `frontend/` con Vite + React + Tailwind.

   * Pagine principali:

     * `QueryList.tsx`
       Chiama `GET /slow-queries` e mostra: fingerprint, durata media, frequenza, livello criticità.
     * `QueryDetail.tsx`
       Chiama `GET /slow-queries/{id}` e mostra:

       * SQL originale (offuscato/mascherato se possibile)
       * Piano di esecuzione formattato (JSON prettificato)
       * Suggerimenti dell’AI (lista bullet con “impatto: alto/medio/basso”)
   * Component `SeverityBadge.tsx`
   * Component `PlanViewer.tsx`

2. Crea un client API (es: `frontend/src/api/client.ts`) che punta all’URL del backend (es. `http://localhost:8000` o quello del compose).

---

### STEP 7. Docker Compose principale

Obiettivo: far girare tutto insieme.

1. Nella root (NON dentro `db_lab/`) crea `docker-compose.yml` con servizi:

   * `internal-db` (Postgres interno)
   * `redis` (se decidi Celery; se usi solo APScheduler puoi saltarlo)
   * `backend`
   * `frontend`

2. Il `backend` deve dipendere da `internal-db`.

3. Il `frontend` deve avere accesso al `backend` (esporta la porta 5173 e punta al backend con env).

4. NON includere `mysql-lab` e `postgres-lab` qui dentro: restano nel compose separato sotto `db_lab/`. Li alzi a parte.

---

### STEP 8. Documentazione

Aggiorna/crea file `README.md` nella root del progetto con:

* come avviare i DB di laboratorio (cd db_lab && docker compose up -d)
* come avviare l’app (docker compose up -d nella root)
* come generare traffico lento (script Python)
* come forzare una raccolta (`curl -X POST /collect/mysql`)
* come forzare un’analisi (`curl -X POST /analyze/run`)

---

## NOTE FINALI PER CLAUDE

* Ogni volta che crei file nuovi, aggiornali nella struttura directory.
* Non inserire segreti reali. Usa `.env.example` con placeholder.
* Per i driver Oracle e SQL Server puoi lasciare TODO/commenti, non è necessario che siano immediatamente funzionanti in questa fase.
* Quando fai query SQL raw in Python, aggiungi sempre commento con:
  `# NOTE: questa query gira SOLO su MySQL` o `# NOTE: questa è Postgres specific`.
* L’obiettivo del MVP è:

  * Lanciare query lente su MySQL lab
  * Collettarle
  * Analizzarle
  * Visualizzarle in dashboard

