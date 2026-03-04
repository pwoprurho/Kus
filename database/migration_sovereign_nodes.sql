-- =========================================================
-- SOVEREIGN NODES TABLE
-- Tracks dedicated LLM infrastructure provisioned per client
-- =========================================================

CREATE TABLE IF NOT EXISTS public.sovereign_nodes (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id uuid REFERENCES public.clients(id) NOT NULL UNIQUE,

    -- Infrastructure
    node_url text NOT NULL,              -- Ollama/vLLM base endpoint (e.g., http://10.0.1.5:11434)
    api_key text NOT NULL UNIQUE,        -- Client's unique proxy API key
    model_name text NOT NULL DEFAULT 'llama3:8b',

    -- Status tracking
    status text NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'suspended', 'offline')),

    -- Resource allocation
    storage_gb numeric DEFAULT 20,

    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Index for fast API key lookups (used on every proxy request)
CREATE UNIQUE INDEX sovereign_nodes_api_key_idx ON public.sovereign_nodes (api_key);
CREATE UNIQUE INDEX sovereign_nodes_client_id_idx ON public.sovereign_nodes (client_id);

-- Enable RLS
ALTER TABLE public.sovereign_nodes ENABLE ROW LEVEL SECURITY;

-- Policy: Admins can manage all nodes
CREATE POLICY "Admins manage sovereign nodes" ON public.sovereign_nodes
    FOR ALL USING (
        (SELECT role FROM public.user_profiles WHERE id = auth.uid())
        IN ('supa_admin', 'admin')
    );

-- Policy: System/API can read nodes (for proxy auth)
CREATE POLICY "System read sovereign nodes" ON public.sovereign_nodes
    FOR SELECT USING (true);

-- Auto-update the updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_sovereign_node_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sovereign_node_updated
    BEFORE UPDATE ON public.sovereign_nodes
    FOR EACH ROW EXECUTE FUNCTION public.update_sovereign_node_timestamp();
