#!/usr/bin/env python3
"""Build the FAISS vector index from Amazon financial PDFs.

Reads PDFs from docs/knowledgebase-files/, chunks them with
RecursiveCharacterTextSplitter, embeds with Titan Embeddings V2,
and serialises the FAISS index to data/faiss_index/.

Chunk size, overlap, embedding model, and output path are all read
from Settings (.env / environment variables).
"""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_aws import BedrockEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ai_stock_agent.infrastructure.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "docs" / "knowledgebase-files"

PDF_FILES = [
    "Amazon-2024-Annual-Report.pdf",
    "AMZN-Q2-2025-Earnings-Release.pdf",
    "AMZN-Q3-2025-Earnings-Release.pdf",
]


def main() -> None:
    settings = Settings()
    output_dir = Path(settings.faiss_index_path)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    pdfs = [PDF_DIR / f for f in PDF_FILES]
    for p in pdfs:
        if not p.exists():
            print(f"ERROR: PDF not found: {p}", file=sys.stderr)
            sys.exit(1)

    print(f"Loading {len(pdfs)} PDFs...")
    all_docs = []
    for pdf_path in pdfs:
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        print(f"  {pdf_path.name}: {len(docs)} pages")
        all_docs.extend(docs)

    print(f"Total pages loaded: {len(all_docs)}")

    print(f"Chunking with size={settings.chunk_size}, overlap={settings.chunk_overlap}...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(all_docs)
    print(f"Total chunks after splitting: {len(chunks)}")

    print(f"Creating embeddings with {settings.embedding_model_id} ({settings.embedding_dims}d)...")
    embeddings = BedrockEmbeddings(
        model_id=settings.embedding_model_id,
        region_name=settings.aws_region,
    )

    print("Building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    output_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(output_dir))
    print(f"FAISS index saved to {output_dir}")

    k = settings.retriever_k
    results = vectorstore.similarity_search("Amazon AI business", k=k)
    print(f"\nVerification: retrieved {len(results)} chunks for test query (k={k})")
    for i, doc in enumerate(results):
        print(f"  [{i+1}] {doc.metadata.get('source', 'unknown')}, page {doc.metadata.get('page')}")
        print(f"      {doc.page_content[:120]}...")


if __name__ == "__main__":
    main()
