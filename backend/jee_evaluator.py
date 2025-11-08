
# ===============================================
# Importing necessary modules and dependencies
# ===============================================
import json
import time
import requests
import re
from statistics import mean
from pathlib import Path

try:
    from backend.utils import generate_with_gemini
    DIRECT_GENERATOR_AVAILABLE = True
except Exception:
    try:
        from backend.utils.core import generate_with_gemini
        DIRECT_GENERATOR_AVAILABLE = True
    except Exception:
        DIRECT_GENERATOR_AVAILABLE = False

# ===============================================
# Constants & Configuration
# ===============================================
EVAL_DATA_PATH = Path("data/jee_bench_sample.json")
REPORT_PATH = Path("data/eval_report.json")
BACKEND_URL = "http://localhost:8000/ask"

# ===============================================
# Helper: Normalization & Matching
# ===============================================
def normalize_text(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or "").strip()).lower()

def extract_first_option(answer_text: str) -> str:
    """Return A/B/C/D if present at start of a line, else empty."""
    if not answer_text:
        return ""
    m = re.search(r'\b([A-D])\b', answer_text, flags=re.I)
    if m:
        return m.group(1).upper()
    return ""

def extract_numbers(s: str):
    """Return list of numeric tokens found (integers, decimals, fractions)."""
    if not s:
        return []

    nums = re.findall(r'[-+]?\d+\.\d+|[-+]?\d+\/\d+|[-+]?\d+', s)
    return nums

def numeric_equal(a: str, b: str, tol=1e-3) -> bool:
    """Compare numeric expressions robustly. Handles ints, floats, simple fractions."""
    if not a or not b:
        return False
    # try parse fraction
    def parse_num(tok):
        try:
            if "/" in tok:
                n, d = tok.split("/")
                return float(n) / float(d)
            return float(tok)
        except Exception:
            return None

    nums_a = extract_numbers(a)
    nums_b = extract_numbers(b)
    if not nums_a or not nums_b:
        return False

    va = parse_num(nums_a[-1])
    vb = parse_num(nums_b[-1])
    if va is None or vb is None:
        return False
    return abs(va - vb) <= tol

# ===============================================
# Main Functionality Evaluation
# ===============================================
def evaluate_agent(limit=20):
    """
    Evaluates Math Agent using sample JEE Bench problems.
    Calculates accuracy and average response time.

    Parameters :
        limit (int): Number of questions to test. Default is 20.

    Returns :
        dict: A dictionary containing evaluation metrics including total tested questions,
              number of correct answers, accuracy percentage, average response time, and detailed results.
    """
    if not EVAL_DATA_PATH.exists():
        print("⚠️ JEE Bench sample not found. Please place jee_bench_sample.json in data/.")
        return

    with open(EVAL_DATA_PATH) as f:
        dataset = json.load(f)

    total_to_test = min(limit, len(dataset))
    if total_to_test == 0:
        print("⚠️ No examples in dataset.")
        return

    correct = 0
    times = []
    results = []

    for i, item in enumerate(dataset[:total_to_test]):
        q = item.get("question", "")
        correct_answer = str(item.get("answer", "")).strip()

        print(f"\n🧮 [{i+1}/{total_to_test}] Question:")
        print(q)
        start = time.time()

        ai_answer = ""
        # Preferred: call local generator directly in EVAL mode
        if DIRECT_GENERATOR_AVAILABLE:
            try:
                prompt = f"Question: {q}\nEVALUATION MODE: Return ONLY THE FINAL ANSWER in one short line."
                ai_answer = generate_with_gemini(prompt, max_tokens=200, temperature=0.0, mode="eval")
            except Exception as e:
                print("❌ Direct generation error:", e)
                ai_answer = ""
        else:
            try:
                resp = requests.post(BACKEND_URL, json={"question": q, "explain_level": "simple", "eval_mode": True}, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                ai_answer = data.get("final_answer", "") or ""
            except Exception as e:
                print("❌ HTTP fallback error:", e)
                ai_answer = ""

        elapsed = round(time.time() - start, 2)
        times.append(elapsed)
        if not ai_answer.strip():
            print("⚠️ Empty AI answer received — skipping this question.")
            results.append({
                "question": q,
                "correct_answer": correct_answer,
                "ai_answer": ai_answer,
                "match": False,
                "match_reason": "empty-output",
                "time_sec": elapsed
            })
            continue


        norm_ai = normalize_text(ai_answer)
        norm_gold = normalize_text(correct_answer)

        match = False
        reason = ""

        # 1) Exact normalized equality or substring
        if norm_gold and (norm_gold == norm_ai or norm_gold in norm_ai or norm_ai in norm_gold):
            match = True
            reason = "text-eq"

        # 2) Option letter match (A/B/C/D)
        if not match:
            opt_ai = extract_first_option(ai_answer)
            opt_gold = extract_first_option(correct_answer)
            if opt_ai and opt_gold and opt_ai == opt_gold:
                match = True
                reason = "option-eq"

        # 3) Numeric comparison (handles simple fractions/decimals)
        if not match:
            if numeric_equal(ai_answer, correct_answer):
                match = True
                reason = "numeric-eq"

        results.append({
            "question": q,
            "correct_answer": correct_answer,
            "ai_answer": ai_answer,
            "match": bool(match),
            "match_reason": reason,
            "time_sec": elapsed
        })

        if match:
            correct += 1
            print("✅ Correct (reason:", reason + ")")
        else:
            print(f"❌ Incorrect (AI: {ai_answer!r})")

        print(f"⏱️ Time: {elapsed}s")

    accuracy = round(correct / total_to_test * 100, 2)
    avg_time = round(mean(times), 2) if times else 0.0

    report = {
        "total_tested": total_to_test,
        "correct": correct,
        "accuracy_percent": accuracy,
        "avg_response_time": avg_time,
        "results": results
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\n📊 Evaluation Complete → Accuracy: {accuracy}% | Avg Time: {avg_time}s")
    print(f"📁 Report saved to: {REPORT_PATH}")

    return report

if __name__ == "__main__":
    evaluate_agent(limit=10)
