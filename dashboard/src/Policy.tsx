import type { Customer, Policy as PolicyRecord } from "./api";
import { label, money } from "./format";
import { usePoll } from "./hooks";

export function Policy({ policyId }: Readonly<{ policyId: string }>) {
  const { data: policy } = usePoll<PolicyRecord>(
    `/api/policies/${policyId}`,
    null,
  );
  if (!policy) return <p className="panel muted">Loading the policy</p>;

  const addOns = policy.add_on_details.map((addOn) => addOn.name).join(", ");
  return (
    <div className="panel">
      <h2>Policy</h2>
      <dl className="facts">
        <dt>Policy</dt>
        <dd className="mono">{policy.policy_id}</dd>
        <dt>Plan</dt>
        <dd>{policy.plan_details.name}</dd>
        <dt>Add-ons</dt>
        <dd>{addOns || "None"}</dd>
        <dt>Bought</dt>
        <dd className="mono">{policy.purchased_on}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination},{" "}
          <span className="mono">{policy.trip.departs_on}</span> to{" "}
          <span className="mono">{policy.trip.returns_on}</span>
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
      </dl>
    </div>
  );
}

export function History({ customerId }: Readonly<{ customerId: string }>) {
  const { data: customer } = usePoll<Customer>(
    `/api/customers/${customerId}`,
    null,
  );
  if (!customer) return <p className="panel muted">Loading the customer</p>;

  return (
    <div className="panel">
      <h2>{customer.name}'s earlier claims</h2>
      {customer.previous_claims.length === 0 ? (
        <p className="muted">No earlier claims.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th scope="col">Claim</th>
              <th scope="col">Filed</th>
              <th scope="col">Type</th>
              <th scope="col">Summary</th>
              <th scope="col">Outcome</th>
              <th scope="col" className="amount">
                Paid
              </th>
            </tr>
          </thead>
          <tbody>
            {customer.previous_claims.map((claim) => (
              <tr key={claim.claim_id}>
                <td className="mono">{claim.claim_id}</td>
                <td className="mono">{claim.filed_on}</td>
                <td>{label(claim.claim_type)}</td>
                <td>{claim.summary}</td>
                <td>{label(claim.outcome)}</td>
                <td className="amount">{money(claim.amount_paid)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
