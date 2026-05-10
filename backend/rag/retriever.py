"""
RAG System: Document ingestion, embedding, and retrieval via ChromaDB.
"""

import os
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

DATA_DIR = Path(__file__).parent.parent / "data"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"

_vectorstore = None  # Singleton


def build_vectorstore(force_rebuild: bool = False) -> Chroma:
    """
    Build or load the ChromaDB vectorstore from financial documents.
    Uses a singleton pattern to avoid reloading on every request.
    """
    global _vectorstore

    if _vectorstore is not None and not force_rebuild:
        return _vectorstore

    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

    # If DB already exists on disk, just load it
    if CHROMA_DIR.exists() and not force_rebuild:
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings,
        )
        return _vectorstore

    # Load and chunk all .txt documents
    docs = []
    for txt_file in DATA_DIR.glob("*.txt"):
        loader = TextLoader(str(txt_file), encoding="utf-8")
        docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(docs)

    _vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
    )
    _vectorstore.persist()

    return _vectorstore


def get_rag_chain():
    """Return a RetrievalQA chain backed by the ChromaDB vectorstore."""
    vectorstore = build_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=False,
    )
    return chain


def query_rag(question: str) -> str:
    """Query the RAG system and return a grounded answer."""
    chain = get_rag_chain()
    result = chain.invoke({"query": question})
    return result.get("result", "I could not find relevant information.")
