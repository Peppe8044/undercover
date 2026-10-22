import type { Step } from "./api";
import { preview, time } from "./format";

const kindLabels: Record<Step["kind"], string> = {
  model: "Agent",
  tool_call: "Tool call",
  tool_result: "Result",
};

export function Steps({
  steps,
  working,
}: Readonly<{ steps: Step[]; working: boolean }>) {
  return (
    <div className="panel">
      <h2>The agent's steps</h2>
      {steps.length === 0 && <p className="muted">No steps yet.</p>}
      <ol className="steps">
        {steps.map((step) => (
          <li key={step.step_id} className={`step step-${step.kind}`}>
            <div className="step-head">
              <span className="step-kind">{kindLabels[step.kind]}</span>
              <span className="mono muted">{time(step.created_at)}</span>
            </div>
            {step.kind === "tool_result" ? (
              <details>
                <summary>{preview(step.content)}</summary>
                <pre className="step-detail">{step.content}</pre>
              </details>
            ) : (
              <p className="step-text">{step.content}</p>
            )}
          </li>
        ))}
      </ol>
      {working && <p className="muted">The agent is working on this claim.</p>}
    </div>
  );
}
