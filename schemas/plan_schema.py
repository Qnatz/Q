PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["name", "description"],
        },
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "purpose": {"type": "string"},
                },
                "required": ["path", "purpose"],
            },
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "description": {"type": "string"},
                    "module": {
                        "type": "string",
                        "enum": [
                            "ProgrammingModule",
                            "QAModule",
                            "ReviewModule",
                            "ManagementModule",
                            "PlanningModule"
                        ]
                    },
                    "output": {
                        "type": "string",
                        "description": "Expected output file or artifact"
                    }
                },
                "required": ["task", "description", "module", "output"],
            },
        },
    },
    "required": ["project", "files", "tasks"],
}
