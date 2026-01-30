-- Supabase SQL schema for Nigeria Tax Law embeddings (pgvector)
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
