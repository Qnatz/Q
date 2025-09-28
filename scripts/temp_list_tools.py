import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import OrchestratorAgent

def list_active_tools():
    try:
        orchestrator = OrchestratorAgent()
        tool_registry = orchestrator.agent_manager.tool_registry
        
        print("Active Tools:")
        tools = tool_registry.list_tools()
        for tool_info in tools:
            print(f"- Name: {tool_info['name']}")
            print(f"  Description: {tool_info['description']}")
            print(f"  Type: {tool_info['type']}")
            print(f"  Keywords: {', '.join(tool_info['keywords'])}")
            print("\n")

    except Exception as e:
        print(f"Error listing tools: {e}")

if __name__ == "__main__":
    list_active_tools()

