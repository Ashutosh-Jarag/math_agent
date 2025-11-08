
# Main File for Math Agent API


# ===============================================
# Importing necessary modules and dependencies
# ===============================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.ask import router as ask_router
from routes.feedback import router as feedback_router
from jee_evaluator import evaluate_agent


# ===============================================
# Fastapi Instance
# ==============================================

app = FastAPI(title="Math Agent API")


# ===============================================
# Middleware Configuration
# ==============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================================
# Routes Registration  /Ask 
# =============================================
app.include_router(ask_router, prefix="/ask", tags=["Ask"])

# ===============================================
# Routes Registration  /Feedback 
# =============================================
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])


# ===============================================
# Evaluation Endpoint 
# ===============================================
@app.get("/evaluate")
def evaluate(limit: int = 10):
    """
    Runs automatic evaluation using JEE Bench dataset.
    """
    report = evaluate_agent(limit=limit)
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation dataset not found.")
    return {"message": "Evaluation completed", "report": report}


# ===============================================
# Root Endpoint
# =============================================
@app.get("/")
def root():
    return {"message": "Math Agent API running", "status": "ok"}
