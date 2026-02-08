# rag_tax_law.py
"""
Production-Ready RAG (Retrieval-Augmented Generation) for Nigerian Tax Law.

This module implements a complete RAG pipeline using:
- Supabase pgvector for vector storage and similarity search
- Google Generative AI for embeddings (text-embedding-004)
- KusmusAIEngine for response generation

Database Schema (see database/schema.sql):
- Table: tax_law_chunks (id, chunk_text, page_num, embedding vector(768))
- RPC: match_tax_documents(query_embedding, match_threshold, match_count)
"""

import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
import google.generativeai as genai

from db import supabase_admin
from core.engine import KusmusAIEngine

load_dotenv()

# Configure Google AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk with metadata."""
    id: int
    text: str
    page_num: Optional[int]
    similarity: float


class TaxLawRAG:
    """
    Production RAG system for Nigerian Tax Law queries.
    
    Features:
    - Vector similarity search using Supabase pgvector
    - Configurable retrieval parameters
    - Context-aware response generation
    - Source citation with page references
    """
    
    def __init__(
        self,
        embedding_model: str = "models/text-embedding-004",
        generation_model: str = "gemini-2.5-flash",
        match_threshold: float = 0.7,
        match_count: int = 5
    ):
        """
        Initialize the RAG system.
        
        Args:
            embedding_model: Google embedding model for query vectorization
            generation_model: Gemini model for response generation
            match_threshold: Minimum similarity score (0-1) for retrieval
            match_count: Maximum number of chunks to retrieve
        """
        self.embedding_model = embedding_model
        self.generation_model = generation_model
        self.match_threshold = match_threshold
        self.match_count = match_count
        
        # System prompt for tax law responses
        self.system_prompt = """You are an expert Nigerian Tax Law advisor powered by Kusmus AI.
        
Your role is to provide accurate, actionable guidance on Nigerian tax matters based on the 
retrieved legal documents. Always:

1. Cite specific sections/pages when referencing the law
2. Distinguish between mandatory requirements and best practices
3. Highlight important deadlines or penalties where applicable
4. Use clear, professional language accessible to business owners
5. If the context doesn't fully answer the question, acknowledge limitations

Format your response with clear headings and bullet points where appropriate."""

    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for the input text.
        
        Args:
            text: Query text to embed
            
        Returns:
            768-dimensional embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            print(f"[TaxLawRAG] Embedding error: {e}")
            raise

    def _retrieve_chunks(self, query_embedding: List[float]) -> List[RetrievedChunk]:
        """
        Retrieve relevant document chunks using vector similarity search.
        
        Args:
            query_embedding: Embedding vector for the user query
            
        Returns:
            List of RetrievedChunk objects sorted by similarity
        """
        if not supabase_admin:
            print("[TaxLawRAG] Supabase client not available")
            return []
        
        try:
            # Call the RPC function defined in schema.sql
            response = supabase_admin.rpc(
                'match_tax_documents',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': self.match_threshold,
                    'match_count': self.match_count
                }
            ).execute()
            
            if not response.data:
                return []
            
            return [
                RetrievedChunk(
                    id=row['id'],
                    text=row['chunk_text'],
                    page_num=row.get('page_num'),
                    similarity=row['similarity']
                )
                for row in response.data
            ]
        except Exception as e:
            print(f"[TaxLawRAG] Retrieval error: {e}")
            return []

    def _build_context(self, chunks: List[RetrievedChunk]) -> str:
        """
        Build context string from retrieved chunks.
        
        Args:
            chunks: List of retrieved document chunks
            
        Returns:
            Formatted context string for the LLM
        """
        if not chunks:
            return "No relevant tax law documents found in the knowledge base."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            page_ref = f" (Page {chunk.page_num})" if chunk.page_num else ""
            context_parts.append(
                f"[Source {i}{page_ref}]\n{chunk.text}\n"
            )
        
        return "\n---\n".join(context_parts)

    def query(self, user_query: str) -> Tuple[str, List[RetrievedChunk]]:
        """
        Process a tax law query using RAG.
        
        Args:
            user_query: Natural language question about Nigerian tax law
            
        Returns:
            Tuple of (generated_response, retrieved_chunks)
        """
        # Step 1: Generate query embedding
        try:
            query_embedding = self._get_embedding(user_query)
        except Exception as e:
            return f"Error generating query embedding: {e}", []
        
        # Step 2: Retrieve relevant chunks
        chunks = self._retrieve_chunks(query_embedding)
        
        # Step 3: Build context
        context = self._build_context(chunks)
        
        # Step 4: Generate response using KusmusAIEngine
        engine = KusmusAIEngine(
            system_instruction=self.system_prompt,
            model_name=self.generation_model
        )
        
        augmented_prompt = f"""Based on the following Nigerian Tax Law documents, answer the user's question.

RETRIEVED LEGAL CONTEXT:
{context}

USER QUESTION: {user_query}

Provide a comprehensive, accurate response with citations to the source documents."""
        
        response, _ = engine.generate_response(augmented_prompt)
        
        return response, chunks

    def add_document_chunk(
        self,
        chunk_text: str,
        page_num: Optional[int] = None
    ) -> bool:
        """
        Add a new document chunk to the knowledge base.
        
        Args:
            chunk_text: Text content of the chunk
            page_num: Optional page number reference
            
        Returns:
            True if successful, False otherwise
        """
        if not supabase_admin:
            print("[TaxLawRAG] Supabase client not available")
            return False
        
        try:
            # Generate embedding for the chunk
            result = genai.embed_content(
                model=self.embedding_model,
                content=chunk_text,
                task_type="retrieval_document"
            )
            embedding = result['embedding']
            
            # Insert into Supabase
            supabase_admin.table('tax_law_chunks').insert({
                'chunk_text': chunk_text,
                'page_num': page_num,
                'embedding': embedding
            }).execute()
            
            return True
        except Exception as e:
            print(f"[TaxLawRAG] Error adding chunk: {e}")
            return False

    def bulk_add_chunks(self, chunks: List[Dict]) -> int:
        """
        Add multiple document chunks to the knowledge base.
        
        Args:
            chunks: List of dicts with 'text' and optional 'page_num' keys
            
        Returns:
            Number of successfully added chunks
        """
        success_count = 0
        for chunk in chunks:
            if self.add_document_chunk(
                chunk_text=chunk['text'],
                page_num=chunk.get('page_num')
            ):
                success_count += 1
        return success_count

    def get_stats(self) -> Dict:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dict with chunk count and other stats
        """
        if not supabase_admin:
            return {"error": "Supabase not available"}
        
        try:
            response = supabase_admin.table('tax_law_chunks').select(
                'id', count='exact'
            ).execute()
            return {
                "total_chunks": response.count or 0,
                "embedding_model": self.embedding_model,
                "generation_model": self.generation_model
            }
        except Exception as e:
            return {"error": str(e)}


# Singleton instance for app-wide use
tax_rag = TaxLawRAG()


# Convenience function for quick queries
def query_tax_law(question: str) -> str:
    """
    Quick helper to query tax law knowledge base.
    
    Args:
        question: Natural language tax law question
        
    Returns:
        Generated response with citations
    """
    response, _ = tax_rag.query(question)
    return response


if __name__ == "__main__":
    # Test the RAG system
    print("=== Tax Law RAG System Test ===")
    print(f"Stats: {tax_rag.get_stats()}")
    
    test_query = "What are the VAT registration requirements for small businesses in Nigeria?"
    print(f"\nQuery: {test_query}")
    print("-" * 50)
    
    response, chunks = tax_rag.query(test_query)
    print(f"Retrieved {len(chunks)} chunks")
    print(f"\nResponse:\n{response}")
