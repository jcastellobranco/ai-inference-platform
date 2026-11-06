import type { Job } from '../types/jobs';
import { parseRagResult } from '../types/jobs';
interface Props { jobs: Job[]; isLoading: boolean; onRefresh: () => void; disabled: boolean }
function ResultCell({ job }: { job: Job }) {
  const rag = parseRagResult(job.result);
  if (rag) return <div className="result-cell">
    <p>{rag.answer}</p>
    {rag.citations.length > 0 && <small>Sources: {rag.citations.map(c => c.source).join(', ')}</small>}
    {rag.evaluation && <small>Evaluation: {rag.evaluation.passed ? 'Passed' : 'Failed'}</small>}
  </div>;
  return <span>{job.result || job.error || '—'}</span>;
}
export function JobsTable({ jobs, isLoading, onRefresh, disabled }: Props) {
  return <section aria-labelledby="jobs-heading">
    <div className="section-heading">
      <h2 id="jobs-heading">Recent jobs</h2>
      <button type="button" onClick={onRefresh} disabled={disabled || isLoading}>
        {isLoading ? 'Refreshing…' : 'Refresh'}
      </button>
    </div>
    {jobs.length === 0 ? <p>No jobs loaded. Enter your token and select Load jobs.</p> :
      <div className="table-scroll"><table>
        <thead><tr><th scope="col">Job ID</th><th scope="col">Prompt</th>
          <th scope="col">Status</th><th scope="col">Attempts</th><th scope="col">Result</th></tr></thead>
        <tbody>{jobs.map(job => <tr key={job.id}>
          <td><code>{job.id}</code></td><td>{job.prompt}</td>
          <td><span className={`status status--${job.status}`}>{job.status}</span></td>
          <td>{job.attempts ?? 0}</td><td><ResultCell job={job}/></td>
        </tr>)}</tbody>
      </table></div>}
  </section>;
}
