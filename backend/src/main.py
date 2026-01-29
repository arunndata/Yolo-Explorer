from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.embedder import Embedder
from src.database import VectorDB
from src.generator import ResponseGenerator
from src.config import TOP_K_RESULTS, LLM_MODEL
from datetime import datetime
import os

app = FastAPI(title="YOLO Code Assistant")

# Initialize components
embedder = Embedder()
db = VectorDB()
generator = ResponseGenerator()

class QuestionRequest(BaseModel):
    question: str
    top_k: int = TOP_K_RESULTS

class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list

@app.get("/")
def root():
    return {"message": "YOLO Code Assistant API"}

@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    try:
        # Generate embedding for question
        query_vector = embedder.encode(request.question)
        
        # Search for relevant code chunks
        results = db.search(query_vector, request.top_k)
        
        if not results:
            raise HTTPException(status_code=404, detail="No relevant code found")
        
        # Generate answer
        answer = generator.generate(request.question, results)
        
        # Format sources
        sources = [
            {
                "file": r["file_path"],
                "name": r["name"],
                "type": r["type"],
                "line": r["lineno"]
            }
            for r in results
        ]
        
        return AnswerResponse(
            question=request.question,
            answer=answer,
            sources=sources
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/stats")
def get_stats():
    """Get system statistics"""
    try:
        # Get total chunks from MongoDB
        total_chunks = db.collection.count_documents({})
        
        # Get embedding model name
        embedding_model_name = "all-MiniLM-L6-v2"  # Default
        if hasattr(embedder, 'model'):
            if hasattr(embedder.model, 'model_name'):
                embedding_model_name = embedder.model.model_name
            elif hasattr(embedder.model, '_model_name'):
                embedding_model_name = embedder.model._model_name
        
        # Get database info
        db_name = db.db.name if hasattr(db, 'db') else "yolo_codebase"
        collection_name = db.collection.name if hasattr(db, 'collection') else "code_chunks"
        
        return {
            "total_chunks": total_chunks,
            "model": LLM_MODEL,
            "embedding_model": embedding_model_name,
            "database": f"MongoDB Atlas ({db_name})",
            "collection": collection_name,
            "last_indexed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "online"
        }
    except Exception as e:
        # Return partial stats even if some fail
        return {
            "total_chunks": 0,
            "model": LLM_MODEL,
            "embedding_model": "unknown",
            "database": "MongoDB Atlas",
            "collection": "code_chunks",
            "error": str(e),
            "status": "error"
        }


# @app.get("/last-prompt")
# def get_last_prompt():
#     """Retrieve the last prompt sent to LLM"""
#     try:
#         content = generator.get_last_prompt()
#         return {
#             "prompt": content,
#             "path": generator.get_last_prompt_path()
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.get("/download-prompt")
# def download_last_prompt():
#     """Download the last_prompt.txt file"""
#     try:
#         prompt_path = generator.get_last_prompt_path()
#         
#         if os.path.exists(prompt_path):
#             return FileResponse(
#                 path=prompt_path,
#                 filename="last_prompt.txt",
#                 media_type="text/plain"
#             )
#         else:
#             raise HTTPException(
#                 status_code=404, 
#                 detail="No prompt file found. Generate a response first."
#             )
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear-cache")
def clear_cache():
    """Clear the response cache"""
    try:
        generator.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))