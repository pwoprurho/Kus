-- Enable RLS on the table
ALTER TABLE public.tax_law_chunks ENABLE ROW LEVEL SECURITY;

-- Policy: Allow Service Role (Admin) full access
-- Note: Service role bypasses RLS, but this is good for explicit admin users
CREATE POLICY "Enable all access for service role" ON public.tax_law_chunks
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Policy: Allow authenticated users (like the Tax Agent logic if running as user) to read
CREATE POLICY "Enable read access for authenticated users" ON public.tax_law_chunks
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- Policy: Allow public read access (if you want the public demo to work without login)
-- CREATE POLICY "Enable read access for public" ON public.tax_law_chunks
--     FOR SELECT
--     USING (true);
