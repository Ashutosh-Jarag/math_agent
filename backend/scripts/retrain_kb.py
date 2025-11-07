# scripts/retrain_kb.py
import os
import pandas as pd
from dotenv import load_dotenv
import requests
import time
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

# ================================================
# Load environment variables
# ================================================
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("COLLECTION_NAME", "math_kb")
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "embedding-001")

FEEDBACK_PATH = "data/feedback_log.csv"

# ================================================
# Helper: Gemini embedding function
# ================================================
def embed_text(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {"model": f"models/{EMBED_MODEL}", "content": text}
    resp = requests.post(url, headers=headers, json=body)
    if not resp.ok:
        print("❌ Embedding error:", resp.text)
        resp.raise_for_status()
    data = resp.json()
    emb = (
        data.get("embedding")
        or data.get("data", [{}])[0].get("embedding")
        or data.get("outputs", [{}])[0].get("embedding")
    )
    return emb


# ================================================
# Step 1: Load feedback and filter high-rated
# ================================================
def load_feedback(min_rating=4):
    if not os.path.exists(FEEDBACK_PATH):
        print("⚠️ No feedback_log.csv found yet.")
        return pd.DataFrame(columns=["user_id", "question", "feedback", "rating"])

    df = pd.read_csv(FEEDBACK_PATH)
    df = df[df["rating"] >= min_rating].dropna(subset=["question"])
    print(f"📘 Loaded {len(df)} positive feedback entries.")
    return df


# ================================================
# Step 2: Upsert new KB entries
# ================================================
def upsert_feedback_to_qdrant(df):
    if df.empty:
        print("⚠️ No qualifying feedback to process.")
        return

    q = QdrantClient(url=QDRANT_URL)

    # Ensure collection exists
    if not q.collection_exists(COLLECTION):
        print(f"🆕 Creating collection '{COLLECTION}'...")
        # Assume embedding size 768 (Gemini)
        q.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )

    points = []
    print("🧠 Generating embeddings for feedback...")
    for idx, row in enumerate(df.itertuples(), start=1):
        text = f"Q: {row.question}\nFeedback: {row.feedback or 'Correct answer provided by user'}"
        emb = embed_text(text)
        if not emb:
            print(f"⚠️ Skipped feedback {idx} (embedding failed).")
            continue

        payload = {
            "question": row.question,
            "final_answer": row.feedback or "",
            "steps": "",
            "tags": "user_feedback"
        }
        points.append({"id": int(time.time() * 1000) % 1_000_000_000, "vector": emb, "payload": payload})

        print(f"✅ Embedded feedback {idx}/{len(df)}")

    if points:
        q.upsert(collection_name=COLLECTION, points=points)
        print(f"🚀 Upserted {len(points)} feedback entries into KB.")
    else:
        print("⚠️ No points upserted (no valid embeddings).")


def main():
    df = load_feedback()
    upsert_feedback_to_qdrant(df)
    print("✅ Retraining completed successfully.")


if __name__ == "__main__":
    main()
