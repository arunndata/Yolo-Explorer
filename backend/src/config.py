import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the backend directory (where .env should be)
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'

# Load .env file
load_dotenv(dotenv_path=env_path)

# Enable debug logging if DEBUG env var is set
if os.getenv("DEBUG", "false").lower() == "true":
    logging.getLogger().setLevel(logging.DEBUG)
    logger.debug(f"Looking for .env at: {env_path}")
    logger.debug(f".env exists: {env_path.exists()}")

# Load environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME", "yolo_assistant")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "code_chunks")

# Log loaded values (partial for security)
if os.getenv("DEBUG", "false").lower() == "true":
    logger.debug(f"MONGODB_URI loaded: {MONGODB_URI[:30] if MONGODB_URI else 'NOT FOUND'}...")
    logger.debug(f"OPENROUTER_API_KEY loaded: {OPENROUTER_API_KEY[:20] if OPENROUTER_API_KEY else 'NOT FOUND'}...")

# Embedding and LLM config
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = os.getenv("LLM_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))

# Validate required variables
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found! Check your .env file.")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found! Check your .env file.")

logger.info(f"Configuration loaded: Model={LLM_MODEL}, Database={DATABASE_NAME}")