import type { Claim, Decision, Status } from "./api";

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export function money(amount: number): string {
  return dollars.format(amount);
}

export const STATUSES: Status[] = [
  "waiting",
  "in_progress",
  "waiting_for_sign_off",
  "decided",
];

export const statusLabels: Record<Status, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  waiting_for_sign_off: "Waiting for sign-off",
  decided: "Decided",
};

export const decisionLabels: Record<Decision, string> = {
  approve: "Approve",
  decline: "Decline",
  refer: "Refer",
};

export function label(code: string): string {
  const words = code.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function time(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US");
}

export function payment(claim: Claim): string {
  if (claim.decision !== "approve") return "No payment";
  if (claim.paid_amount !== null) {
    const paid = `Paid ${money(claim.paid_amount)}`;
    return claim.signed_off_by
      ? `${paid}, signed off by ${claim.signed_off_by.name}`
      : paid;
  }
  if (claim.status === "waiting_for_sign_off") return "Waiting for sign-off";
  return "Not paid";
}

export function preview(text: string, length = 120): string {
  return text.length > length ? `${text.slice(0, length)}...` : text;
}
