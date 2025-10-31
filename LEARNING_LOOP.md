Obiettivo

Aggiungere alla piattaforma AI Query Analyzer un meccanismo di apprendimento incrementale.
Il sistema deve:

Tracciare quali suggerimenti di ottimizzazione sono stati dati per una query lenta.

Rilevare in futuro se quella stessa query (o query equivalente) è diventata più veloce.

Calcolare un miglioramento (“gain ratio”) e classificare l’efficacia del suggerimento.

Usare questi risultati come memoria, per dare priorità ai suggerimenti che hanno funzionato meglio in passato.

Questo è il loop di feedback che rende il prodotto più intelligente nel tempo.

STEP 0. Prerequisito concettuale

Il sistema ragiona in termini di fingerprint della query.

full_sql: la query completa (con valori specifici).

fingerprint: la stessa query ma parametrizzata, es:

Query reale:
SELECT * FROM orders WHERE user_id = 1234 AND status = 'PAID';

Fingerprint:
SELECT * FROM orders WHERE user_id = ? AND status = ?;

Il fingerprint serve per riconoscere “la stessa query funzionale” anche se i parametri cambiano.

Claude deve implementare una funzione di fingerprint nella codebase (anche semplice regex iniziale va bene).

STEP 1. Aggiornare/creare i modelli dati nel DB interno

Nel DB interno dell’app (PostgreSQL interno), aggiungere/aggiornare le seguenti tabelle.
Usa SQLAlchemy nei modelli Python e crea anche migrazioni se già stiamo usando Alembic. Se Alembic non c’è ancora, per ora basta creare i modelli + uno script di init.

1.1 Tabella slow_queries_raw

Questa tabella esiste già o va creata. Deve contenere le osservazioni delle query lente così come viste dal collector.

Campi richiesti (se già esiste, assicurarsi che siano presenti / aggiungerli):

id (UUID, pk)

source_db_type (String, es. "mysql", "postgres", …)

source_db_host (String) → identifica da quale istanza arriva

fingerprint (Text)

full_sql (Text)

duration_ms (Float)

rows_examined (Integer, nullable)

rows_returned (Integer, nullable)

captured_at (DateTime timezone-aware)

plan_json (JSON/Text)

status (Enum: 'NEW' | 'ANALYZED')

Claude: se plan_json non è JSON nativo in SQLAlchemy, mantienilo come Text e lascia parsing lato Python.

1.2 Tabella analysis_result

Questa tabella mappa un’analisi AI alle singole query.

Campi richiesti:

id (UUID, pk)

slow_query_id (FK → slow_queries_raw.id)

problem (Text)

root_cause (Text)

suggestions (JSON/Text)
Esempio contenuto:

[
  "Create index on orders(status, created_at)",
  "Avoid SELECT *",
  "Add WHERE clause to reduce scan"
]


improvement_level (String: 'low' | 'medium' | 'high')

created_at (DateTime)

NUOVI campi da aggiungere ora per il learning loop:

gain_ratio (Float, nullable)
Valore tra 0 e 1: quanto è migliorata la query dopo che il suggerimento è stato applicato.

effectiveness (String, nullable)
'PENDING' | 'CONFIRMED' | 'FAILED'

Default iniziale:

gain_ratio = NULL

effectiveness = 'PENDING'

1.3 Nuova tabella feedback_history

Questa tabella registra ogni confronto “prima vs dopo” per una query (cioè ogni tentativo di misurare miglioramento).

Campi:

id (UUID, pk)

slow_query_fingerprint (Text)

analysis_result_id (FK → analysis_result.id)

old_duration_ms (Float)

new_duration_ms (Float)

gain_ratio (Float)
Calcolo: (old_duration_ms - new_duration_ms) / old_duration_ms

checked_at (DateTime, default NOW())

Claude: crea i modelli SQLAlchemy per queste tabelle e aggiorna eventuali file models.py già esistenti nella cartella backend.

STEP 2. Funzione di fingerprint

Claude deve implementare una funzione Python riutilizzabile per generare il fingerprint della query.

File target (creane uno se non esiste):
backend/services/sql_fingerprint.py

Requisiti minimi della funzione make_fingerprint(sql: str) -> str:

sostituire numeri con ?

sostituire stringhe tra apici con ?

normalizzare spazi multipli

lowercasing opzionale (va bene)

Esempio semplice:

Input:

SELECT * FROM orders WHERE user_id = 1234 AND status = 'PAID' LIMIT 10;


Output:

select * from orders where user_id = ? and status = ? limit ?


Claude: crea anche test di base per questa funzione in backend/tests/test_sql_fingerprint.py.

STEP 3. Estendere il collector

Il collector è il servizio che legge i DB esterni (es. MySQL lab) e inserisce righe in slow_queries_raw.

File interessato: backend/services/collector_service.py

Aggiungere/garantire:

Ogni volta che il collector registra una query lenta, deve:

calcolare il fingerprint con make_fingerprint().

salvare duration_ms.

Il collector NON deve generare analysis_result. Quello lo fa l’analyzer.

Il collector NON deve ancora valutare miglioramenti, solo raccogliere dati grezzi continuamente (anche dopo l’ottimizzazione).

STEP 4. Analyzer: generare suggerimenti

backend/services/analyzer_service.py

Questa parte forse esiste già in bozza. Ora deve fare:

Prendere tutte le righe di slow_queries_raw con status = 'NEW'.

Per ognuna:

Recuperare lo schema del DB sorgente (indici, tabelle, ecc.).

Applicare regole statiche (da backend/services/rules.py).

Preparare eventuale prompt per AI LLM (ma se non c’è ancora la chiamata esterna, stubbare).

Creare una riga in analysis_result con:

slow_query_id

problem

root_cause

suggestions (lista JSON)

improvement_level

effectiveness = 'PENDING'

gain_ratio = NULL

Aggiornare slow_queries_raw.status = 'ANALYZED'.

Claude: Assicurati di avere una funzione tipo analyze_pending_queries() e un endpoint admin POST /analyze/run che la chiama.

STEP 5. Learning loop: detect improvement

Qui costruiamo il cuore dell’“impara nel tempo”.

Claude deve creare un nuovo modulo:
backend/services/learning_service.py

In questo modulo definire una funzione:

def evaluate_suggestion_effectiveness(session):
    """
    1. Trova tutte le analysis_result con effectiveness='PENDING'.
    2. Per ciascuna, identifica il fingerprint associato (tramite slow_queries_raw).
    3. Prende le misure "prima" e "dopo" della stessa query (stesso fingerprint) per vedere se è migliorata.
    4. Se migliorata in modo significativo, aggiorna gain_ratio e effectiveness.
    5. Scrive una riga in feedback_history.
    """


Specifiche tecniche della funzione:

5.1 Recupero “prima”

Per l’analysis_result corrente ottieni il suo slow_query_id.

Dal slow_queries_raw originale (quello collegato), prendi:

fingerprint

duration_ms originale (chiamiamola old_duration_ms)

captured_at (chiamiamola old_time)

5.2 Recupero “dopo”

Cerca nella tabella slow_queries_raw altre righe con:

stesso fingerprint

captured_at più recente di old_time + una finestra di tolleranza (es. almeno 10 minuti / N ore dopo)

Calcola la nuova durata media sulle osservazioni più recenti della stessa query (es. media delle ultime 5).

Se non trovi abbastanza osservazioni (es. la query non è più stata eseguita), salta e lascia effectiveness='PENDING'.

5.3 Calcolo gain_ratio
gain_ratio = (old_duration_ms - new_duration_ms) / old_duration_ms


Se gain_ratio < 0 → peggiorata: effectiveness='FAILED'

Se gain_ratio tra 0 e 0.3 → miglioramento piccolo: effectiveness='PENDING' (continua a monitorare)

Se gain_ratio ≥ 0.3 → considerala efficace: effectiveness='CONFIRMED'

(Le soglie sono nostre, hardcoded per ora. Claude deve metterle in costanti tipo IMPROVEMENT_THRESHOLD = 0.3 in cima al file.)

5.4 Salvataggio

Aggiorna la row di analysis_result con:

gain_ratio

effectiveness (CONFIRMED / FAILED)

Inserisci una nuova row in feedback_history con:

fingerprint

analysis_result_id

old_duration_ms

new_duration_ms

gain_ratio

checked_at = now()

Claude: questa funzione deve essere idempotente (cioè se la rilanci, non deve duplicare record in feedback_history inutilmente). La logica più semplice è: prima di creare un nuovo feedback_history controlla se esiste già una entry per quella analysis_result_id con un checked_at recente.

STEP 6. Scheduler

Claude deve aggiungere un job periodico (può mettere APScheduler nel backend, o in un modulo worker/ separato se abbiamo già un container worker) che:

ogni N minuti esegue:

collect_mysql_slow_queries()
(per aggiornare slow_queries_raw)

ogni M minuti esegue:

analyze_pending_queries()
(per popolare analysis_result)

ogni X minuti esegue:

evaluate_suggestion_effectiveness()
(per aggiornare gain_ratio e effectiveness)

Suggerimento:

N = 1 minuto

M = 5 minuti

X = 30 minuti

Claude deve creare un file tipo:
backend/scheduler.py
con APScheduler che schedula queste tre funzioni.

Lo scheduler può essere avviato in main.py quando parte FastAPI, oppure in un container separato “worker”.
Per MVP va bene avviarlo da FastAPI (blocco startup event di FastAPI).

STEP 7. Esporre il valore in API (per la dashboard)

Aggiornare/creare route API in backend/api/routes/slow_queries.py e backend/api/routes/stats.py:

GET /slow-queries

Restituisce elenco delle query lente (raggruppate per fingerprint), incluse:

fingerprint

avg duration attuale

effectiveness_best (lo stato migliore raggiunto da qualunque suggerimento associato a quel fingerprint: es. CONFIRMED vs FAILED)

last_suggestion_gain (max gain_ratio confermato)

GET /slow-queries/{id}

Restituisce:

full_sql

plan_json (formattato)

suggestions (dall’analysis_result)

effectiveness

gain_ratio (se presente)

timeline (storico da feedback_history se disponibile)

Questo serve al frontend React per mostrare:

“Questa query era lenta”

“L’AI ha detto di fare X”

“Dopo X, ora è 4x più veloce ✅”

Che è esattamente quello che convince un CTO a pagare.

STEP 8. Aggiornare README / documentazione

Claude deve aggiornare il README principale della piattaforma con una nuova sezione chiamata “Learning loop / auto-miglioramento”, che spiega in poche righe:

Il sistema propone ottimizzazioni per query lente.

Poi monitora se la query migliora davvero.

Se sì, marca quel suggerimento come CONFIRMED e calcola il gain_ratio.

Il gain_ratio viene usato per dare più priorità in futuro a raccomandazioni simili.

Questo crea un ciclo di apprendimento progressivo dell’ottimizzatore.

TL;DR per Claude

Aggiungi/modifica i modelli SQLAlchemy (slow_queries_raw, analysis_result, feedback_history) con i campi descritti.

Implementa make_fingerprint(sql) e i relativi test.

Aggiorna il collector per salvare fingerprint e durata.

Aggiorna analyzer per segnare suggerimenti con effectiveness='PENDING'.

Implementa learning_service.evaluate_suggestion_effectiveness() con calcolo gain_ratio e aggiornamento analysis_result + inserimento feedback_history.

Aggiungi uno scheduler periodico che esegue collect → analyze → evaluate.

Estendi le API FastAPI per esporre tutte queste informazioni al frontend.