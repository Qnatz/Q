from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.live import Live
from rich.box import ROUNDED

from core.config import AGENT_STYLES
from utils.ui_helpers import say_user, say_assistant, say_system, say_success, say_error

console = Console()

def splash():
    # This function can be expanded with a more elaborate splash screen
    pass

def agent_log(agent_name: str, message: str) -> Panel:
    """
    Create styled agent message panel for workflow visualization.
    
    Args:
        agent_name: Name of the agent (determines styling)
        message: Log message content
        
    Returns:
        Rich Panel object with appropriate styling
    """
    style = AGENT_STYLES.get(agent_name, "white")
    return Panel(
        message, 
        title=f"[bold {style}]{agent_name}[/]]}}", 
        border_style=style, 
        expand=False
    )