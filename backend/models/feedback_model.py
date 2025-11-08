# backend/models/feedback_model.py
from pydantic import BaseModel

class FeedbackIn(BaseModel):
    user_id: str
    question: str
    feedback: str | None = None
    rating: int  # expected 1–5
