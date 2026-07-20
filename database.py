import os
import chromadb
from chromadb.utils import embedding_functions
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# --- SQLite Setup (Relational DB) ---
SQLITE_DB_PATH = "sqlite:///aidm_database.db"
engine = create_engine(SQLITE_DB_PATH, echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ChromaDB Setup (Vector DB) ---
# We initialize ChromaDB to store data on disk locally.
CHROMA_DATA_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

def get_embedding_function(use_api=False, api_key=None):
    """
    Flexible embedding function setup.
    Defaults to the free, local SentenceTransformers model.
    Can be swapped to an API (like OpenAI) if local ingestion is too slow.
    """
    if use_api and api_key:
        # Example: Using OpenAI API for embeddings if configured to outsource
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-small"
        )
    else:
        # Default: Use local processing (free, runs on CPU)
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

def get_collection(collection_name: str, use_api=False, api_key=None):
    """
    Retrieves or creates a ChromaDB collection.
    collection_name will typically be 'global_rules' or 'campaign_{id}_lore'.
    """
    ef = get_embedding_function(use_api, api_key)
    return chroma_client.get_or_create_collection(
        name=collection_name, 
        embedding_function=ef
    )
