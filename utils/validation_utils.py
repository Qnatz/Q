# validation_utils.py
import json
import jsonschema
from jsonschema import validate
from typing import Dict, Any
from crewai.tools import BaseTool
# Import the schemas
from schemas.plan_schema import PLAN_SCHEMA
from schemas.orchestration_schema import ORCHESTRATION_SCHEMA
from schemas.implementation_schema import IMPLEMENTATION_SCHEMA

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_json(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Validate JSON data against a schema
    
    Args:
        data: The JSON data to validate
        schema: The JSON schema to validate against
        
    Returns:
        bool: True if valid, raises ValidationError if not
    """
    try:
        validate(instance=data, schema=schema)
        return True
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Validation failed: {e.message}")

def validate_plan(data: Dict[str, Any]) -> bool:
    """Validate against PLAN_SCHEMA"""
    return validate_json(data, PLAN_SCHEMA)

def validate_orchestration(data: Dict[str, Any]) -> bool:
    """Validate against ORCHESTRATION_SCHEMA"""
    return validate_json(data, ORCHESTRATION_SCHEMA)

def validate_implementation(data: Dict[str, Any]) -> bool:
    """Validate against IMPLEMENTATION_SCHEMA"""
    return validate_json(data, IMPLEMENTATION_SCHEMA)

class SchemaValidatorTool(BaseTool):
    name: str = "Schema Validator"
    description: str = "Validates JSON data against predefined schemas"
    
    def _run(self, json_data: str, schema_type: str) -> str:
        """
        Validate JSON data against a specific schema
        
        Args:
            json_data: JSON string to validate
            schema_type: Type of schema to use ('plan', 'orchestration', 'implementation')
            
        Returns:
            str: Validation result message
        """
        try:
            data = json.loads(json_data)
            
            if schema_type == 'plan':
                validate_plan(data)
                return "✅ Plan validation successful"
            elif schema_type == 'orchestration':
                validate_orchestration(data)
                return "✅ Orchestration validation successful"
            elif schema_type == 'implementation':
                validate_implementation(data)
                return "✅ Implementation validation successful"
            else:
                return f"❌ Unknown schema type: {schema_type}"
                
        except ValidationError as e:
            return f"❌ Validation failed: {str(e)}"
        except json.JSONDecodeError:
            return "❌ Invalid JSON format"
