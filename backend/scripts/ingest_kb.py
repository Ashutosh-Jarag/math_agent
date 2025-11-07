# scripts/ingest_kb_gemini.py
import os, time, json
import pandas as pd
from dotenv import load_dotenv
import requests
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

# =============================================
# Load environment variables
# =============================================
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("COLLECTION_NAME", "math_kb")
# ✅ Correct model name for Gemini embeddings API
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "embedding-001")

CSV_PATH = "data/math_kb.csv"

# =============================================
# Gemini embedding function (v1beta endpoint)
# =============================================
def embed_batch(texts):
    """
    Generate embeddings using Gemini's 'embedding-001' model (Generative Language API).
    Each text is embedded individually since batching is not supported.
    """
    import os, requests, time
    API_KEY = os.getenv("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}

    embeddings = []
    for text in texts:
        body = {
            "model": "models/embedding-001",
            "content": {
                "parts": [{"text": text}]
            }
        }
        resp = requests.post(url, headers=headers, json=body)
        if not resp.ok:
            print("❌ API Error for text:", text[:60])
            print(resp.text)
            resp.raise_for_status()
        data = resp.json()
        # Response: { "embedding": { "values": [...] } }
        emb = data.get("embedding", {}).get("values")
        if emb is None:
            raise RuntimeError(f"Unexpected response format: {data}")
        embeddings.append(emb)
        time.sleep(0.1)  # small delay to avoid rate limits
    return embeddings


# =============================================
# Helper for creating combined text
# =============================================
def make_text(row):
    return f"Q: {row['question']} A: {row['final_answer']} Steps: {row['steps']}"

# =============================================
# Main ingestion flow
# =============================================
def main():
    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    df['id'] = df['id'].astype(int)
    texts = [make_text(row) for _, row in df.iterrows()]

    print("📘 Loaded", len(df), "records from", CSV_PATH)
    print("🧠 Generating embeddings with Gemini...")

    all_embs = []
    BATCH = 10
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i+BATCH]
        embs = embed_batch(batch)
        all_embs.extend(embs)
        print(f"✅ Embedded {i + len(batch)}/{len(texts)}")
        time.sleep(0.5)

    # =============================================
    # Connect to Qdrant and create collection
    # =============================================
    q = QdrantClient(url=QDRANT_URL)
    dim = len(all_embs[0])
    print(f"📦 Creating Qdrant collection '{COLLECTION}' with dim={dim}...")
    q.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
    )

    # =============================================
    # Upload points (upsert)
    # =============================================
    points = []
    for idx, (_, row) in enumerate(df.iterrows()):
        payload = {
            "question": row["question"],
            "final_answer": row["final_answer"],
            "steps": row["steps"],
            "tags": row.get("tags", "")
        }
        points.append({
            "id": int(row["id"]),
            "vector": all_embs[idx],
            "payload": payload
        })

    BATCH_UPSERT = 64
    for i in range(0, len(points), BATCH_UPSERT):
        batch = points[i:i + BATCH_UPSERT]
        q.upsert(collection_name=COLLECTION, points=batch)
        print(f"⬆️ Upserted {i + len(batch)}/{len(points)} points")

    print("✅ Done ingesting KB into Qdrant.")

if __name__ == "__main__":
    main()
