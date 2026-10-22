import { useState, type SyntheticEvent } from "react";
import { postJson, type Claim, type Handler } from "./api";
import { decisionLabels, money, payment } from "./format";
import { usePoll } from "./hooks";

function SignOff({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  const { data: handlers } = usePoll<Handler[]>("/api/handlers", null);
  const [handlerId, setHandlerId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    setBusy(true);
    void postJson<Claim>(`/api/claims/${claim.claim_id}/sign-off`, {
      handler_id: handlerId,
    })
      .then(
        () => {
          setError(null);
          onSignedOff();
        },
        (reason: unknown) => {
          setError(reason instanceof Error ? reason.message : String(reason));
        },
      )
      .finally(() => {
        setBusy(false);
      });
  };

  return (
    <form className="sign-off" onSubmit={submit}>
      <h3>Sign-off</h3>
      <p>
        The payout of {money(claim.payout ?? 0)} is over the approval limit, so
        a handler signs off before it's paid.
      </p>
      <label>
        Handler
        <select
          value={handlerId}
          onChange={(event) => {
            setHandlerId(event.target.value);
          }}
        >
          <option value="">Choose a handler</option>
          {(handlers ?? [])
            .filter((handler) => handler.can_approve_over_limit)
            .map((handler) => (
              <option key={handler.handler_id} value={handler.handler_id}>
                {handler.name}
              </option>
            ))}
        </select>
      </label>
      <button type="submit" disabled={!handlerId || busy}>
        Sign off and pay
      </button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}

export function Decision({
  claim,
  onSignedOff,
}: Readonly<{ claim: Claim; onSignedOff: () => void }>) {
  if (!claim.decision) {
    return (
      <div className="panel">
        <h2>The agent's decision</h2>
        <p className="muted">
          {claim.status === "in_progress"
            ? "The agent is working on this claim."
            : "The agent hasn't started this claim."}
        </p>
      </div>
    );
  }

  return (
    <div className="panel decision">
      <h2>The agent's decision</h2>
      <dl className="facts">
        <dt>Decision</dt>
        <dd className="decision-value">{decisionLabels[claim.decision]}</dd>
        <dt>Payout</dt>
        <dd className="mono">{money(claim.payout ?? 0)}</dd>
        <dt>Policy section</dt>
        <dd>{claim.policy_section}</dd>
        <dt>Payment</dt>
        <dd>{payment(claim)}</dd>
      </dl>
      <p className="reason">{claim.reason}</p>
      {claim.status === "waiting_for_sign_off" && (
        <SignOff claim={claim} onSignedOff={onSignedOff} />
      )}
    </div>
  );
}
