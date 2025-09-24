from enum import Enum

# Configuration constants
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
    """Response types for conversation flow"""
    CHAT = "chat"
    EXTRACT = "extract"
    ENHANCE = "enhance"
    BUILD = "build"
    CODE_CORRECTION = "code_correction"
    TECHNICAL_INQUIRY = "technical_inquiry"
    IDEATION = "ideation"

# Descriptions for internal processes/roles
INTERNAL_ROLES = {
    "Manager": "Clarifies requirements, extracts missing info, enhances project vision.",
    "Programming": "Builds code, fixes errors, refactors, generates snippets.",
    "Planning": "Organizes tasks, creates technical specifications, decides build priorities."
}

RESPONSE_DESCRIPTIONS = {
    ResponseType.CHAT: "Greetings or general questions → guide user toward project needs.",
    ResponseType.EXTRACT: "Missing 1-2 critical pieces → ask specific questions (LIMIT: 2 turns max).",
    ResponseType.ENHANCE: "Present enhanced vision → ask for build confirmation.",
    ResponseType.BUILD: "Send to development crew immediately.",
    ResponseType.CODE_CORRECTION: "Direct to programmer for immediate fixes.",
    ResponseType.TECHNICAL_INQUIRY: "Direct to research agent.",
    ResponseType.IDEATION: "Generate initial ideas and high-level plans."
}


