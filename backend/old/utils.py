# backend/utils.py
import os
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
import re

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
# def generate_with_gemini(prompt, max_tokens=512, temperature=0.2):
#     """
#     Calls the Gemini model and extracts clean text output.
#     """
#     import requests, json, os
#     API_KEY = os.getenv("GOOGLE_API_KEY")
#     model = os.getenv("GEMINI_GEN_MODEL", "gemini-2.0-flash")

#     url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
#     headers = {"Content-Type": "application/json"}

#     body = {
#         "contents": [{"role": "user", "parts": [{"text": prompt}]}],
#         "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}
#     }

#     resp = requests.post(url, headers=headers, json=body)
#     if not resp.ok:
#         print("❌ Gemini API Error:", resp.text)
#         resp.raise_for_status()

#     data = resp.json()

#     # Try extracting clean text safely
#     try:
#         text = (
#             data.get("candidates", [{}])[0]
#             .get("content", {})
#             .get("parts", [{}])[0]
#             .get("text", "")
#         )
#     except Exception:
#         text = str(data)

#     # If still no text, fallback to legacy response structure
#     if not text:
#         text = data.get("output_text") or str(data)

#     return text.strip()

def generate_with_gemini(prompt, max_tokens=512, temperature=0.0, model=None):
    """
    Call Gemini and return a concise string containing only:
      - numbered steps (1., 2., ...) and
      - a final line starting with 'Final Answer:' or 'Answer:'.
    Post-process to remove salutations and filler.
    """
    API_KEY = os.getenv("GOOGLE_API_KEY")
    GEN_MODEL = model or os.getenv("GEMINI_GEN_MODEL", "gemini-2.5-flash")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEN_MODEL}:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}

    # We add an extra instruction at the top of the prompt to force concise output
    concise_directive = (
        "INSTRUCTIONS (very important):\n"
        "Return ONLY numbered steps and a single 'Final Answer:' line. "
        "Do NOT include greetings, apologies, explanations about methodology, "
        "or extra commentary. Use short clear sentences. Example:\n"
        "you can start with just - Here is your solution:\n"
        "1. Step one...\n2. Step two...\nFinal Answer: <expression>\n"
    )
    # combine
    full_prompt = concise_directive + "\n\n" + prompt

    body = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }

    resp = requests.post(url, headers=headers, json=body)
    if not resp.ok:
        # preserve readable error
        print("❌ Gemini API Error:", resp.text)
        resp.raise_for_status()

    data = resp.json()

    # SAFE extraction of text from response
    text = ""
    try:
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        ) or ""
    except Exception:
        text = ""

    # Fallbacks (older fields)
    if not text:
        text = data.get("output_text") or data.get("text") or str(data)

    # ===== POST-PROCESSING: remove salutations/filler =====
    # remove common greetings at the start
    text = re.sub(r'^\s*(hi|hello|hey|dear student|i\'d be happy to help)[\.,!\s:-]*', '', text, flags=re.I)

    # remove lines that are clearly filler like "Let's break it down" or "Problem:" at top
    lines = [ln.rstrip() for ln in text.splitlines()]
    filtered_lines = []
    for ln in lines:
        ln_strip = ln.strip()
        # keep numbered steps or Final Answer lines, or math lines (containing = or ^ or / or numbers)
        if re.match(r'^\d+\s*\.', ln_strip):  # numbered step
            filtered_lines.append(ln_strip)
        elif re.match(r'^(final answer|answer)\s*[:\-]', ln_strip, flags=re.I):
            filtered_lines.append(ln_strip)
        elif re.search(r'[=\^\*\/]|\\[a-z]+|\bC\b', ln_strip):  # likely math expression line
            filtered_lines.append(ln_strip)
        # else drop it (saves tokens)
    # If nothing extracted, fall back to trying to salvage useful lines (very short)
    if not filtered_lines:
        # pick lines that look like math or are short
        for ln in lines:
            if len(ln.strip()) <= 120 and re.search(r'\d|\+|\-|\=|\^|/|\*', ln):
                filtered_lines.append(ln.strip())
        # final fallback: use the first 6 non-empty lines
        if not filtered_lines:
            filtered_lines = [ln.strip() for ln in lines if ln.strip()][:6]

    result = "\n".join(filtered_lines).strip()
    return result


