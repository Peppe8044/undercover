import type { Status } from "./api";
import { statusLabels } from "./format";

export function StatusBadge({ status }: Readonly<{ status: Status }>) {
  return (
    <span className={`badge badge-${status}`}>{statusLabels[status]}</span>
  );
}
