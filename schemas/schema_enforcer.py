# schema_enforcer.py
from functools import wraps
from utils.validation_utils import validate_plan, validate_orchestration, validate_implementation

def enforce_schema(schema_type):
    """
    Decorator to enforce schema validation on method outputs
    
    Args:
        schema_type: Type of schema to enforce ('plan', 'orchestration', 'implementation')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Validate based on schema type
            if schema_type == 'plan':
                validate_plan(result)
            elif schema_type == 'orchestration':
                validate_orchestration(result)
            elif schema_type == 'implementation':
                validate_implementation(result)
                
            return result
        return wrapper
    return decorator
