import React, { useState } from "react";
import AskForm from "./components/AskForm";
import AnswerCard from "./components/AnswerCard";
import FeedbackForm from "./components/FeedbackForm";
import { askQuestion } from "./api";

export default function App() {
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastQuestion, setLastQuestion] = useState("");

  async function handleAsk(payload) {
    setLoading(true);
    setAnswer(null);
    setLastQuestion(payload.question);
    try {
      const res = await askQuestion(payload);
      setAnswer(res);
    } catch (e) {
      alert("Error: " + (e?.message || e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <header>
        <h1>Math Agent</h1>
        <p className="subtitle">Ask math questions — get step-by-step answers.</p>
      </header>

      <main>
        <AskForm onAsk={handleAsk} loading={loading} />

        {loading && <div className="spinner">Loading…</div>}

        {answer && (
          <>
            <AnswerCard data={answer} />
            <FeedbackForm question={lastQuestion} />
          </>
        )}
      </main>

      <footer>
        <small>Built for solving math problems</small>
      </footer>
    </div>
  );
}
