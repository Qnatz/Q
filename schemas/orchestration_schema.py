import dataclasses
from typing import List, Optional

@dataclasses.dataclass
class Task:
    description: str
    notes: List[str] = dataclasses.field(default_factory=list)

    def add_note(self, note: str):
        self.notes.append(note)

@dataclasses.dataclass
class ProgrammingTaskParams:
    task: str
    context: str
    conversation_history: str
    plan: str
    project_state: dict
    step_already_performed: bool
    skip_until_step: Optional[str]
    repo_path: str
    task_id: str
    message_callback: callable
    is_last_step: bool
    skip_tests: bool
    skip_build: bool
    test_command: Optional[str]
    build_command: Optional[str]
    focus_file: Optional[str]
    focus_diff: Optional[str]
    focus_lines: Optional[str]
    exit_on_failure: bool
    max_retries: int
    retry_count: int
    error_message: Optional[str]
    error_details: Optional[str]
    code_changes_made: bool
    planning_note: Optional[str]
    current_step_index: int
    total_steps: int

ORCHESTRATION_SCHEMA = {
    "type": "object",
    "properties": {
        # high-level intent of the request
        "intent": {
            "type": "string",
            "enum": [
                "ideation",
                "code_correction",
                "build",
                "technical_inquiry",
                "enhance",
                "extract",
                "chat",
            ],
        },
        "project": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["name", "description"],
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_name": {"type": "string"},
                    "description": {"type": "string"},
                    "assigned_module": {
                        "type": "string",
                        "enum": [
                            "PlanningModule",
                            "ManagementModule",
                            "ProgrammingModule",
                            "QAModule",
                            "ReviewModule",
                            "ResearchModule"
                        ]
                    },
                    "expected_output": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"]
                    },
                    "files_generated": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": [
                    "task_name",
                    "description",
                    "assigned_module",
                    "expected_output",
                    "status"
                ],
            },
        },
        "current_phase": {
            "type": "string",
            "enum": [
                "classification",  # NEW: before planning, intent detection
                "planning",
                "approval",
                "implementation",
                "review",
                "testing",
                "completed",
            ],
        },
        "code_correction_state": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": [
                        "awaiting_description",
                        "investigation",
                        "awaiting_confirmation",
                        "implementing",
                        "verifying"
                    ]
                },
                "user_request": {"type": "string"},
                "investigation_summary": {"type": "string"},
                "proposed_plan": {"type": "string"},
                "verification_command": {"type": "string"}
            }
        }
    },
    "required": ["intent", "project", "tasks", "current_phase"],
}