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

-- 1. Add verification_code column to audit_requests table
ALTER TABLE audit_requests 
ADD COLUMN verification_code TEXT;

-- 2. Add a status column to track if they have used it (optional but good practice)
ALTER TABLE audit_requests 
ADD COLUMN access_granted BOOLEAN DEFAULT FALSE;

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