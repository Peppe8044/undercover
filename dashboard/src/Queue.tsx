import type { ClaimRow } from "./api";
import { decisionLabels, label, money, STATUSES } from "./format";
import { usePoll } from "./hooks";
import { StatusBadge } from "./StatusBadge";

export function Queue() {
  const { data: claims, error } = usePoll<ClaimRow[]>("/api/claims", 2000);

  if (!claims) {
    return error ? (
      <p role="alert">The backend can't be reached: {error}</p>
    ) : (
      <p>Loading the queue</p>
    );
  }

  return (
    <section>
      <h1>Claims queue</h1>
      <ul className="counts">
        {STATUSES.map((status) => (
          <li key={status} className="panel count">
            <StatusBadge status={status} />
            <span className="count-number" data-testid={`count-${status}`}>
              {claims.filter((claim) => claim.status === status).length}
            </span>
          </li>
        ))}
      </ul>
      <div className="panel table-panel">
        <table>
          <thead>
            <tr>
              <th scope="col">Claim</th>
              <th scope="col">Customer</th>
              <th scope="col">Type</th>
              <th scope="col">Summary</th>
              <th scope="col" className="amount">
                Claimed
              </th>
              <th scope="col">Submitted</th>
              <th scope="col">State</th>
              <th scope="col">Decision</th>
              <th scope="col" className="amount">
                Payout
              </th>
            </tr>
          </thead>
          <tbody>
            {claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td>
                  <a className="mono" href={`#/claims/${claim.claim_id}`}>
                    {claim.claim_id}
                  </a>
                </td>
                <td>{claim.customer_name}</td>
                <td>{label(claim.claim_type)}</td>
                <td>{claim.summary}</td>
                <td className="amount">{money(claim.amount_claimed)}</td>
                <td className="mono">{claim.submitted_on}</td>
                <td>
                  <StatusBadge status={claim.status} />
                </td>
                <td>{claim.decision ? decisionLabels[claim.decision] : ""}</td>
                <td className="amount">
                  {claim.payout === null ? "" : money(claim.payout)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
