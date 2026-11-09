-- Document selection is part of the durable job payload, not transient UI state.
-- Fresh deployment and an existing database both accept this additive migration.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS audit_policy_document_id uuid;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS audit_target_document_ids uuid[];
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_audit_documents_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_audit_documents_check CHECK (
    agent_workflow <> 'compliance' OR
    (audit_policy_document_id IS NOT NULL
     AND audit_target_document_ids IS NOT NULL
     AND cardinality(audit_target_document_ids) BETWEEN 1 AND 4
     AND NOT audit_policy_document_id = ANY(audit_target_document_ids))
);
