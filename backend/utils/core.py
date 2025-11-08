
# Core utility functions for embeddings, Qdrant, and Gemini integration.

# ===============================================
# Imports
# ===============================================

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

    parameters :
        query : The question to ask
    
    returns :
        context : Combined text snippets from Google search results
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

    parameters :
        text : The input text to embed

    returns :
        embedding : A list of floats representing the embedding
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

    parameters :
        query : The user's question/query
        top_k : Number of similar documents to retrieve

    returns :
        hits : List of matching documents sorted by similarity score
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

def generate_with_gemini(prompt, max_tokens=512, temperature=0.0, model=None, mode="student"):
    """
    Call Gemini and return cleaned text.
    mode: "student" -> return numbered steps + Final Answer (default)
          "eval"    -> return ONLY a single final answer line (best for automated evaluation)
          "legacy"  -> return raw Gemini output (for debugging)
    
    Parameters :
        prompt : The user's question/query
        max_tokens : Maximum tokens to generate
        temperature : Temperature parameter for generation
        model : Model name (optional)
        mode : Mode ("student", "eval", or "legacy")

    Returns:
        text: Cleaned text generated by Gemini based on the specified mode.
    """
    API_KEY = os.getenv("GOOGLE_API_KEY")
    GEN_MODEL = model or os.getenv("GEMINI_GEN_MODEL", "gemini-2.5-flash")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEN_MODEL}:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}

    if mode == "student":
        directive = (
            "INSTRUCTIONS: Return numbered steps and a single 'Final Answer:' line. "
            "Do NOT include greetings or extra commentary. Example:\n"
            "1. Step one...\n2. Step two...\nFinal Answer: <expression>\n"
        )
    else:  # evalution mode
        directive = (
            "You are evaluating a math problem. "
            "Return only one line containing the FINAL ANSWER. "
            "Do not explain or show steps. "
            "For numeric answers, give just the number (e.g., 6, 1/2, 3.14). "
            "For MCQs, give the option letter (A, B, C, or D). "
            "If unsure, still attempt to give your best single answer."
)

    full_prompt = directive + "\n\n" + prompt

    body = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }

    resp = requests.post(url, headers=headers, json=body)
    if not resp.ok:
        print("❌ Gemini API Error:", resp.text)
        resp.raise_for_status()

    data = resp.json()
    text = ""
    try:
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        ) or ""
    except Exception:
        text = data.get("output_text") or data.get("text") or str(data)

    text = text.strip()

    if mode == "student":
        text = re.sub(r'^\s*(hi|hello|hey|dear student|i\'d be happy to help)[\.,!\s:-]*', '', text, flags=re.I)
        lines = [ln.rstrip() for ln in text.splitlines()]
        filtered_lines = []
        for ln in lines:
            ln_strip = ln.strip()
            if re.match(r'^\d+\s*\.', ln_strip):
                filtered_lines.append(ln_strip)
            elif re.match(r'^(final answer|answer)\s*[:\-]', ln_strip, flags=re.I):
                filtered_lines.append(ln_strip)
            elif re.search(r'[=\^\*\/]|\\[a-z]+|\bC\b', ln_strip):
                filtered_lines.append(ln_strip)
        if not filtered_lines:
            for ln in lines:
                if len(ln.strip()) <= 120 and re.search(r'\d|\+|\-|\=|\^|/|\*', ln):
                    filtered_lines.append(ln.strip())
            if not filtered_lines:
                filtered_lines = [ln.strip() for ln in lines if ln.strip()][:6]
        result = "\n".join(filtered_lines).strip()
        return result

    else:  

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return ""  

        for ln in lines:
            m = re.match(r'^(final answer|answer)\s*[:\-]\s*(.*)$', ln, flags=re.I)
            if m:
                candidate = m.group(2).strip()
                candidate = candidate.strip('. ')
                return candidate

        for ln in lines:
            m = re.match(r'^[\(\[]?([A-D])[\)\].:\s-]+', ln, flags=re.I)
            if m:
                return m.group(1).upper()

        nums = re.findall(r'[-+]?\d*\.?\d+\/?\d*', text)
        if nums:
            return nums[-1].strip()

        return lines[0][:200]


