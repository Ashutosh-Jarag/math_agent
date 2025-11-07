# scripts/search_kb_local.py
import os
from dotenv import load_dotenv
import requests
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("COLLECTION_NAME", "math_kb")

def embed_text(text):
    """
    Generate an embedding for a query using Gemini's embedding-001 model.
    Must match the format used during ingestion (embedContent).
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {
        "model": "models/embedding-001",
        "content": {"parts": [{"text": text}]}
    }

    resp = requests.post(url, headers=headers, json=body)
    if not resp.ok:
        print("❌ Embedding error:")
        print(resp.text)
        resp.raise_for_status()

    data = resp.json()
    vec = data.get("embedding", {}).get("values")
    if vec is None:
        raise RuntimeError(f"Unexpected response format: {data}")
    return vec

def kb_search(query, top_k=3):
    """
    Search similar questions in the local Qdrant knowledge base.
    """
    vec = embed_text(query)
    q = QdrantClient(url=QDRANT_URL)
    hits = q.search(collection_name=COLLECTION, query_vector=vec, limit=top_k)
    return hits

if __name__ == "__main__":
    qtext = input("Enter a math question: ").strip()
    hits = kb_search(qtext, top_k=3)
    for i, h in enumerate(hits):
        print(f"\nHit {i+1} (score: {h.score:.4f})")
        print("Question:", h.payload.get("question"))
        print("Answer:", h.payload.get("final_answer"))
        print("Steps:", h.payload.get("steps"))
