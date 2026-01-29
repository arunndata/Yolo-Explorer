from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
    
    def encode(self, text):
        return self.model.encode(text).tolist()
    
    def encode_batch(self, texts):
        return self.model.encode(texts).tolist()