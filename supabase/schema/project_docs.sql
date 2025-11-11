create extension if not exists vector;

create table if not exists project_docs (
  id text primary key,
  file_name text,
  chunk_index int,
  content text,
  embedding vector(1536)
);

create index if not exists idx_project_docs_embedding
on project_docs using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create or replace function match_project_docs(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id text,
  file_name text,
  content text,
  similarity float
)
language sql stable as $$
  select
    id,
    file_name,
    content,
    1 - (embedding <=> query_embedding) as similarity
  from project_docs
  where 1 - (embedding <=> query_embedding) > match_threshold
  order by similarity desc
  limit match_count;
$$;
