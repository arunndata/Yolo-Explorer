from pymongo import MongoClient
from typing import List, Dict
from src.config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME

class VectorDB:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.collection = self.db[COLLECTION_NAME]
    
    def create_vector_index(self):
        """Run this once manually in MongoDB Atlas UI or via MongoDB commands"""
        # In Atlas UI: Create Search Index -> Vector Search
        # Index name: code_vector_index
        # Field: embedding, Dimensions: 384, Similarity: cosine
        pass
    
    def insert_chunks(self, chunks: List[Dict]):
        if chunks:
            self.collection.insert_many(chunks)
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict]:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "code_vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 100,
                    "limit": top_k
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "file_path": 1,
                    "name": 1,
                    "type": 1,
                    "code": 1,
                    "docstring": 1,
                    "lineno": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        return list(self.collection.aggregate(pipeline))
    
    def clear_collection(self):
        self.collection.delete_many({})