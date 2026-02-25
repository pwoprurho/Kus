-- Migration: Add 'phone' column to 'audit_requests' table
-- Reason: Fixes 'Could not find the phone column' error during public audit requests.

ALTER TABLE public.audit_requests 
ADD COLUMN IF NOT EXISTS phone TEXT;

-- Verify the change (optional)
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'audit_requests' AND column_name = 'phone';
