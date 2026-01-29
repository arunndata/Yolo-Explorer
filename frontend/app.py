# File: app.py

import streamlit as st
import requests
from typing import List, Dict, Optional

# Page configuration
st.set_page_config(
    page_title="YOLO Code Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748b;
        margin-bottom: 2rem;
    }
    .source-card {
        background: #f8fafc;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    .code-block {
        background: #1e293b;
        color: #e2e8f0;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .example-question {
        background: #f1f5f9;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        cursor: pointer;
        border: 2px solid transparent;
        transition: all 0.3s;
    }
    .example-question:hover {
        border-color: #667eea;
        background: #e0e7ff;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
API_URL = "http://localhost:8000"

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_stats() -> Optional[Dict]:
    """Fetch system stats from backend"""
    try:
        response = requests.get(f"{API_URL}/stats", timeout=5)
        response.raise_for_status()
        return response.json()
    except:
        return None

def ask_question(question: str, top_k: int = 5) -> Dict:
    """Send question to FastAPI backend"""
    try:
        response = requests.post(
            f"{API_URL}/ask",
            json={"question": question, "top_k": top_k},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend API. Make sure the server is running on http://localhost:8000")
        st.info("Run: `uvicorn src.main:app --reload`")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def display_sources(sources: List[Dict]):
    """Display source code references"""
    st.markdown("### 📚 Source References")
    
    for i, source in enumerate(sources, 1):
        with st.expander(f"**{i}. {source['name']}** ({source['type']})"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"📁 **File:** `{source['file']}`")
            with col2:
                st.markdown(f"📍 **Line:** {source['line']}")

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    top_k = st.slider(
        "Number of code chunks to retrieve",
        min_value=1,
        max_value=10,
        value=5,
        help="More chunks = more context but slower"
    )
    
    st.markdown("---")
    
    st.markdown("## 📊 Stats")
    
    # Fetch dynamic stats
    stats = get_stats()
    
    if stats:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Indexed Chunks", 
                f"{stats.get('total_chunks', 0):,}"
            )
        with col2:
            model_name = stats.get('model', 'Unknown')
            # Shorten model name if too long
            display_name = model_name.split('/')[-1] if '/' in model_name else model_name
            if len(display_name) > 15:
                display_name = display_name[:12] + "..."
            st.metric("Model", display_name)
        
        # Additional stats in expandable section
        with st.expander("📈 More Stats"):
            st.markdown(f"**Embedding Model:** `{stats.get('embedding_model', 'N/A')}`")
            st.markdown(f"**Database:** `{stats.get('database', 'MongoDB Atlas')}`")
            st.markdown(f"**Collection:** `{stats.get('collection', 'code_chunks')}`")
            if 'last_indexed' in stats:
                st.markdown(f"**Last Indexed:** {stats.get('last_indexed', 'N/A')}")
    else:
        # Fallback to placeholders if API is down
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Indexed Chunks", "---")
        with col2:
            st.metric("Model", "---")
        st.warning("⚠️ Could not fetch stats from backend")
    
    st.markdown("---")
    
    st.markdown("## ℹ️ About")
    
    # 🔧 FIX: Check if stats exists before using .get()
    if stats:
        total_chunks_display = f"{stats.get('total_chunks', 1156):,}"
        model_display = stats.get('model', 'OpenRouter LLM')
    else:
        total_chunks_display = "1,156"
        model_display = "OpenRouter LLM"
    
    st.markdown(f"""
    This assistant helps you understand the **Ultralytics YOLO** codebase by:
    
    - 🔍 Searching through {total_chunks_display} code chunks
    - 🧠 Using semantic vector search
    - 💬 Generating contextual answers with LLM
    
    **Tech Stack:**
    - FastAPI
    - MongoDB Atlas
    - {model_display}
    - Sentence Transformers
    """)
    
    st.markdown("---")
    
    if st.button("🔄 Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Main content
st.markdown('<h1 class="main-header">🤖 YOLO Code Assistant</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Your AI-powered guide to the Ultralytics YOLO codebase</p>', unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Example questions
st.markdown("### 💡 Example Questions")

example_questions = [
    "How do I train a YOLOv8 model on a custom dataset?",
    "What data augmentation techniques are used during training?",
    "How does Non-Maximum Suppression work in YOLO?",
    "How can I export a YOLO model to ONNX format?",
    "What's the difference between YOLOv8n and YOLOv8s models?",
]

cols = st.columns(2)
for i, question in enumerate(example_questions):
    with cols[i % 2]:
        if st.button(question, key=f"example_{i}", use_container_width=True):
            st.session_state.user_question = question

st.markdown("---")

# Chat interface
st.markdown("### 💬 Ask Your Question")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message:
            display_sources(message["sources"])

# User input
if prompt := st.chat_input("Ask about YOLO code..."):
    st.session_state.user_question = prompt

# Handle question from button or input
if "user_question" in st.session_state and st.session_state.user_question:
    question = st.session_state.user_question
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    
    # Get response from API
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching codebase..."):
            response = ask_question(question, top_k)
        
        if response:
            # Display answer
            st.markdown(response["answer"])
            
            # Display sources
            display_sources(response["sources"])
            
            # Add assistant message to chat
            st.session_state.messages.append({
                "role": "assistant",
                "content": response["answer"],
                "sources": response["sources"]
            })
    
    # Clear the question
    del st.session_state.user_question

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #64748b; padding: 2rem;'>
    <p>Built with ❤️ using FastAPI, Streamlit, MongoDB Atlas & OpenRouter</p>
    <p>🔗 <a href='http://localhost:8000/docs' target='_blank'>API Documentation</a></p>
</div>
""", unsafe_allow_html=True)