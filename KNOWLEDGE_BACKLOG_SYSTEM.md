# 🧠 Knowledge Backlog System — AI Query Analyzer

## 🎯 Obiettivo

Progettare e implementare un **sistema di knowledge backlog** per l’applicazione `AI Query Analyzer`.

Questo sistema consente di:

1. **Archiviare i casi di ottimizzazione SQL**: ogni volta che una query viene analizzata, ottimizzata e monitorata, i dati vengono salvati.
2. **Riconoscere pattern ricorrenti**: individuare quali tipi di problemi e soluzioni funzionano meglio.
3. **Fornire esempi di casi simili** alle nuove query lente (per potenziare il motore AI con RAG).
4. **Generare dataset strutturati** per addestrare o fine-tuning di modelli AI specializzati in ottimizzazione SQL.

---

## 🧩 Architettura generale

```text
[Collector] → [Analyzer AI] → [Feedback Loop] → [Knowledge Backlog]
                                               ↘ [Training Dataset Builder]
Collector → registra le query lente e i piani di esecuzione.

Analyzer AI → propone ottimizzazioni e salva i suggerimenti.

Feedback Loop → valuta se la query è migliorata dopo l’applicazione del fix.

Knowledge Backlog → archivia tutti i casi completi (input, azione, risultato).

Dataset Builder → esporta i casi confermati in un formato adatto al training AI.

🧱 STEP 1 — Schema dati
Nuova tabella PostgreSQL: knowledge_backlog.

Campo	Tipo	Descrizione
id	UUID (PK)	Identificatore univoco del caso
fingerprint	TEXT	Query normalizzata (parametrizzata)
db_type	VARCHAR(20)	mysql / postgres / oracle / sqlserver
full_sql	TEXT	Query originale (anonimizzata)
plan_json	JSON	Piano di esecuzione originale
schema_context	JSON	Tabelle, indici, cardinalità
suggestions	JSON	Raccomandazioni AI e regole
applied_fix	JSON	Soluzione applicata (se nota)
old_duration_ms	FLOAT	Tempo medio prima
new_duration_ms	FLOAT	Tempo medio dopo
gain_ratio	FLOAT	(old-new)/old
effectiveness	VARCHAR(20)	pending / confirmed / failed
analyzer_version	VARCHAR(20)	Versione del motore AI
created_at	TIMESTAMP	Data creazione caso
updated_at	TIMESTAMP	Ultima revisione

🔸 Indici raccomandati:

(fingerprint, db_type)

(effectiveness)

⚙️ STEP 2 — Popolamento automatico
Ogni volta che un’analisi ha effectiveness='CONFIRMED', viene aggiunta una riga nel backlog.

File target:
backend/services/learning_service.py

python
Copia codice
def persist_to_backlog(session, analysis_result):
    """
    Crea o aggiorna un record nel knowledge_backlog per un suggerimento confermato.
    Prende dati da slow_queries_raw, analysis_result e feedback_history.
    """
Flusso:

Recupera slow_queries_raw (query, piano, fingerprint, db_type).

Recupera analysis_result (suggerimenti, livello di miglioramento, AI version).

Recupera feedback_history (gain_ratio, tempi prima/dopo).

Inserisce/aggiorna record nel backlog.

🧩 STEP 3 — Anonimizzazione automatica
Modulo:
backend/utils/anonymizer.py

python
Copia codice
def anonymize_sql(sql: str) -> str
Requisiti:
Sostituire nomi di tabelle/colonne con placeholder (table_1, col_2).

Sostituire valori letterali con ?.

Mantenere struttura e parole chiave SQL.

Esempio:

sql
Copia codice
SELECT user_id, amount FROM payments WHERE user_id = 123;
→

sql
Copia codice
SELECT col_1, col_2 FROM table_1 WHERE col_1 = ?;
Anche i riferimenti in plan_json devono essere anonimizzati.

🧠 STEP 4 — Retrieval Engine (RAG)
Modulo:
backend/services/knowledge_retriever.py

python
Copia codice
def find_similar_cases(fingerprint: str, db_type: str, plan_json: dict, limit: int = 5) -> list:
    """
    Restituisce i casi più simili nel knowledge backlog per pattern di query o piano.
    """
Funzionalità:
Calcola embedding o hash (simhash, levenshtein, ecc.).

Confronta fingerprint e caratteristiche di piano.

Restituisce fino a 5 casi con:

fingerprint simile

suggerimento applicato

gain medio

tipo di problema risolto

👉 Usato dal modulo Analyzer per proporre soluzioni “già verificate”.

📦 STEP 5 — Dataset Builder
Modulo:
backend/utils/dataset_builder.py

python
Copia codice
def export_training_dataset(session, output_path: str, min_gain: float = 0.3):
    """
    Estrae tutti i casi confermati con gain_ratio >= min_gain
    e li salva in formato JSONL per fine-tuning o RAG dataset.
    """
Formato JSONL:
Ogni riga = 1 caso di successo

json
Copia codice
{
  "input": {
    "db_type": "mysql",
    "fingerprint": "select * from orders where status = ?",
    "plan_json": {"type": "ALL", "rows_examined": 250000},
    "schema_context": {"orders": {"rows": 250000, "indexes": []}}
  },
  "output": {
    "suggestion": "create index on orders(status)",
    "gain_ratio": 0.94
  }
}
CLI script:
File: backend/scripts/export_dataset.py

bash
Copia codice
python backend/scripts/export_dataset.py --min_gain 0.5 --output data/training_set.jsonl
🌐 STEP 6 — API REST per il Backlog
Nuovo modulo: backend/api/routes/knowledge.py

Endpoint	Metodo	Descrizione
/knowledge	GET	Lista dei casi, filtrabile per db_type, effectiveness, min_gain
/knowledge/similar	GET	Trova i casi più simili dato fingerprint e db_type
/knowledge/{id}	GET	Dettaglio completo del caso
/knowledge/export	POST	Genera dataset JSONL e restituisce percorso file

⚙️ STEP 7 — Estensioni future (commenti da inserire nel codice)
🔹 Clustering automatico dei casi simili (“pattern di join non indicizzato”).

🔹 Ranking dinamico delle regole statiche in base all’efficacia media.

🔹 API per statistiche aggregate (success rate, guadagno medio, tipologia problema più frequente).

🔹 Pipeline di fine-tuning con dataset generati (HuggingFace / OpenAI).

📈 Benefici
Aspetto	Valore
Automazione	Impara dai casi reali senza supervisione manuale
Scalabilità	Ogni installazione arricchisce la base di conoscenza
Precisione AI	I nuovi casi usano esempi simili già risolti (RAG)
Training dataset	Crea un asset proprietario per fine-tuning
Business value	Trasforma l’esperienza d’uso in valore cumulativo

💥 Review tecnica finale
✔️ Crea un loop virtuoso di apprendimento: ogni ottimizzazione confermata diventa conoscenza.
✔️ Permette di estrarre dataset di alta qualità, già strutturati e anonimizzati.
✔️ Fornisce memoria storica per debugging e analisi future.
⚠️ Anonimizzazione essenziale prima di ogni condivisione esterna.

💡 Risultato finale:

Il tuo AI Query Analyzer diventa un AI DBA auto-addestrante, che impara dai propri successi e costruisce nel tempo un archivio di ottimizzazioni verificabili e riutilizzabili.