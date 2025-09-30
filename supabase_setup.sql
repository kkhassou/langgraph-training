-- Supabase Vector Store Setup Script
-- Run this in Supabase SQL Editor to create the necessary tables and functions

-- 1. Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create default collection table
CREATE TABLE IF NOT EXISTS default_collection (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create index for vector similarity search (optional but recommended for performance)
CREATE INDEX IF NOT EXISTS default_collection_embedding_idx
ON default_collection
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Create kanagawa_history collection (example)
CREATE TABLE IF NOT EXISTS kanagawa_history (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Create index for kanagawa_history
CREATE INDEX IF NOT EXISTS kanagawa_history_embedding_idx
ON kanagawa_history
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 6. Optional: Create a function for similarity search (advanced)
CREATE OR REPLACE FUNCTION search_documents(
    table_name TEXT,
    query_embedding vector(768),
    match_threshold FLOAT DEFAULT 0.0,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY EXECUTE format(
        'SELECT 
            id,
            content,
            metadata,
            1 - (embedding <=> %L) AS similarity
        FROM %I
        WHERE 1 - (embedding <=> %L) > %L
        ORDER BY embedding <=> %L
        LIMIT %L',
        query_embedding,
        table_name,
        query_embedding,
        match_threshold,
        query_embedding,
        match_count
    );
END;
$$;

-- 7. Grant necessary permissions (adjust as needed)
-- These are typically handled automatically, but you can uncomment if needed
-- GRANT ALL ON default_collection TO authenticated;
-- GRANT ALL ON kanagawa_history TO authenticated;

-- 8. Create RLS policies if needed (for security)
-- ALTER TABLE default_collection ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can insert their own documents" ON default_collection
--     FOR INSERT WITH CHECK (true);
-- CREATE POLICY "Users can view all documents" ON default_collection
--     FOR SELECT USING (true);
