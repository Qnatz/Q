import json
import re
from typing import Optional, Any

def safe_json_loads(s: str) -> Optional[Any]:
    """Safely parse a JSON string, returning None if parsing fails."""
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None

def validate_json(data: Any, schema: dict) -> bool:
    """Validate data against a JSON schema."""
    try:
        from jsonschema import validate
        validate(instance=data, schema=schema)
        return True
    except ImportError:
        print("Warning: jsonschema is not installed. Skipping validation.")
        return True
    except Exception:
        return False

def safe_json_extract(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'\{(?:.|\s)*?\}', text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None