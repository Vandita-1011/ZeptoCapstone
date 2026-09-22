import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection("zepto_policies")

query = "How long does delivery take?"
query_embedding = model.encode([query]).tolist()

results = collection.query(query_embeddings=query_embedding, n_results=3)

for doc_id, doc_text, distance in zip(results["ids"][0], results["documents"][0], results["distances"][0]):
    print(f"{doc_id} (distance={distance:.4f}): {doc_text[:150]}...")