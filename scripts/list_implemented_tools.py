
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.tool_registry import ToolRegistry

def list_tools():
    registry = ToolRegistry()
    tools = registry.list_tools()
    print("Implemented Tools:")
    for tool in tools:
        print(f"- {tool['name']} ({tool['description']})")

if __name__ == "__main__":
    list_tools()
