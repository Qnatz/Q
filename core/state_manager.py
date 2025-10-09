import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field

from memory.unified_memory import UnifiedMemory

logger = logging.getLogger(__name__)

@dataclass
class ConversationState:
    """Data class for conversation state with proper type hints"""
    user_id: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    history_summary: str = ""
    extracted_info: Dict[str, Any] = field(default_factory=dict)
    pending_build: Optional[Dict[str, Any]] = None
    pending_build_confirmation: Optional[Dict[str, Any]] = None
    is_in_ideation_session: bool = False
    is_in_correction_session: bool = False
    correction_phase: Optional[str] = None
    module_status: Dict[str, str] = field(default_factory=lambda: {"planner": "idle", "programmer": "idle"})
    current_phase: str = "conversation"
    turn: int = 0
    user_context: Optional[Dict[str, Any]] = None
    current_project_id: Optional[str] = None
    ideation_session_start_index: int = 0
    
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
        logger.debug(f"StateManager initialized with UnifiedMemory id: {id(self._unified_memory)}")
        self.conversation_states: Dict[str, ConversationState] = {}

    @property
    def unified_memory(self) -> UnifiedMemory:
        return self._unified_memory

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state from persistent storage"""
        try:
            if hasattr(self._unified_memory, 'tinydb'):
                return self._unified_memory.tinydb.get_state(key, default)
            else:
                logger.warning("unified_memory.tinydb not available")
                return default
        except Exception as e:
            logger.error(f"Error getting state for key '{key}': {e}")
            return default

    def set_state(self, key: str, value: Any):
        """Set state in persistent storage"""
        try:
            if hasattr(self._unified_memory, 'tinydb'):
                self._unified_memory.tinydb.store_state(key, value)
            else:
                logger.warning("unified_memory.tinydb not available, state not persisted")
        except Exception as e:
            logger.error(f"Error setting state for key '{key}': {e}")

    def append_to_state(self, key: str, value: Any):
        """Append value to a list in state"""
        try:
            current_state = self.get_state(key, [])
            if not isinstance(current_state, list):
                current_state = [current_state]
            current_state.append(value)
            self.set_state(key, current_state)
        except Exception as e:
            logger.error(f"Error appending to state for key '{key}': {e}")

    def get_conversation_state(self, user_id: str, project_id: Optional[str] = None) -> ConversationState:
        """
        Retrieve or initialize conversation state for a user and project.
        Returns a ConversationState object.
        """
        state_key = f"{user_id}_{project_id}" if project_id else user_id
        
        if state_key not in self.conversation_states:
            # Try to load from persistent storage
            persisted_state_data = self.get_state(f"conversation_state_{state_key}")
            
            if persisted_state_data:
                try:
                    loaded_state = ConversationState(**persisted_state_data)
                    self.conversation_states[state_key] = loaded_state
                    logger.info(f"Loaded conversation state for {state_key} from persistent storage.")
                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to load conversation state for {state_key}: {e}. Initializing new state.")
                    self.conversation_states[state_key] = self._initialize_new_conversation_state(user_id, project_id)
            else:
                self.conversation_states[state_key] = self._initialize_new_conversation_state(user_id, project_id)
                
        return self.conversation_states[state_key]

    def _initialize_new_conversation_state(self, user_id: str, project_id: Optional[str] = None) -> ConversationState:
        """Initialize a new conversation state"""
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
            user_context=None,
            current_project_id=project_id
        )

    def update_conversation_state(self, user_id: str, state: ConversationState, project_id: Optional[str] = None):
        """Update in-memory conversation state and persist to UnifiedMemory"""
        state_key = f"{user_id}_{project_id}" if project_id else user_id
        self.conversation_states[state_key] = state
        
        try:
            self.set_state(f"conversation_state_{state_key}", state.to_dict())
            logger.debug(f"Persisted conversation state for {state_key}.")
        except Exception as e:
            logger.error(f"Failed to persist conversation state for {state_key}: {e}")

    # Alias for backward compatibility
    def _update_conversation_state(self, user_id: str, state: ConversationState, project_id: Optional[str] = None):
        """Alias for update_conversation_state (backward compatibility)"""
        self.update_conversation_state(user_id, state, project_id)

    def clear_conversation_history(self, user_id: str, project_id: Optional[str] = None):
        """
        Clears the conversation history for a given user and project from persistent storage.
        """
        state_key = f"{user_id}_{project_id}" if project_id else user_id
        try:
            # Remove from in-memory cache
            if state_key in self.conversation_states:
                del self.conversation_states[state_key]
            
            # Remove from persistent storage
            if hasattr(self._unified_memory, 'tinydb'):
                tinydb = self._unified_memory.tinydb
                if hasattr(tinydb, 'delete_state'):
                    tinydb.delete_state(f"conversation_state_{state_key}")
                elif hasattr(tinydb, 'remove_state'):
                    tinydb.remove_state(f"conversation_state_{state_key}")
                else:
                    logger.warning("TinyDB has no delete_state or remove_state method")
            
            logger.info(f"Cleared conversation history for {state_key}.")
        except Exception as e:
            logger.error(f"Failed to clear conversation history for {state_key}: {e}")

    def get_all_conversation_states(self) -> Dict[str, ConversationState]:
        """Get all active conversation states"""
        return self.conversation_states.copy()

    def has_conversation_state(self, user_id: str, project_id: Optional[str] = None) -> bool:
        """Check if a conversation state exists"""
        state_key = f"{user_id}_{project_id}" if project_id else user_id
        return state_key in self.conversation_states
