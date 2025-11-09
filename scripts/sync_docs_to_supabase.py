import os, glob, json, time, requests
from openai import OpenAI

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def embed_text(text: str, retries=2, delay=2.0):
    for attempt in range(retries + 1):
        try:
            resp = client.embeddings.create(model="text-embedding-3-small", input=text)
            return resp.data[0].embedding
        except Exception as e:
            if attempt < retries:
                print(f"   ⚠️ Retry {attempt+1}/{retries} after error: {e}")
                time.sleep(delay)
            else:
                raise

def chunk_text(text: str, size: int = 800, overlap: int = 100):
    words = text.split()
    for i in range(0, len(words), size - overlap):
        yield " ".join(words[i:i + size])

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

paths = [
    p for p in glob.glob("**/*.md", recursive=True)
    if "node_modules" not in p and "venv" not in p and "dist" not in p
]

print(f"📚 Found {len(paths)} markdown files to sync.\n")

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
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/project_docs?file_name=eq.{file_name}",
            headers=headers
        )

        for i, chunk in enumerate(chunks):
            embedding = embed_text(chunk)
            data = {
                "id": f"{path}_{i}",
                "file_name": file_name,
                "chunk_index": i,
                "content": chunk,
                "embedding": embedding,
            }
            res = requests.post(
                f"{SUPABASE_URL}/rest/v1/project_docs",
                headers=headers,
                data=json.dumps(data)
            )
            if res.status_code not in (200, 201):
                print(f"   ❌ Upload failed ({res.status_code}): {res.text}")
                errors += 1
            else:
                uploaded += 1

    except Exception as e:
        print(f"❌ Error processing {path}: {e}")
        errors += 1

print("\n✅ Sync completed.")
print(f"   Uploaded chunks: {uploaded}")
print(f"   Errors: {errors}")
