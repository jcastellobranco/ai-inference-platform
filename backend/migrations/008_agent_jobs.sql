-- Add agent jobs without changing existing inference/RAG behavior.
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check
  CHECK (job_type IN ('inference', 'rag', 'agent'));
