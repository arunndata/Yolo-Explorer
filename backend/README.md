RAG-based code assistant for answering questions about Ultralytics YOLO using FastAPI, MongoDB Atlas, and sentence transformers.

## Quick Start

### 1. Setup
```bash
# Install uv if not already installed
pip install uv

# Clone and setup
git clone <your-repo>
cd yolo-code-assistant
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB URI and OpenRouter API key
```

### 2. Clone YOLO Repository
```bash
git clone https://github.com/ultralytics/ultralytics.git
```

### 3. Index the Codebase
```bash
python scripts/setup_index.py
# Enter path to ultralytics directory when prompted
```

### 4. Create Vector Index in MongoDB Atlas
- Go to MongoDB Atlas → Database → Search Indexes
- Create Search Index → JSON Editor
- Paste:
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    }
  ]
}
```
- Name it: `code_vector_index`

### 5. Run the API
```bash
uvicorn src.main:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

## Example Questions

### Q1: How do I train a YOLOv8 model on a custom dataset?
**Expected retrieval:** Training classes from `engine/trainer.py`, dataset loaders from `data/`

### Q2: What's the difference between YOLOv8n and YOLOv8s?
**Expected retrieval:** Model configuration files, architecture definitions

### Q3: How does Non-Maximum Suppression work?
**Expected retrieval:** NMS implementation from post-processing code

### Q4: How can I export a model to ONNX?
**Expected retrieval:** Export utilities from `engine/exporter.py`

### Q5: What data augmentation is used during training?
**Expected retrieval:** Augmentation pipeline from `data/augment.py`

## Design Decisions

### Code Chunking Strategy
**Approach:** AST-based function/class extraction

**Rationale:**
- Preserves semantic boundaries (complete functions/classes)
- Maintains code context better than fixed-size chunks
- Easier to reference specific functions in answers

**Trade-offs:** Very large functions might exceed context limits (can be handled with overlap)

### Embedding Model Choice
**Model:** `all-MiniLM-L6-v2` (384 dimensions)

**Rationale:**
- Fast inference (~3000 sentences/sec on CPU)
- Small footprint (80MB)
- Good semantic similarity performance
- No GPU required

**Alternative:** CodeBERT for better code-specific understanding (requires more compute)

### LLM Selection
**Model:** `gpt-4o-mini` via OpenRouter

**Rationale:**
- Free tier available
- Strong code comprehension
- 128k context window
- Good instruction following

### Metadata Extracted
For each code chunk:
- `file_path`: Source location
- `name`: Function/class identifier
- `type`: function or class
- `code`: Full source code
- `docstring`: Documentation
- `lineno`: Line number for references
- `embedding`: 384-dim vector

## Future Improvements

### With More Time (Priority Order)

1. **Hybrid Search** (High Priority)
   - Combine vector search with BM25 keyword matching
   - Better recall on specific function names

2. **Code Graph Context** (High Priority)
   - Build import dependency graphs
   - Include caller/callee relationships in context

3. **Re-ranking Layer** (Medium Priority)
   - Use cross-encoder to re-rank top-K results
   - Improves precision significantly

4. **Streaming Responses** (Medium Priority)
   - Stream LLM output for better UX
   - Use FastAPI's StreamingResponse

5. **Conversation History** (Low Priority)
   - Multi-turn conversations
   - Reference previous questions

### Production Scaling

**Critical for Production:**
- **Caching:** Redis for embeddings and common queries
- **Rate Limiting:** Prevent abuse
- **Monitoring:** Prometheus + Grafana for metrics
- **Async Processing:** Better concurrency handling
- **Load Balancing:** Multiple API instances
- **Error Recovery:** Retry logic, circuit breakers
- **Logging:** Structured logging with ELK stack

**Infrastructure:**
- Containerize with Docker
- Deploy on Kubernetes for auto-scaling
- Use managed MongoDB Atlas for reliability
- CDN for static assets

### Missing Features

- **Feedback Loop:** User ratings to improve retrieval
- **Code Execution:** Run and test generated code snippets
- **Version Support:** Index multiple YOLO versions
- **UI Frontend:** Web interface (currently API only)
- **Authentication:** User management and API keys

## API Usage

```python
import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={"question": "How do I train YOLOv8?", "top_k": 5}
)

print(response.json()["answer"])
```

## Project Structure
```
yolo-code-assistant/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   ├── config.py       # Configuration
│   ├── embedder.py     # Sentence transformer wrapper
│   ├── indexer.py      # AST-based code parsing
│   ├── database.py     # MongoDB operations
│   ├── generator.py    # LLM response generation
│   └── main.py         # FastAPI app
└── scripts/
    └── setup_index.py  # One-time indexing script
```

## License
MIT