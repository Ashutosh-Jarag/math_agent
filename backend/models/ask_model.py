# backend/models/ask_model.py
from pydantic import BaseModel

class AskIn(BaseModel):
    question: str
    explain_level: str = "detailed"
    user_id: str | None = None

class AskOut(BaseModel):
    steps: list[str]
    final_answer: str
    sources: list[str]
    confidence: float
