import requests
import os
import logging
from typing import List, Dict
from src.config import OPENROUTER_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

class ResponseGenerator:
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.model = LLM_MODEL
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        # self.last_prompt_path = "last_prompt.txt"  # Uncomment for debugging
    
    def generate(self, question: str, context_chunks: List[Dict]) -> str:
        context = self._format_context(context_chunks)
        
        prompt = f"""You are an expert assistant for the Ultralytics YOLO codebase. Your role is to help developers understand and use YOLO by analyzing source code.

INSTRUCTIONS:
1. Answer ONLY using the provided code context below
2. Provide working code examples when applicableAlso cite specific files and line numbers when referencing code
3. If the context doesn't fully answer the question, say so explicitly
4. For standard YOLO questions, prefer basic implementations over specialized variants

CODE CONTEXT:
{context}

QUESTION: {question}

RESPONSE FORMAT:
- Start with a direct answer in few sentences
- Provide a minimal working example if applicable
- Explain implementation details with code references
- Note any caveats or limitations"""
        
        logger.debug("="*80)
        logger.debug("RESPONSE GENERATION")
        logger.debug("="*80)
        
        logger.debug(f"QUESTION: {question}")
        
        logger.debug("RETRIEVED CODE CHUNKS:")
        for i, chunk in enumerate(context_chunks, 1):
            logger.debug(f"[{i}] {chunk['name']} ({chunk['type']}) - {chunk['file_path']}:{chunk['lineno']}")
        
        # Save prompt to file (Commented out - uncomment if needed for testing)
        # try:
        #     with open(self.last_prompt_path, "w", encoding="utf-8") as f:
        #         f.write(prompt)
        #     logger.debug(f"Full prompt saved to: {os.path.abspath(self.last_prompt_path)}")
        # except Exception as e:
        #     logger.warning(f"Could not save prompt to file: {e}")
        
        logger.info("Calling OpenRouter API...")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "YOLO Code Assistant",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.6,
            "max_tokens": 1000
        }
        
        try:
            if not self.api_key or self.api_key == "None":
                raise ValueError("OPENROUTER_API_KEY not found in .env file!")
            
            logger.debug(f"Using API Key: {self.api_key[:20]}...")
            logger.info(f"Model: {self.model}")
            
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            logger.debug(f"Response Status: {response.status_code}")
            logger.debug(f"Response Headers: {dict(response.headers)}")
            logger.debug(f"Raw Response: {response.text[:500]}...")
            
            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"API returned {response.status_code}: {error_detail}")
            
            data = response.json()
            
            if not data:
                raise ValueError("Empty response from API")
            
            if "choices" not in data:
                raise ValueError(f"No 'choices' in response. Got: {data}")
            
            if not data["choices"]:
                raise ValueError("Empty 'choices' array in response")
            
            if "message" not in data["choices"][0]:
                raise ValueError(f"No 'message' in choice. Got: {data['choices'][0]}")
            
            if "content" not in data["choices"][0]["message"]:
                raise ValueError(f"No 'content' in message. Got: {data['choices'][0]['message']}")
            
            answer = data["choices"][0]["message"]["content"]
            
            logger.info("LLM response received successfully")
            logger.debug(f"Response preview: {answer[:200]}...")
            
            if 'usage' in data:
                logger.info(f"Token usage - Prompt: {data['usage'].get('prompt_tokens', 'N/A')}, "
                          f"Completion: {data['usage'].get('completion_tokens', 'N/A')}, "
                          f"Total: {data['usage'].get('total_tokens', 'N/A')}")
            
            return answer
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    #  (Commented out - uncomment if needed for testing)
    # def get_last_prompt(self) -> str:
    #     """
    #     Retrieve the content of the last prompt sent to LLM.
    #     
    #     Returns:
    #         str: Content of last_prompt.txt or error message
    #     """
    #     try:
    #         if os.path.exists(self.last_prompt_path):
    #             with open(self.last_prompt_path, "r", encoding="utf-8") as f:
    #                 content = f.read()
    #             logger.debug(f"Retrieved last prompt from: {os.path.abspath(self.last_prompt_path)}")
    #             return content
    #         else:
    #             error_msg = "No prompt file found. Generate a response first."
    #             logger.warning(error_msg)
    #             return error_msg
    #     except Exception as e:
    #         error_msg = f"Error reading prompt file: {str(e)}"
    #         logger.error(error_msg)
    #         return error_msg
    
    # def get_last_prompt_path(self) -> str:
    #     """
    #     Get the absolute path to the last_prompt.txt file.
    #     
    #     Returns:
    #         str: Absolute path to last_prompt.txt
    #     """
    #     return os.path.abspath(self.last_prompt_path)
    
    def _format_context(self, chunks: List[Dict]) -> str:
        formatted = []
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            docstring_line = chunk.get('docstring', '')
            purpose = docstring_line.split('\n')[0] if docstring_line else "No description"
            
            formatted.append(
                f"=== CODE CHUNK [{i}/{total_chunks}] ===\n"
                f"File: {chunk['file_path']}\n"
                f"Function/Class: {chunk['name']} ({chunk['type']})\n"
                f"Lines: {chunk['lineno']}\n"
                f"Purpose: {purpose}\n"
                f"---\n"
                f"{chunk['code']}\n"
                f"{'='*30}"
            )
        return "\n\n".join(formatted)
    
    def clear_cache(self):
        """Clear any cached responses (placeholder for future caching)"""
        logger.info("Cache cleared (no caching implemented yet)")
        pass