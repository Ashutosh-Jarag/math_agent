import React from "react";

export default function AnswerCard({ data }) {
  return (
    <div className="answer-card">
      <h2>Answer</h2>

      <div className="final-answer">
        <strong>Final Answer: </strong>
        {data.final_answer || "—"}
      </div>

      <div className="steps">
        <h3>Steps</h3>
        {Array.isArray(data.steps) && data.steps.length ? (
          <ol>
            {data.steps.map((s, i) => (
              <li key={i} dangerouslySetInnerHTML={{ __html: s }} />
            ))}
          </ol>
        ) : (
          <p>No steps provided.</p>
        )}
      </div>

      <div className="meta">
        <small>Confidence: {data.confidence ?? "—"}</small>
        {data.sources && data.sources.length ? (
          <small> • Sources: {data.sources.join(", ")}</small>
        ) : null}
      </div>
    </div>
  );
}
