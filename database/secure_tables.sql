-- Secure User Profiles
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Admins can view all profiles" ON public.user_profiles
    FOR SELECT USING (
        (SELECT role FROM public.user_profiles WHERE id = auth.uid()) IN ('supa_admin', 'admin')
    );

-- Secure Audit Requests (Leads)
ALTER TABLE public.audit_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can view leads" ON public.audit_requests
    FOR ALL USING (
        (SELECT role FROM public.user_profiles WHERE id = auth.uid()) IN ('supa_admin', 'admin')
    );

CREATE POLICY "Public can insert leads" ON public.audit_requests
    FOR INSERT WITH CHECK (true);

-- Secure Blog Posts
ALTER TABLE public.blog_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can view published posts" ON public.blog_posts
    FOR SELECT USING (status = 'Published');

CREATE POLICY "Admins can manage posts" ON public.blog_posts
    FOR ALL USING (
        (SELECT role FROM public.user_profiles WHERE id = auth.uid()) IN ('supa_admin', 'admin', 'editor')
    );
