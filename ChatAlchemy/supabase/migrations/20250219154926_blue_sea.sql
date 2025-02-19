/*
  # Create documents table for knowledge base

  1. New Tables
    - `documents`
      - `id` (uuid, primary key)
      - `content` (text, stores the document content)
      - `created_at` (timestamp)
      - `metadata` (jsonb, for additional document metadata)

  2. Extensions
    - Enable pg_trgm for text search capabilities

  3. Security
    - Enable RLS on documents table
    - Add policy for authenticated users to read documents
*/

-- Enable the pg_trgm extension for text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create the documents table
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

-- Create a GiST index for text search
CREATE INDEX IF NOT EXISTS documents_content_trgm_idx ON documents USING gist (content gist_trgm_ops);

-- Enable Row Level Security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Create policy for reading documents
CREATE POLICY "Allow reading documents"
  ON documents
  FOR SELECT
  TO authenticated
  USING (true);