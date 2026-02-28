-- Migration: Add company_name to audit_requests
-- Description: Separates entity name from representative name for better CRM tracking.

ALTER TABLE public.audit_requests 
ADD COLUMN IF NOT EXISTS company_name TEXT;

-- Update comment for clarity
COMMENT ON COLUMN public.audit_requests.company_name IS 'The organization or company requesting the audit';
COMMENT ON COLUMN public.audit_requests.name IS 'The individual representative or contact person';
