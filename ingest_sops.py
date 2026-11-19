"""Build the optional persistent Chroma vector store from the demo runbook.

The portfolio frontend works without running this script; it labels its
runbook fallback honestly. Install requirements-ai.txt for embedding ingestion.
"""
from __future__ import annotations

from pathlib import Path
from aiops.integrations import ROOT, SOP_FILE


def ingest_documents():
    if not SOP_FILE.is_file():
        raise FileNotFoundError(f"Missing SOP document: {SOP_FILE}")
    try:
        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_core.documents import Document
    except ImportError as exc:
        raise RuntimeError("Install optional AI dependencies: pip install -r requirements-ai.txt") from exc
    text = SOP_FILE.read_text(encoding="utf-8")
    chunks = RecursiveCharacterTextSplitter(chunk_size=650, chunk_overlap=75).split_documents(
        [Document(page_content=text, metadata={"source": str(SOP_FILE.relative_to(ROOT))})])
    if not chunks:
        raise RuntimeError("SOP is empty. Nothing to ingest.")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    collection = Chroma.from_documents(documents=chunks, embedding=embeddings,
                                       persist_directory=str(ROOT / "chroma_db"),
                                       collection_name="sentinelops_sops")
    print(f"Ingested {len(chunks)} chunks into {ROOT / 'chroma_db'}. Source: {SOP_FILE.name}")
    return collection


if __name__ == "__main__":
    ingest_documents()
