import type { Claim, Step } from "./api";
import { Decision } from "./Decision";
import { label, money } from "./format";
import { usePoll } from "./hooks";
import { History, Policy } from "./Policy";
import { StatusBadge } from "./StatusBadge";
import { Steps } from "./Steps";

function Details({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <>
      <div className="panel">
        <h2>The claim</h2>
        <dl className="facts">
          <dt>Type</dt>
          <dd>{label(claim.claim_type)}</dd>
          <dt>Incident</dt>
          <dd>
            <span className="mono">{claim.incident_date}</span>,{" "}
            {claim.incident_location}
          </dd>
          <dt>Submitted</dt>
          <dd className="mono">{claim.submitted_on}</dd>
          <dt>Claimed</dt>
          <dd className="mono">{money(claim.amount_claimed)}</dd>
        </dl>
        <h3>The customer's story</h3>
        <p className="story">{claim.story}</p>
      </div>
      <div className="panel">
        <h2>Items</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Category</th>
              <th scope="col" className="amount">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td>{label(item.category)}</td>
                <td className="amount">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h2>Documents</h2>
        {claim.documents.map((document) => (
          <article key={document.name} className="document">
            <h3>
              {document.name}{" "}
              <span className="muted">{label(document.type)}</span>
            </h3>
            <p>{document.content}</p>
          </article>
        ))}
      </div>
    </>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const {
    data: claim,
    error,
    reload,
  } = usePoll<Claim>(`/api/claims/${claimId}`, 1000);
  const { data: steps } = usePoll<Step[]>(`/api/claims/${claimId}/steps`, 1000);

  if (!claim) {
    return error ? <p role="alert">{error}</p> : <p>Loading {claimId}</p>;
  }

  return (
    <section>
      <a href="#/">Back to the queue</a>
      <div className="claim-head">
        <h1 className="mono">{claim.claim_id}</h1>
        <StatusBadge status={claim.status} />
      </div>
      <p className="lead">{claim.summary}</p>
      <div className="columns">
        <div className="column">
          <Decision claim={claim} onSignedOff={reload} />
          <Details claim={claim} />
        </div>
        <div className="column">
          <Steps steps={steps ?? []} working={claim.status === "in_progress"} />
          <Policy policyId={claim.policy_id} />
          <History customerId={claim.customer_id} />
        </div>
      </div>
    </section>
  );
}
