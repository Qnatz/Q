# state_manager.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from tinydb import TinyDB, Query
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConversationState:
    """Data class for conversation state with proper type hints"""
    user_id: str
    history: List[Dict[str, Any]]
    history_summary: str = ""
    extracted_info: Dict[str, Any] = None
    pending_build: Optional[Dict[str, Any]] = None
    pending_build_confirmation: Optional[Dict[str, Any]] = None
    is_in_ideation_session: bool = False
    is_in_correction_session: bool = False
    correction_phase: Optional[str] = None
    module_status: Dict[str, str] = None
    current_phase: str = "conversation"
    turn: int = 0
    user_context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.extracted_info is None:
            self.extracted_info = {}
        if self.module_status is None:
            self.module_status = {"planner": "idle", "programmer": "idle"}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return asdict(self)
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access for backward compatibility"""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"ConversationState has no attribute '{key}'")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-style get method for backward compatibility"""
        try:
            return self[key]
        except KeyError:
            return default

class StateManager:
    def __init__(self, db_path: str = 'chat_history.json'):
        self.conversation_states: Dict[str, ConversationState] = {}
        self.db = TinyDB(db_path)
        self.history_table = self.db.table('history')

    def get_conversation_state(self, user_id: str) -> ConversationState:
        """
        Retrieve or initialize conversation state for a user.
        Returns a ConversationState object that supports both attribute and dictionary access.
        """
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = ConversationState(
                user_id=user_id,
                history=[],
                history_summary="",
                extracted_info={},
                pending_build=None,
                pending_build_confirmation=None,
                is_in_ideation_session=False,
                is_in_correction_session=False,
                correction_phase=None,
                module_status={"planner": "idle", "programmer": "idle"},
                current_phase="conversation",
                turn=0,
                user_context=None
            )
        return self.conversation_states[user_id]

    def _update_conversation_state(self, user_id: str, state: ConversationState):
        """Update in-memory conversation state"""
        self.conversation_states[user_id] = state
