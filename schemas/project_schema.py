from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

@dataclass
class ProjectMetadata:
    project_id: str
    project_name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "ideation"  # e.g., "ideation", "planning", "programming", "qa", "completed", "interrupted"
    completion_rate: float = 0.0  # 0.0 to 1.0
    plan: Optional[Dict[str, Any]] = None
    refined_prompt: str = ""
    user_id: str = "default_user"
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "status": self.status,
            "completion_rate": self.completion_rate,
            "plan": self.plan,
            "refined_prompt": self.refined_prompt,
            "user_id": self.user_id,
            "conversation_history": self.conversation_history
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            project_id=data["project_id"],
            project_name=data["project_name"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            status=data.get("status", "ideation"),
            completion_rate=data.get("completion_rate", 0.0),
            plan=data.get("plan"),
            refined_prompt=data.get("refined_prompt", ""),
            user_id=data.get("user_id", "default_user"),
            conversation_history=data.get("conversation_history", [])
        )
