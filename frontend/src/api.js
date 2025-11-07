const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function askQuestion(payload) {
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to get answer");
  return await res.json();
}

export async function sendFeedback(payload) {
  const res = await fetch(`${API_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to send feedback");
  return await res.json();
}
