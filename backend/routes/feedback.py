# backend/routes/feedback.py
from fastapi import APIRouter
from models.feedback_model import FeedbackIn
import csv, os, subprocess, pandas as pd
from datetime import datetime

router = APIRouter()

FEEDBACK_LOG = "data/feedback_log.csv"
RETRAIN_TRIGGER_COUNT = 10

@router.post("/")
def feedback(req: FeedbackIn):
    os.makedirs(os.path.dirname(FEEDBACK_LOG), exist_ok=True)
    with open(FEEDBACK_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([req.user_id, req.question, req.feedback, req.rating, datetime.now().isoformat()])

    if os.path.exists(FEEDBACK_LOG):
        df = pd.read_csv(FEEDBACK_LOG, names=["user_id","question","feedback","rating","timestamp"])
        if len(df[df["rating"] >= 4]) % RETRAIN_TRIGGER_COUNT == 0:
            subprocess.Popen(["python3", "scripts/retrain_kb.py"], stdout=open("retrain.log", "a"), stderr=subprocess.STDOUT)
            return {"message": "✅ Feedback recorded. Retraining started automatically."}
    return {"message": "✅ Feedback recorded."}
