#!/usr/bin/env python3
"""Build the FAISS vector index from Amazon financial PDFs.

Reads PDFs from docs/knowledgebase-files/, chunks them with
RecursiveCharacterTextSplitter, embeds with Titan Embeddings V2,
and serialises the FAISS index to data/faiss_index/.
"""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_aws import BedrockEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "docs" / "knowledgebase-files"
OUTPUT_DIR = PROJECT_ROOT / "data" / "faiss_index"

PDF_FILES = [
    "Amazon-2024-Annual-Report.pdf",
    "AMZN-Q2-2025-Earnings-Release.pdf",
    "AMZN-Q3-2025-Earnings-Release.pdf",
]


def main() -> None:
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

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(all_docs)
    print(f"Total chunks after splitting: {len(chunks)}")

    print("Creating embeddings with Titan Embeddings V2 (512d)...")
    embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name="us-east-1",
    )

    print("Building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(OUTPUT_DIR))
    print(f"FAISS index saved to {OUTPUT_DIR}")

    results = vectorstore.similarity_search("Amazon AI business", k=3)
    print(f"\nVerification: retrieved {len(results)} chunks for test query")
    for i, doc in enumerate(results):
        print(f"  [{i+1}] {doc.metadata.get('source', 'unknown')}, page {doc.metadata.get('page')}")
        print(f"      {doc.page_content[:100]}...")


if __name__ == "__main__":
    main()
