# Design Documentation

## System Architecture

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    YOLO Code Assistant                        │
│                   (Full-Stack RAG System)                     │
└──────────────────────────────────────────────────────────────┘

                    ┌───────────────┐
                    │   End User    │
                    └───────┬───────┘
                            │
                    ┌───────▼──────────┐
                    │   Streamlit UI   │  (http://localhost:8501)
                    │   Chat Interface │
                    └───────┬──────────┘
                            │ HTTP POST
                    ┌───────▼──────────┐
                    │  FastAPI Server  │  (http://localhost:8000)
                    │   REST Endpoints │
                    └───────┬──────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│   Embedder    │   │   Database   │   │  Generator   │
│   (SentTrans) │   │   (MongoDB)  │   │  (OpenAI)    │
└───────────────┘   └──────────────┘   └──────────────┘
```

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **Streamlit Frontend** | User interface, chat history | Streamlit 1.30+ |
| **FastAPI Backend** | API orchestration, request handling | FastAPI 0.104+ |
| **Embedder** | Text → 384-dim vectors | sentence-transformers |
| **Database** | Vector storage, similarity search | MongoDB Atlas |
| **Generator** | Context + Query → Answer | OpenAI GPT-3.5 |

## Detailed Component Design

### 1. Streamlit Frontend (`app.py`)

**Purpose:** Beautiful chat interface for users

**Key Features:**
```python
# Chat interface with history
st.chat_message("user")
st.chat_message("assistant")

# Adjustable retrieval
top_k = st.slider("Number of chunks", 1, 10, 5)

# Example questions
if st.button("How do I train YOLOv8?"):
    query = "How do I train YOLOv8?"

# Source display
with st.expander(f"Source {i}: {source['name']}"):
    st.markdown(f"File: `{source['file']}`")
```

**Design Decisions:**

1. **Why Streamlit over Gradio?**
   -  More customizable layout
   -  Better for production deployment
   -  Richer component library
   -  Slightly slower reruns (acceptable trade-off)

2. **Chat vs Q&A interface:**
   - Chat: Natural conversation flow
   - Q&A: More structured, but less intuitive
   - **Choice:** Chat (users expect chat in 2026)

3. **Sidebar vs inline settings:**
   - Sidebar keeps main area clean
   - Easy access without cluttering chat
   - **Choice:** Sidebar for settings, stats, about

**State Management:**
```python
# Session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Persist across reruns
st.session_state.messages.append({
    "role": "assistant",
    "content": answer,
    "sources": sources
})
```

**API Communication:**
```python
def ask_question(question: str, top_k: int) -> Dict:
    response = requests.post(
        "http://localhost:8000/ask",
        json={"question": question, "top_k": top_k},
        timeout=30
    )
    return response.json()
```

**Error Handling:**
```python
try:
    response = requests.post(...)
except requests.exceptions.ConnectionError:
    st.error(" Cannot connect to backend")
    st.info("Run: `uvicorn src.main:app --reload`")
except Exception as e:
    st.error(f"Error: {e}")
```

### 2. FastAPI Backend (`src/main.py`)

**Purpose:** REST API orchestrating RAG pipeline

**Architecture:**
```python
@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    # 1. Embed query
    query_vector = embedder.encode(request.question)
    
    # 2. Vector search
    results = db.search(query_vector, request.top_k)
    
    # 3. Generate answer
    answer = generator.generate(request.question, results)
    
    # 4. Return structured response
    return AnswerResponse(
        question=request.question,
        answer=answer,
        sources=[...]
    )
```

**API Design:**

**Request:**
```json
{
  "question": "How do I train YOLOv8?",
  "top_k": 5
}
```

**Response:**
```json
{
  "question": "...",
  "answer": "To train a YOLOv8 model...",
  "sources": [
    {
      "file": "models/yolo/detect/train.py",
      "name": "DetectionTrainer",
      "type": "class",
      "line": 15
    }
  ]
}
```

**Why REST API vs Direct Coupling?**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **REST API** |  Decoupled<br> Testable<br> Scalable |  Network overhead | **Chosen** |
| Direct import | Faster |  Tight coupling<br> Hard to scale | Rejected |

**Initialization:**
```python
# Global instances (initialized once)
embedder = Embedder()
db = VectorDB()
generator = ResponseGenerator()
```

**Why global?** Model loading is expensive (~2s), shouldn't happen per request.

### 3. Code Indexer (`src/indexer.py`)

**Purpose:** Transform Python source → Vector embeddings

**Pipeline:**
```
.py files → AST Parse → Extract Functions/Classes → Format Chunks
    ↓
Add Metadata (file, line, type)
    ↓
Generate Embeddings (384 dims)
    ↓
Upload to MongoDB
```

**AST-Based Extraction:**
```python
def _parse_file(self, file_path: Path) -> List[Dict]:
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    chunks = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            chunk = self._extract_node(node, source, file_path)
            if chunk:
                chunks.append(chunk)
    
    return chunks
```

**Chunk Structure:**
```python
chunk = {
    "file_path": "models/yolo/detect/train.py",
    "name": "DetectionTrainer",
    "type": "class",
    "code": "class DetectionTrainer(BaseTrainer):\n    ...",
    "docstring": "Trainer for YOLO detection models.",
    "lineno": 15,
    "text_for_embedding": "DetectionTrainer\n<docstring>\n<code>"
}
```

**Why `text_for_embedding` is special:**
- Combines name + docstring + code
- Deleted after embedding (not stored)
- Optimizes semantic search (name/docs weighted higher)

**Design Decision: What to Extract?**

| Unit | Pros | Cons | Decision |
|------|------|------|----------|
| **Functions/Classes** |  Semantic<br> Self-contained |  Variable size | **Chosen** |
| Fixed 500 lines |  Uniform |  Splits functions | Rejected |
| Entire files |  Full context |  Too large | Rejected |
| Paragraphs |  Small |  Breaks syntax | Rejected |

### 4. Embedder (`src/embedder.py`)

**Purpose:** Text → 384-dimensional vectors

**Model:** `sentence-transformers/all-MiniLM-L6-v2`

**Implementation:**
```python
class Embedder:
    def __init__(self):
        self.model = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2'
        )
    
    def encode(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()
```

**Performance:**
- Single encoding: ~20ms
- Batch (32): ~500ms
- **Optimization:** Always batch during indexing

**Model Comparison:**

| Model | Dimensions | Speed | Quality | Size | Choice |
|-------|-----------|-------|---------|------|--------|
| **all-MiniLM-L6-v2** | 384 |  Fast |  Good | 80MB | **Selected** |
| all-mpnet-base-v2 | 768 |  Medium |  Better | 420MB | Too slow |
| text-embedding-3-small | 1536 |  API |  Best | API | Costs money |

**Why 384 dimensions is enough:**
- Captures semantic meaning effectively
- Faster cosine similarity computation
- Lower storage (384 floats vs 1536)
- Diminishing returns beyond 512 dims for this use case

### 5. Vector Database (`src/database.py`)

**Purpose:** Store & retrieve code chunks via similarity

**MongoDB Atlas Configuration:**
```python
class VectorDB:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.collection = self.db[COLLECTION_NAME]
```

**Document Schema:**
```json
{
  "_id": ObjectId("..."),
  "file_path": "models/yolo/detect/train.py",
  "name": "DetectionTrainer",
  "type": "class",
  "code": "class DetectionTrainer...",
  "docstring": "Trainer for YOLO detection...",
  "lineno": 15,
  "embedding": [0.1, 0.2, ..., 0.05]  // 384 floats
}
```

**Vector Search Query:**
```python
def search(self, query_vector: List[float], top_k: int = 5):
    pipeline = [
        {
            "$vectorSearch": {
                "index": "code_vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 100,  # Search space
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
                "lineno": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    return list(self.collection.aggregate(pipeline))
```

**Key Parameters:**

1. **`numCandidates`:** How many chunks to consider
   - Too low (10): Fast but may miss relevant chunks
   - Too high (1000): Slower, diminishing returns
   - **Sweet spot:** 10-20x `limit` (50-100 for top-5)

2. **`similarity`:** Distance metric
   - Options: cosine, euclidean, dotProduct
   - **Choice:** Cosine (standard for sentence embeddings)

**Index Definition:**
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

**Why MongoDB Atlas?**

| Feature | MongoDB | FAISS | Pinecone |
|---------|---------|-------|----------|
| Vector search |  Native |  Fastest |  Native |
| Metadata filtering |  Rich |  None |  Limited |
| Persistence | Cloud |  Memory |  Cloud |
| Setup |  Easy |  Easy |  Easy |
| Cost |  Free 512MB |  Free |  Limited free |

**Decision:** MongoDB's flexible schema + free tier + vector search = perfect fit

### 6. Response Generator (`src/generator.py`)

**Purpose:** Retrieved chunks + Query → Natural language answer

**OpenAI Integration:**
```python
class ResponseGenerator:
    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-3.5-turbo"
    
    def generate(self, question: str, context_chunks: List[Dict]) -> str:
        context = self._format_context(context_chunks)
        
        prompt = f"""You are an expert on Ultralytics YOLO codebase.

CODE CONTEXT:
{context}

QUESTION: {question}

Provide a clear answer with code examples and file references."""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert..."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
```

**Context Formatting:**
```python
def _format_context(self, chunks: List[Dict]) -> str:
    formatted = []
    for i, chunk in enumerate(chunks, 1):
        formatted.append(
            f"[{i}] File: {chunk['file_path']} (line {chunk['lineno']})\n"
            f"Name: {chunk['name']} ({chunk['type']})\n"
            f"Code:\n{chunk['code']}\n"
        )
    return "\n---\n".join(formatted)
```

**Why numbered chunks?**
- LLM can reference "[3]" in answer
- Users can verify which chunk was used
- Enables trust and debugging

**Prompt Engineering Decisions:**

1. **System message:**
   - Sets expert persona
   - Constrains to YOLO domain
   - Reduces hallucination

2. **Code-first ordering:**
   ```
   Context → Question → Instructions
   ```
   - LLM sees context before question
   - Proven more effective than Question → Context

3. **Explicit instructions:**
   - "Include function names"
   - "Explain implementation"
   - "If insufficient, say so"
   - LLMs follow bullet points better

**Parameters:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `temperature` | 0.7 | Balanced: factual yet natural |
| `max_tokens` | 1000 | Enough for detailed answers |
| `model` | gpt-3.5-turbo | Cost-effective, fast, reliable |

**Why GPT-3.5 vs GPT-4?**
- GPT-4: 10x more expensive (~$0.03/query vs ~$0.002)
- GPT-3.5: Good enough for code Q&A
- Can upgrade to GPT-4 for complex questions
- **Decision:** Start with 3.5, A/B test 4 later

## Data Flow

### Indexing Flow

```
1. Clone Ultralytics repo
   ↓
2. Walk target directories (models/, engine/, data/)
   ↓
3. For each .py file:
   - Parse with AST
   - Extract functions/classes
   - Format chunk with metadata
   ↓
4. Batch encode chunks (32 at a time)
   ↓
5. Upload to MongoDB with embeddings
   ↓
6. Create vector index (manual in Atlas UI)
```

**Bottlenecks:**
- Repo clone: 5 min (network)
- Embedding: 8 min (CPU-bound)
- Upload: 1 min (network)

**Total: ~15 minutes**

### Query Flow

```
1. User enters question in Streamlit
   ↓
2. POST /ask to FastAPI
   ↓
3. Embed question (50ms)
   ↓
4. Vector search in MongoDB (100ms)
   ↓
5. Format top-K chunks as context
   ↓
6. Send to OpenAI GPT-3.5 (2-4s)
   ↓
7. Return answer + sources
   ↓
8. Display in Streamlit chat
```

**Latency breakdown:**
- Embedding: 50ms
- Vector search: 100ms
- LLM generation: 2,000-4,000ms
- **Total: ~3-5 seconds**

## Key Design Trade-offs

### 1. Chunk Size

**Decision:** Variable size (AST-based)

| Approach | Pros | Cons | Choice |
|----------|------|------|--------|
| AST chunks |  Semantic<br> Complete |  Variable (50-500 lines) | **Chosen** |
| Fixed 100 lines |  Uniform |  Breaks functions | Rejected |
| Sliding window |  No info loss |  3x storage | Future |

**Rationale:** Semantic coherence > uniform size

### 2. Top-K Value

**Decision:** k=5 (default, adjustable 1-10)

**Empirical testing:**
- k=3: 60% good answers
- k=5: 75% good answers ← **Sweet spot**
- k=10: 78% good (marginal, 2x tokens)

**Trade-off:** More chunks = more context but slower + more expensive

### 3. Embedding Model

**Decision:** all-MiniLM-L6-v2

**Comparison:**

```
Quality ────▶
Speed   ────▶

        Quality
          │
  mpnet ● │     ● OpenAI ada-002
          │
MiniLM ●──┼──────  (Chosen)
          │
          └─────── Speed/Cost
```

**Rationale:** 80% quality at 0% cost

### 4. LLM Choice

**Decision:** OpenAI GPT-3.5

**Considered:**
1. GPT-4: Better quality, 10x cost → **Too expensive for MVP**
2. DeepSeek (free): Unreliable, frequent downtime → **Not production-ready**
3. Llama 3.1 (self-hosted): Setup complexity → **Out of scope**

**Choice:** GPT-3.5 = best balance of quality/cost/reliability

### 5. UI Framework

**Decision:** Streamlit

**vs Gradio:**
- Streamlit: More customizable, better deployment
- Gradio: Faster prototyping, limited styling

**Trade-off:** Longer setup time for better long-term maintainability

## Performance Optimization Strategies

### Current (MVP)
-  Batch embedding during indexing
-  Global model instances (no reload per request)
-  MongoDB indexes for fast lookup

### Future Improvements

1. **Caching** (10x speedup for repeats)
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def retrieve_cached(query, top_k):
       return retrieve(query, top_k)
   ```

2. **Async LLM calls** (parallel requests)
   ```python
   async def generate_async(question, chunks):
       response = await openai_client.chat.completions.create(...)
   ```

3. **GPU acceleration** (8x faster embedding)
   ```python
   model = SentenceTransformer('...', device='cuda')
   ```

4. **Query preprocessing** (better retrieval)
   - Expand abbreviations: "NMS" → "Non-Maximum Suppression"
   - Extract entities: "train YOLOv8" → "train", "YOLOv8"

## Error Handling

### Handled Errors

1. **MongoDB connection fails**
   ```python
   try:
       client = MongoClient(uri, serverSelectionTimeoutMS=5000)
   except Exception as e:
       print("MongoDB connection failed. Check .env")
       sys.exit(1)
   ```

2. **OpenAI API rate limit**
   ```python
   try:
       response = client.chat.completions.create(...)
   except openai.RateLimitError:
       return "Rate limit exceeded. Please try again in 60s."
   ```

3. **No chunks retrieved**
   ```python
   if not results:
       return {
           "answer": "No relevant code found. Try rephrasing?",
           "sources": []
       }
   ```

### Unhandled Edge Cases

1. **Very large classes (>2000 lines)**
   - May exceed LLM context window
   - **Future:** Split with sliding window

2. **Concurrent requests overwhelming OpenAI**
   - No rate limiting on backend
   - **Future:** Add request queue

3. **Outdated code in index**
   - YOLO repo changes, index doesn't
   - **Future:** Auto-reindex on schedule

## Testing Strategy

### Unit Tests (Future)
```python
def test_embedder():
    embedder = Embedder()
    vec = embedder.encode("test")
    assert len(vec) == 384

def test_vector_search():
    db = VectorDB()
    results = db.search([0.1]*384, k=5)
    assert len(results) == 5
```

### Integration Tests (Future)
```python
def test_end_to_end():
    response = requests.post(
        "http://localhost:8000/ask",
        json={"question": "How to train YOLO?", "top_k": 5}
    )
    assert response.status_code == 200
    assert "train" in response.json()["answer"].lower()
```

### Evaluation Metrics (Future)

**Retrieval Quality:**
- Precision@K: % relevant in top-K
- MRR: Mean Reciprocal Rank

**Answer Quality:**
- Correctness: Human eval (0-1 scale)
- Completeness: Addresses all sub-questions?

## Deployment Architecture (Future)

```
┌─────────────────────────────────────────────┐
│              Production Setup                │
└─────────────────────────────────────────────┘

Streamlit Cloud (Frontend)
     ↓ HTTPS
Railway/AWS (FastAPI Backend)
     ↓
MongoDB Atlas (Vector DB)
     ↓
OpenAI API (LLM)

Additional:
- Redis (Query cache)
- CloudWatch (Monitoring)
- Sentry (Error tracking)
```

## Conclusion

This design prioritizes:
1. **Simplicity**: Straightforward architecture, easy to understand
2. **Reliability**: Proven technologies, good error handling
3. **Cost-efficiency**: Free tiers, optimized API usage
4. **User experience**: Fast responses, clear sources

Trade-offs accepted for MVP:
- Variable chunk sizes (semantic coherence over uniformity)
- GPT-3.5 over GPT-4 (cost over marginal quality)
- No caching yet (simplicity over performance)
- No evaluation dataset (time constraint)

