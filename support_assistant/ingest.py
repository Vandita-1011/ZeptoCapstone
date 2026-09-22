import os
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = "docs"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "zepto_policies"

model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)


def load_documents():
    docs = []
    for filename in sorted(os.listdir(DOCS_DIR)):
        if filename.endswith(".txt"):
            doc_id = filename.replace(".txt", "")
            with open(os.path.join(DOCS_DIR, filename), "r", encoding="utf-8") as f:
                content = f.read().strip()
            docs.append((doc_id, content))
    return docs


def ingest():
    docs = load_documents()
    ids = [doc_id for doc_id, _ in docs]
    texts = [content for _, content in docs]

    embeddings = model.encode(texts).tolist()

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings
    )
    print(f"Ingested {len(docs)} documents into ChromaDB collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    ingest()