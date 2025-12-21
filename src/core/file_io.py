"""File I/O utilities for reading novels and writing JSONL files."""

import json
from typing import List, Dict, Any
from pathlib import Path


class FileIO:
    """Utilities for file input/output operations."""
    
    @staticmethod
    def read_novel(file_path: str) -> str:
        """Read novel text from file.
        
        Args:
            file_path: Path to novel text file.
            
        Returns:
            Novel text as string.
            
        Raises:
            FileNotFoundError: If file doesn't exist.
            IOError: If file cannot be read.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Novel file not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Failed to read novel file: {e}")
    
    @staticmethod
    def write_jsonl(file_path: str, data: List[Dict[str, Any]], 
                   metadata: Dict[str, Any] = None) -> None:
        """Write data to JSONL file with optional metadata.
        
        Args:
            file_path: Output file path.
            data: List of dictionaries to write.
            metadata: Optional metadata to include as first line.
            
        Raises:
            IOError: If file cannot be written.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                # Write metadata as first line if provided
                if metadata:
                    f.write(json.dumps({"metadata": metadata}) + '\n')
                
                # Write each data item as a JSON line
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        except Exception as e:
            raise IOError(f"Failed to write JSONL file: {e}")
    
    @staticmethod
    def read_jsonl(file_path: str) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Read data from JSONL file.
        
        Args:
            file_path: Input file path.
            
        Returns:
            Tuple of (metadata, data_list). Metadata is empty dict if not present.
            
        Raises:
            FileNotFoundError: If file doesn't exist.
            IOError: If file cannot be read.
            json.JSONDecodeError: If file contains invalid JSON.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"JSONL file not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                return {}, []
            
            # Check if first line is metadata
            first_line = json.loads(lines[0])
            if "metadata" in first_line:
                metadata = first_line["metadata"]
                data_lines = lines[1:]
            else:
                metadata = {}
                data_lines = lines
            
            # Parse data lines
            data = [json.loads(line) for line in data_lines if line.strip()]
            
            return metadata, data
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in file: {e}", e.doc, e.pos)
        except Exception as e:
            raise IOError(f"Failed to read JSONL file: {e}")
    
    @staticmethod
    def ensure_directory(dir_path: str) -> None:
        """Ensure directory exists, create if it doesn't.
        
        Args:
            dir_path: Directory path to ensure.
        """
        Path(dir_path).mkdir(parents=True, exist_ok=True)
