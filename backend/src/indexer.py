import ast
import os
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

class CodeIndexer:
    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.target_dirs = ["models", "engine", "data"]
    
    def extract_code_chunks(self) -> List[Dict]:
        chunks = []
        for target_dir in self.target_dirs:
            dir_path = self.source_dir / target_dir
            if not dir_path.exists():
                logger.warning(f"Directory not found: {dir_path}. Skipping...")
                continue
            
            logger.info(f"Indexing directory: {dir_path}")
            for py_file in dir_path.rglob("*.py"):
                try:
                    file_chunks = self._parse_file(py_file)
                    chunks.extend(file_chunks)
                except SyntaxError as e:
                    logger.warning(f"Syntax error in {py_file}: {e}. Skipping file.")
                except UnicodeDecodeError as e:
                    logger.warning(f"Encoding error in {py_file}: {e}. Skipping file.")
                except Exception as e:
                    logger.error(f"Unexpected error parsing {py_file}: {e}. Skipping file.")
        
        if not chunks:
            logger.error(f"No code chunks found! Verify that {self.source_dir} contains Python files in {self.target_dirs}")
        else:
            logger.info(f"Successfully extracted {len(chunks)} code chunks")
        
        return chunks
    
    def _parse_file(self, file_path: Path) -> List[Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Could not decode {file_path} with UTF-8. Trying latin-1...")
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    source = f.read()
            except Exception as e:
                raise UnicodeDecodeError(f"Failed to read file with any encoding: {e}")
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise SyntaxError(f"Invalid Python syntax at line {e.lineno}: {e.msg}")
        
        chunks = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                chunk = self._extract_node(node, source, file_path)
                if chunk:
                    chunks.append(chunk)
        
        return chunks
    
    def _extract_node(self, node, source: str, file_path: Path) -> Dict:
        try:
            lines = source.split('\n')
            start = node.lineno - 1
            end = node.end_lineno if hasattr(node, 'end_lineno') else start + 10
            code = '\n'.join(lines[start:end])
            
            docstring = ast.get_docstring(node) or ""
            
            return {
                "file_path": str(file_path.relative_to(self.source_dir)),
                "name": node.name,
                "type": "class" if isinstance(node, ast.ClassDef) else "function",
                "code": code,
                "docstring": docstring,
                "lineno": node.lineno,
                "text_for_embedding": f"{node.name}\n{docstring}\n{code}"
            }
        except Exception as e:
            logger.debug(f"Could not extract node {getattr(node, 'name', 'unknown')} from {file_path}: {e}")
            return None