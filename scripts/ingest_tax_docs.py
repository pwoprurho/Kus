# scripts/ingest_tax_docs.py
import os
import sys
import logging
from typing import List, Optional
from pypdf import PdfReader
from dotenv import load_dotenv

# Add parent directory to path to import rag_tax_law
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_tax_law import tax_rag

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "docs")

def ingest_pdf(file_path: str):
    """Parses a PDF and adds chunks to the RAG knowledge base."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    logger.info(f"Indexing: {os.path.basename(file_path)}")
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text.strip():
                continue
            
            # Simple chunking by page for now
            # In a more advanced version, we'd use LangChain character splitters
            page_num = i + 1
            logger.info(f"  Adding page {page_num}/{total_pages}...")
            
            success = tax_rag.add_document_chunk(
                chunk_text=text,
                page_num=page_num
            )
            
            if not success:
                logger.warning(f"    Failed to add page {page_num}")
                
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")

def main():
    if not os.path.exists(DOCS_DIR):
        logger.error(f"Docs directory not found: {DOCS_DIR}")
        return

    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf")]
    
    if not pdf_files:
        logger.warning("No PDF files found in static/docs")
        return

    logger.info(f"Found {len(pdf_files)} PDFs to index.")
    
    for pdf in pdf_files:
        full_path = os.path.join(DOCS_DIR, pdf)
        ingest_pdf(full_path)

    logger.info("Ingestion completed.")
    print(f"Final Knowledge Base Stats: {tax_rag.get_stats()}")

if __name__ == "__main__":
    main()
