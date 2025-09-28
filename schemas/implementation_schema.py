IMPLEMENTATION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "action": {"type": "string", "enum": ["create", "update", "delete"]},
            "content": {"type": "string"}
        },
        "required": ["file_path", "action", "content"]
    }
}