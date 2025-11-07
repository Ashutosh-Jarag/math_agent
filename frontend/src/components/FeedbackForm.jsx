import React, { useState } from "react";
import { sendFeedback } from "../api";

export default function FeedbackForm({ question }) {
  const [rating, setRating] = useState(5);
  const [feedback, setFeedback] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      await sendFeedback({
        user_id: "demo",
        question,
        rating,
        feedback,
      });
      setSubmitted(true);
    } catch (err) {
      alert("Error sending feedback: " + err.message);
    }
  }

  if (submitted) return <p>✅ Feedback submitted. Thanks!</p>;

  return (
    <form onSubmit={handleSubmit} className="feedback-form">
      <h3>Rate this answer</h3>
      <label>
        Rating:
        <input
          type="number"
          min="1"
          max="5"
          value={rating}
          onChange={(e) => setRating(e.target.value)}
        />
      </label>
      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Optional feedback..."
      />
      <button type="submit">Send Feedback</button>
    </form>
  );
}
