# tools/utils/validation_utils.py
"""
Validation utilities for tools
"""

import json
import logging
from typing import Dict, Any

from schemas.implementation_schema import IMPLEMENTATION_SCHEMA

logger = logging.getLogger(__name__)

class SchemaValidatorTool:
    """Schema validation utility for tool outputs"""
    
    def _run(self, json_string: str, schema_type: str) -> bool:
        """
        Validate JSON against a schema type
        
        Args:
            json_string: JSON string to validate
            schema_type: Type of schema to validate against
            
        Returns:
            bool: True if validation passes
        """
        try:
            data = json.loads(json_string)
            
            if schema_type == 'plan':
                return self._validate_plan_schema(data)
            elif schema_type == 'implementation':
                return self._validate_implementation_schema(data)
            else:
                logger.warning(f"Unknown schema type: {schema_type}")
                return True  # Default to passing for unknown types
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def _validate_plan_schema(self, data: dict) -> bool:
        """Validate project plan schema"""
        required_keys = ['tasks', 'files']
        if not all(key in data for key in required_keys):
            return False
        
        # Validate tasks structure
        if not isinstance(data['tasks'], list):
            return False
        
        for task in data['tasks']:
            if not isinstance(task, dict) or 'task' not in task:
                return False
        
        # Validate files structure  
        if not isinstance(data['files'], list):
            return False
            
        for file_item in data['files']:
            if not isinstance(file_item, dict) or 'file_path' not in file_item:
                return False
        
        return True
    
    def _validate_implementation_schema(self, data: list) -> bool:
        """Validate implementation schema"""
        if not isinstance(data, list):
            return False
        
        for item in data:
            if not isinstance(item, dict):
                return False
            if "file_path" not in item or not isinstance(item["file_path"], str):
                return False
            if "action" not in item or item["action"] not in ["create", "update", "delete"]:
                return False
            if "content" not in item or not isinstance(item["content"], str):
                return False
                
        return True