from pathlib import Path

def load_system_prompt() -> str:
    """Load the mentor system prompt from gpt_system/system.md."""
    system_path = Path(__file__).resolve().parent.parent / "gpt_system" / "system.md"
    if not system_path.exists():
        raise FileNotFoundError(f"System prompt missing: {system_path}")
    return system_path.read_text(encoding="utf-8")
