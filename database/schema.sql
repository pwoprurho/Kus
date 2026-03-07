-- =========================================================
-- KUSMUS AI MASTER SCHEMA
-- Includes: Tables, Triggers, Functions, and RLS Policies
-- =========================================================

-- ---------------------------------------------------------
-- 1. TABLE CREATION
-- ---------------------------------------------------------

-- 1.1 USER PROFILES (Links to Supabase Auth)
CREATE TABLE public.user_profiles (
    id uuid references auth.users(id) not null primary key,
    full_name text not null,
    email text unique not null,
    
    -- Hierarchy: supa_admin > admin > editor > talent > intern
    role text not null default 'intern' 
        check (role in ('supa_admin', 'admin', 'editor', 'talent', 'intern')),
        
    location text,
    created_at timestamp with time zone default now()
);

-- Index for faster lookups based on email
CREATE UNIQUE INDEX user_profiles_email_idx ON public.user_profiles (email);


-- 1.2 AUDIT REQUESTS (Public Leads from Home Page)
CREATE TABLE public.audit_requests (
    id uuid default gen_random_uuid() primary key,
    name text not null,
    email text not null,
    phone text,
    message text,
    created_at timestamp with time zone default now()
);


-- 1.3 CLIENTS (Tier 1 CRM)
CREATE TABLE public.clients (
    id uuid default gen_random_uuid() primary key,
    
    -- Links back to the initial form submission (optional FK)
    audit_request_id uuid references public.audit_requests(id), 

    company_name text unique not null,
    contact_name text,
    contact_email text,
    
    -- Business Logic Categories
    tier text not null check (tier in ('Tier 1 Partner', 'Tier 2 Client', 'Strategic Lead')),
    status text not null check (status in ('Lead', 'Engaged', 'Audit Phase', 'Deployment', 'Archived')),
    
    sector text,
    value_usd numeric, -- Estimated contract value
    created_at timestamp with time zone default now()
);


-- 1.4 BLOG POSTS (AI Content Engine)
CREATE TABLE public.blog_posts (
    id serial primary key,
    
    -- Links author/editor back to user_profiles
    author_id uuid references public.user_profiles(id), 

    title text not null,
    summary text,
    content_html text not null,
    
    status text not null default 'Draft' check (status in ('Draft', 'Published', 'Pending Review', 'Archived')),
    
    tags text[], -- Array for tags (e.g., {'AI', 'Logistics'})
    published_at timestamp with time zone,
    created_at timestamp with time zone default now()
);


-- 1.5 CHAT SESSIONS (AI Assistant Tracking)
CREATE TABLE public.chat_sessions (
    id uuid default gen_random_uuid() primary key,
    ip_address text, -- For security/analytics
    user_agent text, -- Browser info
    started_at timestamp with time zone default now()
);


-- 1.6 CHAT MESSAGES (Conversation History)
CREATE TABLE public.chat_messages (
    id serial primary key,
    session_id uuid references public.chat_sessions(id) not null, 
    sender text not null check (sender in ('user', 'ai')),
    content text not null,
    created_at timestamp with time zone default now()
);


-- 1.7 TAX LAW EMBEDDINGS (pgvector RAG)
-- Requires pgvector extension enabled on your Supabase project
CREATE TABLE public.tax_law_chunks (
    id bigserial primary key,
    chunk_text text not null,
    page_num int,
    embedding vector(768) not null, -- 768 for Google embedding, adjust if needed
    created_at timestamptz default now()
);

-- Create an index for fast vector search
CREATE INDEX tax_law_chunks_embedding_idx ON public.tax_law_chunks USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Optional: full-text search index
CREATE INDEX tax_law_chunks_text_idx ON public.tax_law_chunks USING gin (to_tsvector('english', chunk_text));


-- ---------------------------------------------------------
-- 2. AUTOMATION & TRIGGERS
-- ---------------------------------------------------------

-- Function to auto-create a profile after a user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  insert into public.user_profiles (id, full_name, email, role)
  values (new.id, new.raw_user_meta_data->>'full_name', new.email, 'intern');
  return new;
END;
$$ language plpgsql security definer;

-- Trigger that fires AFTER a user is inserted into auth.users
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();


-- ---------------------------------------------------------
-- 3. ROW LEVEL SECURITY (RLS) POLICIES
-- ---------------------------------------------------------

-- Enable RLS on all tables (Deny All by default)
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.blog_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_law_chunks ENABLE ROW LEVEL SECURITY;

-- Helper Functions for Roles
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.user_profiles
    WHERE id = auth.uid() 
    AND role IN ('admin', 'supa_admin')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.is_staff()
RETURNS boolean AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.user_profiles
    WHERE id = auth.uid() 
    AND role IN ('supa_admin', 'admin', 'editor', 'talent', 'intern')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- POLICIES: USER PROFILES
CREATE POLICY "Users can see own profile" ON public.user_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Admins read all profiles" ON public.user_profiles FOR SELECT USING ((SELECT role FROM public.user_profiles WHERE id = auth.uid()) IN ('supa_admin', 'admin', 'editor'));
CREATE POLICY "Supa Admin update profiles" ON public.user_profiles FOR UPDATE USING ((SELECT role FROM public.user_profiles WHERE id = auth.uid()) = 'supa_admin');

-- POLICIES: AUDIT REQUESTS
CREATE POLICY "Public insert leads" ON public.audit_requests FOR INSERT WITH CHECK (true);
CREATE POLICY "Admins view leads" ON public.audit_requests FOR SELECT USING (public.is_admin() OR (SELECT role FROM public.user_profiles WHERE id = auth.uid()) = 'editor');

-- POLICIES: CLIENTS
CREATE POLICY "Staff view clients" ON public.clients FOR SELECT USING ((SELECT role FROM public.user_profiles WHERE id = auth.uid()) IN ('supa_admin', 'admin', 'editor'));
CREATE POLICY "Admins manage clients" ON public.clients FOR ALL USING (public.is_admin());

-- POLICIES: BLOG POSTS
CREATE POLICY "Public read published posts" ON public.blog_posts FOR SELECT USING (status = 'Published');
CREATE POLICY "Staff read all posts" ON public.blog_posts FOR SELECT USING (public.is_staff());
CREATE POLICY "Authors edit own posts" ON public.blog_posts FOR UPDATE USING (auth.uid() = author_id);
CREATE POLICY "Editors manage all posts" ON public.blog_posts FOR ALL USING ((SELECT role FROM public.user_profiles WHERE id = auth.uid()) IN ('supa_admin', 'admin', 'editor'));

-- POLICIES: CHAT
CREATE POLICY "Public insert chat" ON public.chat_sessions FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert messages" ON public.chat_messages FOR INSERT WITH CHECK (true);
CREATE POLICY "Admins read chats" ON public.chat_messages FOR SELECT USING (public.is_admin());

-- POLICIES: TAX LAW CHUNKS
CREATE POLICY "Staff manage tax law chunks" ON public.tax_law_chunks
    FOR ALL USING (
        (SELECT role FROM public.user_profiles WHERE id = auth.uid()) 
        IN ('supa_admin', 'admin', 'editor')
    );

-- ---------------------------------------------------------
-- 4. RPC FUNCTIONS (For RAG)
-- ---------------------------------------------------------

create or replace function match_tax_documents (
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
returns table (
  id bigint,
  chunk_text text,
  page_num int,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    tax_law_chunks.id,
    tax_law_chunks.chunk_text,
    tax_law_chunks.page_num,
    1 - (tax_law_chunks.embedding <=> query_embedding) as similarity
  from tax_law_chunks
  where 1 - (tax_law_chunks.embedding <=> query_embedding) > match_threshold
  order by tax_law_chunks.embedding <=> query_embedding
  limit match_count;
end;
$$;


-- 1. Add verification_code column to audit_requests table
ALTER TABLE audit_requests 
ADD COLUMN verification_code TEXT;

-- 3. Add access_granted column to audit_requests table
ALTER TABLE audit_requests 
ADD COLUMN access_granted BOOLEAN DEFAULT FALSE;

-- 4. Add phone column to audit_requests table (migration)
ALTER TABLE audit_requests 
ADD COLUMN IF NOT EXISTS phone TEXT;

-- 1. Ensure the Secure Chat Table exists (Fixes "Disappearing Messages")
CREATE TABLE IF NOT EXISTS public.secure_chat_messages (
    id uuid default gen_random_uuid() primary key,
    client_id uuid references public.clients(id) not null,
    admin_id uuid references auth.users(id), 
    sender_type text not null check (sender_type in ('client', 'admin')),
    encrypted_content text not null, 
    
    -- NEW: File Attachment Support
    attachment_url text, 
    attachment_type text, -- e.g., 'image', 'document'
    
    is_read boolean default false,
    created_at timestamp with time zone default now()
);

-- 2. Enable Security (RLS)
ALTER TABLE public.secure_chat_messages ENABLE ROW LEVEL SECURITY;

-- 3. Policy: Allow Staff to view/manage all secure chats
CREATE POLICY "Staff manage secure chats" ON public.secure_chat_messages
    FOR ALL USING (
        (SELECT role FROM public.user_profiles WHERE id = auth.uid()) 
        IN ('supa_admin', 'admin', 'editor')
    );

-- 4. Policy: Allow System/API to insert messages
CREATE POLICY "System insert secure chats" ON public.secure_chat_messages
    FOR INSERT WITH CHECK (true);

-- 5. STORAGE BUCKET SETUP (For File Uploads)
-- You must manually create a bucket named 'secure-files' in your Supabase Dashboard
-- Go to Storage -> New Bucket -> Name: 'secure-files' -> Public: False

-- Create table for Sandbox tracking
CREATE TABLE IF NOT EXISTS public.sandbox_logs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    persona_id text NOT NULL, -- e.g., 'downtime_mitigation'
    user_message_length int,   -- Track engagement depth
    created_at timestamp with time zone DEFAULT now()
);

-- Enable RLS (Internal only)
ALTER TABLE public.sandbox_logs ENABLE ROW LEVEL SECURITY;

-- Allow the Service Role (Admin App) to manage logs
CREATE POLICY "Admin full access to logs" ON public.sandbox_logs
    FOR ALL USING (true);

-- has_attachment column for sandbox_logs
ALTER TABLE public.sandbox_logs
ADD COLUMN IF NOT EXISTS has_attachment boolean DEFAULT false;


-- =========================================================
-- MIGRATION: Clients Table Restructure
-- The application's auth system uses clients as a login table,
-- not the original CRM structure. These columns are required.
-- =========================================================

-- Core auth fields used by routes/auth.py
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS full_name text;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS password_hash text;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS recovery_key text;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS phone text;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now();

-- Make company_name nullable (clients register with email, not company)
ALTER TABLE public.clients ALTER COLUMN company_name DROP NOT NULL;
-- Remove the strict tier/status constraints for auth-based clients
ALTER TABLE public.clients ALTER COLUMN tier DROP NOT NULL;
ALTER TABLE public.clients ALTER COLUMN status DROP NOT NULL;

-- Index for fast email-based auth lookups
CREATE UNIQUE INDEX IF NOT EXISTS clients_email_idx ON public.clients (email);

-- Policy: Allow service role to manage all client records
CREATE POLICY "Service role manages clients" ON public.clients
    FOR ALL USING (true);


-- =========================================================
-- MIGRATION: Audit Requests — Missing Columns
-- =========================================================

ALTER TABLE public.audit_requests
ADD COLUMN IF NOT EXISTS company_name text;

ALTER TABLE public.audit_requests
ADD COLUMN IF NOT EXISTS hosting_preference text;

ALTER TABLE public.audit_requests
ADD COLUMN IF NOT EXISTS is_registered boolean DEFAULT false;


-- =========================================================
-- NEW TABLE: Sovereign Nodes
-- Tracks dedicated GPU instances provisioned for clients.
-- Used by services/sovereign_node.py and routes/sovereign.py
-- =========================================================

CREATE TABLE IF NOT EXISTS public.sovereign_nodes (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id uuid REFERENCES public.clients(id) NOT NULL,

    -- Node connection details
    node_url text,
    api_key text NOT NULL,

    -- Model & hardware configuration
    model_name text NOT NULL DEFAULT 'llama3:8b',
    storage_gb integer DEFAULT 20,

    -- Lifecycle
    status text NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'offline', 'terminated')),
    hosting_type text DEFAULT 'Managed'
        CHECK (hosting_type IN ('Managed', 'Self-Hosted')),

    -- RunPod integration
    pod_id text,  -- RunPod pod identifier (NULL for self-hosted)

    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- One node per client (enforced at DB level)
CREATE UNIQUE INDEX IF NOT EXISTS sovereign_nodes_client_idx
    ON public.sovereign_nodes (client_id);

-- Enable RLS
ALTER TABLE public.sovereign_nodes ENABLE ROW LEVEL SECURITY;

-- Policy: Service role full access (backend manages all nodes)
CREATE POLICY "Service role manages sovereign nodes" ON public.sovereign_nodes
    FOR ALL USING (true);

-- Policy: Admins can view all nodes
CREATE POLICY "Admins view sovereign nodes" ON public.sovereign_nodes
    FOR SELECT USING (
        (SELECT role FROM public.user_profiles WHERE id = auth.uid())
        IN ('supa_admin', 'admin')
    );