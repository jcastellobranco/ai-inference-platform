ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_agent_workflow_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_agent_workflow_check
 CHECK (agent_workflow IN ('tools', 'research', 'compliance'));
