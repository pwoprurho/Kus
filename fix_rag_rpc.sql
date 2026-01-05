-- Run this in your Supabase SQL Editor to enable RAG search

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
