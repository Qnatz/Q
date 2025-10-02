from enum import Enum

# Configuration constants
PROMPT_DIR = "agent_prompts"
MAX_RECENT_TURNS = 6
MAX_SUMMARY_TOKENS = 200
MAX_TURNS_BEFORE_BUILD = 4

# Agent message styles
AGENT_STYLES = {
    "Planning": "yellow",
    "Programming": "cyan",
    "QA": "magenta",
    "Management": "green",
    "Review": "blue",
    "Orchestrator": "bold white",
    "Research": "cyan"
}

class ResponseType(Enum):
    """Response types for conversation flow - streamlined routing system"""
    CHAT = "chat"
    BUILD = "build"
    TECHNICAL_INQUIRY = "technical_inquiry"
    IDEATION = "ideation"
    UPDATE_PROGRAMMER = "update_programmer"
    START_PLANNER = "start_planner"
    UPDATE_PLANNER = "update_planner"
    RESUME_AND_UPDATE_PLANNER = "resume_and_update_planner"
    CREATE_NEW_ISSUE = "create_new_issue"
    START_PLANNER_FOR_FOLLOWUP = "start_planner_for_followup"
    CODE_ASSIST = "code_assist"
    NO_OP = "no_op"

# Descriptions for internal processes/roles
INTERNAL_ROLES = {
    "Manager": "Clarifies requirements, extracts missing info, enhances project vision.",
    "Programming": "Builds code, fixes errors, refactors, generates snippets.",
    "Planning": "Organizes tasks, creates technical specifications, decides build priorities."
}

RESPONSE_DESCRIPTIONS = {
    ResponseType.CHAT: "Simple conversations and greetings → respond conversationally and guide toward project ideas.",
    ResponseType.BUILD: "Send to development crew immediately.",
    ResponseType.TECHNICAL_INQUIRY: "Direct to research agent for technical questions.",
    ResponseType.IDEATION: "Brainstorm initial ideas and refine vague concepts into concrete plans.",
    ResponseType.UPDATE_PROGRAMMER: "Add message to programmer's running session.",
    ResponseType.START_PLANNER: "Send well-defined, complete request to planner.",
    ResponseType.UPDATE_PLANNER: "Send new related request to running planner.",
    ResponseType.RESUME_AND_UPDATE_PLANNER: "Resume interrupted planner with additional context.",
    ResponseType.CREATE_NEW_ISSUE: "Create a new GitHub issue.",
    ResponseType.START_PLANNER_FOR_FOLLOWUP: "Send followup request to planner.",
    ResponseType.CODE_ASSIST: "Handle code help, refactoring, requirements clarification, and project enhancement.",
    ResponseType.NO_OP: "No action needed - message doesn't require routing."
}
