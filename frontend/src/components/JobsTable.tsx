import { Button, Table } from './ui';
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
      <Button variant="unstyled" type="button" onClick={onRefresh} disabled={disabled || isLoading}>
        {isLoading ? 'Refreshing…' : 'Refresh'}
      </Button>
    </div>
    {jobs.length === 0 ? <p>No jobs loaded. Enter your token and select Load jobs.</p> :
      <Table.Scroll><Table.Root>
        <Table.Header><Table.Row><Table.Head scope="col">Job ID</Table.Head><Table.Head scope="col">Prompt</Table.Head>
          <Table.Head scope="col">Status</Table.Head><Table.Head scope="col">Attempts</Table.Head><Table.Head scope="col">Result</Table.Head></Table.Row></Table.Header>
        <Table.Body>{jobs.map(job => <Table.Row key={job.id}>
          <Table.Cell><code>{job.id}</code></Table.Cell><Table.Cell>{job.prompt}</Table.Cell>
          <Table.Cell><span className={`status status--${job.status}`}>{job.status}</span></Table.Cell>
          <Table.Cell>{job.attempts ?? 0}</Table.Cell><Table.Cell><ResultCell job={job}/></Table.Cell>
        </Table.Row>)}</Table.Body>
      </Table.Root></Table.Scroll>}
  </section>;
}
