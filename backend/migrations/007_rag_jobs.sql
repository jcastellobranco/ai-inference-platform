-- Preserve existing jobs as inference jobs. Run before deploying RAG jobs API/worker.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_type text NOT NULL DEFAULT 'inference';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS reference_answer text;
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_job_type_check CHECK (job_type IN ('inference','rag'));
ALTER TABLE jobs ADD CONSTRAINT jobs_reference_length_check CHECK (
  reference_answer IS NULL OR length(reference_answer) BETWEEN 1 AND 16000
);
