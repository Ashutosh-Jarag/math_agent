# backend/routes/ask.py
from fastapi import APIRouter, HTTPException
from models.ask_model import AskIn, AskOut
from utils.core import kb_search, generate_with_gemini, web_search_fallback
from utils.guardrails import input_guardrail, output_guardrail
import os, re

router = APIRouter()

KB_THRESHOLD = float(os.getenv("KB_THRESHOLD", 0.78))
KB_TOPK = int(os.getenv("KB_TOPK", 3))

def parse_generation_result(gen_text):
    """Extract steps and final answer from Gemini response."""
    lines = [ln.strip() for ln in str(gen_text).splitlines() if ln.strip()]
    steps, final_answer = [], ""
    for ln in lines:
        if re.match(r'^\d+\.', ln): steps.append(ln)
        elif re.match(r'^(final answer|answer)', ln, re.I): final_answer = ln.split(':',1)[-1].strip()
    return steps, final_answer, 0.6


@router.post("/", response_model=AskOut)
def ask(req: AskIn):
    q = req.question.strip()
    if not q or not input_guardrail(q):
        raise HTTPException(status_code=400, detail="Only math questions are allowed.")

    hits = kb_search(q, top_k=KB_TOPK)
    if hits:
        top = hits[0]
        score = float(getattr(top, "score", 0.0) or 0.0)
        if score >= KB_THRESHOLD:
            payload = top.payload
            context = f"Question: {payload['question']}\nSteps: {payload['steps']}\nAnswer: {payload['final_answer']}"
            prompt = f"Use this context to answer: {q}\n{context}\nGive step-by-step answer and final answer clearly."
            gen_text = generate_with_gemini(prompt)
            steps, final_answer, conf = parse_generation_result(gen_text)
            if not output_guardrail(str(steps)+final_answer):
                raise HTTPException(status_code=400, detail="Unsafe output detected.")
            return AskOut(steps=steps, final_answer=final_answer, sources=[str(top.id)], confidence=round(max(conf,score),3))
    
    context = web_search_fallback(q)
    prompt = f"Student asked: {q}\nContext: {context}\nAnswer step-by-step with 'Final Answer:' line."
    gen_text = generate_with_gemini(prompt)
    steps, final_answer, conf = parse_generation_result(gen_text)
    return AskOut(steps=steps, final_answer=final_answer, sources=[], confidence=round(conf,3))
