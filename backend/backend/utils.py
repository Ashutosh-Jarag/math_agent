# backend/utils.py
import os
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# ===============================================
# Load environment variables
# ===============================================
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("COLLECTION_NAME", "math_kb")
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "embedding-001")  
GEN_MODEL = os.getenv("GEMINI_GEN_MODEL", "gemini-1.5-flash")  

qdrant_client = QdrantClient(url=QDRANT_URL)



# ===============================================
# Web search fallback function
# ===============================================
def web_search_fallback(query: str) -> str:
    """
    Fetch additional context using Serper.dev (Google Search API).
    Returns combined text snippets to help Gemini.
    """
    import os, requests
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("⚠️ SERPER_API_KEY not found in .env — skipping web search.")
        return ""

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    body = {"q": query, "num": 3}

    resp = requests.post(url, headers=headers, json=body)
    if not resp.ok:
        print("⚠️ Web search API error:", resp.text)
        return ""

    data = resp.json()
    # Extract snippet texts
    results = [r["snippet"] for r in data.get("organic", []) if "snippet" in r]
    context = "\n".join(results)
    return context

# ===============================================
# Embedding Function
# ===============================================
def embed_text(text):
    """
    Generate an embedding using Gemini's embedding-001 model.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text}]}
    }

    resp = requests.post(url, headers=headers, json=body)
    if not resp.ok:
        print("❌ Embedding error:", resp.text)
        resp.raise_for_status()

    data = resp.json()
    embedding = data.get("embedding", {}).get("values")
    if not embedding:
        raise RuntimeError(f"Unexpected embedding response format: {data}")
    return embedding

# ===============================================
# Knowledge Base Search (Qdrant)
# ===============================================
def kb_search(query, top_k=3):
    """
    Search the Qdrant vector database for similar math problems.
    """
    vec = embed_text(query)
    hits = qdrant_client.search(collection_name=COLLECTION, query_vector=vec, limit=top_k)
    return hits

# ===============================================
# Text Generation Function
# ===============================================
def generate_with_gemini(prompt, max_tokens=512, temperature=0.2):
    """
    Calls the Gemini model and extracts clean text output.
    """
    import requests, json, os
    API_KEY = os.getenv("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_GEN_MODEL", "gemini-2.0-flash")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}
    }

    resp = requests.post(url, headers=headers, json=body)
    if not resp.ok:
        print("❌ Gemini API Error:", resp.text)
        resp.raise_for_status()

    data = resp.json()

    # Try extracting clean text safely
    try:
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
    except Exception:
        text = str(data)

    # If still no text, fallback to legacy response structure
    if not text:
        text = data.get("output_text") or str(data)

    return text.strip()

