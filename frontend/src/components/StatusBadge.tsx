import type { JobStatus } from '../types/jobs';
export function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`status-pill status-pill--${status}`}>
    <span className="status-dot" />{status}
  </span>;
}
