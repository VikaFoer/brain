-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    doc_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(1000),
    act_number VARCHAR(100),
    date DATE,
    authority VARCHAR(500),
    url TEXT,
    source TEXT,
    file_type VARCHAR(20),
    file_path TEXT,
    text_length INTEGER,
    needs_ocr BOOLEAN DEFAULT FALSE,
    reference_block TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chunks table with pgvector
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id VARCHAR(100) PRIMARY KEY,
    doc_id VARCHAR(50) NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding vector(3072),  -- text-embedding-3-large default dimensions
    section_path TEXT[],  -- Array: [Розділ, Стаття, Частина, Пункт]
    chunk_index INTEGER,
    char_start INTEGER,
    char_end INTEGER,
    tokens INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_section_path ON chunks USING GIN(section_path);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- Adjust based on data size

-- Index for documents
CREATE INDEX IF NOT EXISTS idx_documents_act_number ON documents(act_number);
CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(date);
CREATE INDEX IF NOT EXISTS idx_documents_authority ON documents(authority);

-- Function to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for documents
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();




