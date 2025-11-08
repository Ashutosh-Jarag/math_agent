
import os
from dotenv import load_dotenv
import dspy
from dspy.evaluate import Evaluate

load_dotenv()

# ==========================
# Configure LLM (Gemini)
# ==========================
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY in .env")

llm = dspy.Google(model="gemini-2.0-flash", api_key=GEMINI_KEY)
dspy.settings.configure(lm=llm)

# ==========================
# Define a DSPy program
# ==========================
class MathSolver(dspy.Module):
    def __init__(self):
        super().__init__()
        self.solve = dspy.ChainOfThought("question -> steps, final_answer")

    def forward(self, question):
        result = self.solve(question=question)
        return result

# ==========================
# Sample training data (from KB or JEE)
# ==========================
train_data = [
    dspy.Example(
        question="Differentiate f(x)=x^3+2x^2-5x",
        steps="Apply power rule: d(xⁿ)/dx = n·xⁿ⁻¹",
        final_answer="f'(x)=3x²+4x−5"
    ),
    dspy.Example(
        question="Integrate 2x dx",
        steps="Use power rule of integration.",
        final_answer="x² + C"
    ),
]

# ==========================
# Train using DSPy optimizer
# ==========================
program = MathSolver()

print("🧠 Optimizing prompt using DSPy...")
optimizer = dspy.MIPROv2()  # Multi-instance prompt optimizer
optimized_program = optimizer.compile(program, trainset=train_data)

# ==========================
# Test on a new example
# ==========================
test_question = "Differentiate x² + 2x + 1"
result = optimized_program(question=test_question)
print("\n📘 Test Output:")
print("Steps:", result.steps)
print("Final Answer:", result.final_answer)

# ==========================
# Save optimized program
# ==========================
optimized_program.save("backend/models/dspy_optimized_math.json")
print("\n✅ DSPy optimization complete! Saved tuned prompt.")
