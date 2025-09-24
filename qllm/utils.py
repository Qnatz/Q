"""Small utilities used across backends."""

import json
from typing import Any


def json_dumps_safe(obj: Any, **kwargs) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, **kwargs)
    except Exception:
        # Fallback to a readable representation
        try:
            return str(obj)
        except Exception:
            return "<unserializable>"
