# ===============================================
# 🧠 DSPy Optimization on Real JEE Bench Dataset (Gemini Integration - Model Fix)
# ===============================================
import os
import json
from dotenv import load_dotenv
import dspy
from dspy.evaluate import Evaluate
import google.generativeai as genai
import copy

# ===============================================
# Load Environment
# ===============================================
load_dotenv()
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_KEY:
    raise RuntimeError("❌ Missing GOOGLE_API_KEY in .env file.")

# ===============================================
# ✅ Configure Gemini SDK
# ===============================================
print("⚙️ Configuring DSPy with Gemini (direct via SDK)...")

# Use a stable model name supported by all SDKs
MODEL_NAME = "gemini-1.5-pro"

try:
    genai.configure(api_key=GEMINI_KEY)
    test_model = genai.GenerativeModel(MODEL_NAME)
    _ = test_model.generate_content("ping")
except Exception as e:
    raise RuntimeError(f"❌ Gemini API Key invalid or model unavailable: {e}")

# ===============================================
# Gemini → DSPy Adapter (No Deepcopy Problem)
# ===============================================
from dspy.clients import BaseLM

class GeminiLM(BaseLM):
    """Custom LM adapter that connects DSPy to Google Gemini directly."""
    def __init__(self, model=MODEL_NAME):
        super().__init__(model=model)
        self.client = genai.GenerativeModel(model)

    def forward(self, prompt=None, messages=None, **kwargs):
        if messages:
            user_text = "\n".join([m["content"] for m in messages if m["role"] == "user"])
        else:
            user_text = prompt or ""

        try:
            response = self.client.generate_content(user_text)
            return response.text.strip() if response and hasattr(response, "text") else ""
        except Exception as e:
            return f"[Gemini Error: {e}]"

    # 🚫 Prevent deepcopy crash
    def __deepcopy__(self, memo):
        return self

    # 🚫 Prevent BaseLM.copy() crash
    def copy(self):
        return self

# Register globally
lm = GeminiLM(model=MODEL_NAME)
dspy.settings.configure(lm=lm)

# ===============================================
# Define Math Solver Module
# ===============================================
class MathSolver(dspy.Module):
    """A reasoning module for solving math problems."""
    def __init__(self):
        super().__init__()
        self.solve = dspy.ChainOfThought("question -> steps, final_answer")

    def forward(self, question):
        return self.solve(question=question)

# ===============================================
# Load Dataset
# ===============================================
DATA_PATH = "data/jee_bench_sample.json"
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"❌ Dataset not found at {DATA_PATH}")

with open(DATA_PATH, "r") as f:
    dataset = json.load(f)

if isinstance(dataset, dict):
    dataset = dataset.get("data", list(dataset.values()))

if not isinstance(dataset, list):
    raise ValueError("⚠️ Dataset format invalid — must be a list of objects.")

# ===============================================
# Prepare Examples
# ===============================================
examples = []
for item in dataset:
    q = item.get("question", "")
    a = str(item.get("answer", "")).strip() or str(item.get("gold", "")).strip()
    if q and a:
        examples.append(dspy.Example(question=q, final_answer=a).with_inputs("question"))

if not examples:
    raise ValueError("⚠️ No valid examples found in JEE dataset.")

print(f"📘 Loaded {len(examples)} JEE examples for DSPy tuning")

# ===============================================
# Split Data
# ===============================================
split = int(0.8 * len(examples))
trainset, evalset = examples[:split], examples[split:]
print(f"📊 Using {len(trainset)} for training and {len(evalset)} for validation.")

# ===============================================
# Define Metric
# ===============================================
def answer_match(example, prediction) -> float:
    gold = str(example.get("final_answer", "")).strip().lower()
    pred = str(getattr(prediction, "final_answer", "")).strip().lower()
    if not gold or not pred:
        return 0.0
    if gold == pred:
        return 1.0
    import re
    num = lambda s: re.findall(r"[-+]?\d*\.\d+|\d+", s)
    try:
        if num(gold) and num(pred) and abs(float(num(gold)[-1]) - float(num(pred)[-1])) < 1e-3:
            return 1.0
    except:
        pass
    return 1.0 if len(gold) == 1 and gold in "abcd" and gold == pred else 0.0

# ===============================================
# Run DSPy Optimization
# ===============================================
program = MathSolver()
optimizer = dspy.MIPROv2(metric=answer_match)
print("🧠 Starting DSPy optimization using MIPROv2...")
optimized_program = optimizer.compile(program, trainset=trainset)

# ===============================================
# Evaluate
# ===============================================
evaluator = Evaluate(metric=answer_match, display_progress=True)
evaluation_result = evaluator(optimized_program, evalset)

print("\n📊 DSPy Evaluation Summary:")
print(f" - Total evaluated: {len(evalset)}")
print(f" - Accuracy: {evaluation_result['score'] * 100:.2f}%")

# ===============================================
# Save
# ===============================================
os.makedirs("backend/models", exist_ok=True)
optimized_program.save("backend/models/dspy_optimized_math.json")
print("✅ DSPy optimized prompt saved to backend/models/dspy_optimized_math.json")

# ===============================================
# Test
# ===============================================
print("\n🧪 Testing optimized DSPy solver...")
test_q = "Differentiate x^3 + 2x^2 - 5x"
result = optimized_program(question=test_q)
print("Q:", test_q)
print("Steps:", getattr(result, "steps", "N/A"))
print("Final Answer:", getattr(result, "final_answer", "N/A"))

print("🎯 DSPy optimization completed successfully.")
