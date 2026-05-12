import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class VectorMemory:
    def __init__(self, embedding_dim=768):
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.documents = []
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def add_document(self, document):
        embedding = self.model.encode([document])[0]
        self.index.add(np.array([embedding], dtype=np.float32))
        self.documents.append(document)

    def search(self, query, k=5):
        query_embedding = self.model.encode([query])[0]
        distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), k)
        return [self.documents[i] for i in indices[0]]