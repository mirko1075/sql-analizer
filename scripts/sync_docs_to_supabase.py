import os
import glob
import time
from openai import OpenAI
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

def embed_text(text: str, retries: int = 2, delay: float = 2.0):
    """Crea embedding con retry automatico"""
    for attempt in range(retries + 1):
        try:
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return resp.data[0].embedding
        except Exception as e:
            if attempt < retries:
                print(f"   ⚠️ Retry {attempt+1}/{retries} after error: {e}")
                time.sleep(delay)
            else:
                raise

def chunk_text(text: str, size: int = 800, overlap: int = 100):
    """Divide il testo in blocchi con overlap"""
    words = text.split()
    for i in range(0, len(words), size - overlap):
        yield " ".join(words[i:i + size])

# Trova tutti i file Markdown nel progetto
paths = [
    p for p in glob.glob("**/*.md", recursive=True)
    if "node_modules" not in p and "venv" not in p and "dist" not in p
]

print(f"📚 Found {len(paths)} markdown files to sync.\n")

total_chunks = 0
uploaded = 0
errors = 0

for path in paths:
    try:
        with open(path, "r") as f:
            content = f.read()

        file_name = os.path.basename(path)
        chunks = list(chunk_text(content))
        print(f"→ Syncing {file_name} ({len(chunks)} chunks)")

        # Cancella i vecchi chunk dello stesso file
        supabase.table("project_docs").delete().eq("file_name", file_name).execute()

        for i, chunk in enumerate(chunks):
            try:
                embedding = embed_text(chunk)
                data = {
                    "id": f"{path}_{i}",
                    "file_name": file_name,
                    "chunk_index": i,
                    "content": chunk,
                    "embedding": embedding,
                }

                for attempt in range(2):  # 2 tentativi per Supabase
                    try:
                        supabase.table("project_docs").insert(data).execute()
                        uploaded += 1
                        total_chunks += 1
                        break
                    except Exception as e:
                        if attempt == 0:
                            print(f"   ⚠️ Supabase retry: {e}")
                            time.sleep(1)
                        else:
                            raise

            except Exception as e:
                print(f"   ❌ Chunk {i} failed: {e}")
                errors += 1

    except Exception as e:
        print(f"❌ Error processing file {path}: {e}")
        errors += 1

print("\n✅ Sync completed.")
print(f"   Files processed: {len(paths)}")
print(f"   Chunks uploaded: {uploaded}")
print(f"   Total errors: {errors}")
