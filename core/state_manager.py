# state_manager.py
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

import logging
from memory.unified_memory import UnifiedMemory

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
    def __init__(self, unified_memory: UnifiedMemory = None):
        self._unified_memory = unified_memory or UnifiedMemory()
        self.conversation_states: Dict[str, ConversationState] = {}

    @property
    def unified_memory(self) -> UnifiedMemory:
        return self._unified_memory

    def get_state(self, key: str, default: Any = None) -> Any:
        return self._unified_memory.get_state(key, default)

    def set_state(self, key: str, value: Any):
        self._unified_memory.set_state(key, value)

    def append_to_state(self, key: str, value: Any):
        # Assuming state is a list, append to it. If not, create a new list.
        current_state = self._unified_memory.get_state(key, [])
        if not isinstance(current_state, list):
            current_state = [current_state] # Convert to list if not already
        current_state.append(value)
        self._unified_memory.set_state(key, current_state)

    def get_conversation_state(self, user_id: str) -> ConversationState:
        """
        Retrieve or initialize conversation state for a user.
        Returns a ConversationState object that supports both attribute and dictionary access.
        """
        if user_id not in self.conversation_states:
            # Try to load from persistent memory
            persisted_state_data = self._unified_memory.get_state(f"conversation_state_{user_id}")
            if persisted_state_data:
                try:
                    # Ensure all fields are present, providing defaults for new ones
                    loaded_state = ConversationState(**persisted_state_data)
                    self.conversation_states[user_id] = loaded_state
                    logger.info(f"Loaded conversation state for user {user_id} from memory.")
                except TypeError as e:
                    logger.error(f"Failed to load conversation state for user {user_id}: {e}. Initializing new state.")
                    self.conversation_states[user_id] = self._initialize_new_conversation_state(user_id)
            else:
                self.conversation_states[user_id] = self._initialize_new_conversation_state(user_id)
        return self.conversation_states[user_id]

    def _initialize_new_conversation_state(self, user_id: str) -> ConversationState:
        return ConversationState(
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

    def _update_conversation_state(self, user_id: str, state: ConversationState):
        """Update in-memory conversation state and persist to UnifiedMemory"""
        self.conversation_states[user_id] = state
        self._unified_memory.set_state(f"conversation_state_{user_id}", state.to_dict())
        logger.debug(f"Persisted conversation state for user {user_id}.")
