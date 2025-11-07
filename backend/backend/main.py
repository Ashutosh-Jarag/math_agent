# backend/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from backend.utils import kb_search, generate_with_gemini, web_search_fallback
import re

# ===============================================
# Load environment variables
# ===============================================
load_dotenv()
KB_THRESHOLD = float(os.getenv("KB_THRESHOLD", 0.78))
KB_TOPK = int(os.getenv("KB_TOPK", 3))

app = FastAPI(title="Math Routing Agent - Minimal")

# ===============================================
# Input/Output Schemas
# ===============================================
class AskIn(BaseModel):
    question: str
    explain_level: str = "detailed"  # "simple" | "detailed"
    user_id: str | None = None

class AskOut(BaseModel):
    steps: list[str]
    final_answer: str
    sources: list[str]
    confidence: float

# ===============================================
# Guardrail Functions
# ===============================================
def input_guardrail(question: str) -> bool:
    """
    Accepts a question string and returns True if it's math-related.
    Otherwise False.
    """
    allowed_keywords = [
        "integrate", "differentiate", "derivative", "equation", "matrix",
        "limit", "solve", "find", "function", "value", "graph", "area", "volume"
    ]
    return any(word in question.lower() for word in allowed_keywords)

def output_guardrail(text: str) -> bool:
    """
    Returns True if the AI output is safe and math-related.
    Filters out irrelevant or sensitive responses.
    """
    banned_keywords = ["violence", "religion", "politics", "hack", "illegal", "suicide"]
    return not any(bad in text.lower() for bad in banned_keywords)

# def parse_generation_result(gen_result):
#     """
#     Parse Gemini output and standardize into (steps, final_answer, confidence).
#     """
#     if isinstance(gen_result, dict):
#         steps = gen_result.get("steps") or []
#         final = gen_result.get("final_answer") or ""
#         conf = float(gen_result.get("confidence", 0.5))
#         steps = [str(s) for s in steps] if steps else []
#         return steps, final, conf

#     text = str(gen_result)
#     lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
#     steps = []
#     final = ""
#     for ln in lines:
#         lowered = ln.lower()
#         if "final answer" in lowered or ln.startswith("Answer:") or ln.startswith("Final:"):
#             final = ln.split(":", 1)[1].strip() if ":" in ln else ln
#         else:
#             steps.append(ln)
#     if not final and steps:
#         candidate = steps[-1]
#         if len(candidate.split()) <= 6:
#             final = candidate
#             steps = steps[:-1]
#     return steps, final, 0.55

def parse_generation_result(gen_text):
    """
    gen_text: string returned by generate_with_gemini (already post-processed concisely)
    Returns (steps_list, final_answer, confidence)
    """
    if isinstance(gen_text, dict):
        # If earlier versions return dict, handle it
        txt = "\n".join(gen_text.get("steps", [])) if gen_text.get("steps") else str(gen_text)
    else:
        txt = str(gen_text)

    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    steps = []
    final_answer = ""
    for ln in lines:
        # numbered step
        m = re.match(r'^(\d+)\s*[\.\)]\s*(.*)$', ln)
        if m:
            steps.append(m.group(2).strip())
            continue
        # final answer
        m2 = re.match(r'^(final answer|answer)\s*[:\-]\s*(.*)$', ln, flags=re.I)
        if m2:
            final_answer = m2.group(2).strip()
            continue
        # if line looks like math expression, append as step if no numbered format
        if re.search(r'[=\^\*/]|\\[a-z]+|\bC\b', ln):
            steps.append(ln)
    # If no explicit final found, try last line guess
    if not final_answer and steps:
        if re.match(r'^[A-Za-z0-9\-\+\/*\^\(\)\s\._]+$', steps[-1]) and len(steps[-1].split()) <= 8:
            final_answer = steps[-1]
            steps = steps[:-1]
    # Confidence heuristic: if from KB we likely set it externally; else default 0.6
    return steps, final_answer or "", 0.6


# ===============================================
# Main Endpoint
# ===============================================
@app.post("/ask", response_model=AskOut)
def ask(req: AskIn):
    q = req.question.strip()

    # 🧱 1️⃣ INPUT GUARDRAIL
    if not q:
        raise HTTPException(status_code=400, detail="Empty question provided.")
    if not input_guardrail(q):
        raise HTTPException(
            status_code=400,
            detail="This AI agent only supports mathematical questions."
        )

    # 2️⃣ KB Lookup
    hits = kb_search(q, top_k=KB_TOPK)
    if hits:
        top = hits[0]
        score = float(getattr(top, "score", 0.0) or 0.0)

        if score >= KB_THRESHOLD:
            payload = top.payload
            kb_steps = payload.get("steps") or ""
            kb_answer = payload.get("final_answer") or ""

            context = (
                f"Retrieved example:\n"
                f"Question: {payload.get('question')}\n"
                f"Steps: {kb_steps}\n"
                f"Answer: {kb_answer}\n"
            )

            prompt = f"""
            You are a patient math professor.
            The student's question is: {q}
            Use the retrieved example below to produce a clear, step-by-step solution.
            Keep it {req.explain_level}.
            Use numbered steps and give the final answer clearly.
            {context}
            """

            gen = generate_with_gemini(prompt)
            steps, final_answer, conf = parse_generation_result(gen)

            if not output_guardrail(str(steps) + final_answer):
                raise HTTPException(
                    status_code=400,
                    detail="Unsafe or off-topic content detected in model output."
                )

            if not steps:
                steps = [kb_steps] if kb_steps else []
            if not final_answer:
                final_answer = kb_answer or ""

            reported_conf = round(max(conf, score), 3)

            return AskOut(
                steps=steps,
                final_answer=final_answer,
                sources=[str(top.id)],
                confidence=reported_conf
            )

    # 3️⃣ KB miss → Web Search Fallback + Generation
    context = web_search_fallback(q)
    if context:
        prompt = f"""
        You are a helpful math professor.
        Student asked: {q}
        Here are some search snippets that might help:
        {context}

        Use this context to provide a clear, step-by-step solution.
        Number each step and clearly show the 'Final Answer:' at the end.
        """
    else:
        prompt = f"""
        You are a math professor.
        Student asked: {q}
        No relevant context found.
        Please attempt to solve it step-by-step using standard math rules.
        """

    gen_text = generate_with_gemini(prompt, max_tokens=512, temperature=0.0)
    steps, final_answer, conf = parse_generation_result(gen_text)

    if not output_guardrail(str(steps) + final_answer):
        raise HTTPException(
            status_code=400,
            detail="Unsafe or irrelevant content detected in model output."
        )

    return AskOut(
        steps=steps or [str(gen)],
        final_answer=final_answer or "",
        sources=[],
        confidence=round(float(conf), 3)
    )

# ===============================================
# Root Endpoint
# ===============================================
@app.get("/")
def root():
    return {"message": "Math Agent API is running", "status": "ok"}
