import React, { useState } from "react";

export default function AskForm({ onAsk, loading }) {
  const [question, setQuestion] = useState("");
  const [explain, setExplain] = useState("detailed");
  const [userId, setUserId] = useState("user123");

  function submit(e) {
    e?.preventDefault();
    if (!question.trim()) return alert("Please type a question.");
    onAsk({ question: question.trim(), explain_level: explain, user_id: userId });
  }

  return (
    <form className="ask-form" onSubmit={submit}>
      <label>Question</label>
      <textarea
        rows={3}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="e.g., Differentiate f(x)=x^3 + 2x^2 - 5x"
      />

      <div className="row">
        <label>Explain level</label>
        <select value={explain} onChange={(e) => setExplain(e.target.value)}>
          <option value="simple">Simple</option>
          <option value="detailed">Detailed</option>
        </select>

        <label>User ID</label>
        <input value={userId} onChange={(e) => setUserId(e.target.value)} />
      </div>

      <div className="actions">
        <button type="submit" disabled={loading}>
          Ask
        </button>
      </div>
    </form>
  );
}
