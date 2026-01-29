import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexer import CodeIndexer
from src.embedder import Embedder
from src.database import VectorDB

def main():
    # Path to cloned ultralytics repository
    YOLO_SOURCE = input("Enter path to ultralytics directory: ").strip()
    
    if not Path(YOLO_SOURCE).exists():
        print(f"Error: Directory {YOLO_SOURCE} not found")
        return
    
    print("Step 1: Extracting code chunks...")
    indexer = CodeIndexer(YOLO_SOURCE)
    chunks = indexer.extract_code_chunks()
    print(f"Found {len(chunks)} code chunks")
    
    print("\nStep 2: Generating embeddings...")
    embedder = Embedder()
    texts = [chunk["text_for_embedding"] for chunk in chunks]
    embeddings = embedder.encode_batch(texts)
    
    # Add embeddings to chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
        del chunk["text_for_embedding"]
    
    print("\nStep 3: Uploading to MongoDB...")
    db = VectorDB()
    db.clear_collection()
    db.insert_chunks(chunks)
    
    print(f"\nSuccess! Indexed {len(chunks)} code chunks")
    print("\nNEXT STEPS:")
    print("1. Create vector search index in MongoDB Atlas:")
    print("   - Index name: code_vector_index")
    print("   - Field: embedding")
    print("   - Dimensions: 384")
    print("   - Similarity: cosine")
    print("2. Run: uvicorn src.main:app --reload")

if __name__ == "__main__":
    main()