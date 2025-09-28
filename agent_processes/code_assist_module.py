# code_assist_module.py
import json
import re
from typing import Dict, Any, Optional, List, Generator
from dataclasses import dataclass
import logging

from core.llm_service import LLMService
from core.state_manager import ConversationState
from tools.tool_registry import ToolRegistry, ToolExecutionStatus
from utils.json_utils import safe_json_extract
from utils.validation_utils import validate
from memory.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

@dataclass
class CodeAssistResult:
    success: bool
    message: str
    action_type: str  # explain, refactor, debug, generate, optimize
    code_suggestions: Optional[List[Dict[str, Any]]] = None
    executed_tools: Optional[List[str]] = None
    warnings: Optional[List[str]] = None

class CodeAssistAgent:
    def __init__(self, llm_service: LLMService, tool_registry: ToolRegistry, prompt_manager: PromptManager):
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.prompt_manager = prompt_manager
        self._max_retries = 2
        self._supported_actions = {
            "explain", "refactor", "debug", "generate", "optimize", 
            "translate", "document", "test", "review"
        }

from qllm.unified_llm import UnifiedLLM

class CodeAssistModule:
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager

    def get_assistance(self, action_type: str, user_query: str, context: str) -> Dict[str, any]:
        """Get code assistance based on the action type."""
        prompt_name = "code_assist_prompt"
        prompt = self.prompt_manager.get_prompt(prompt_name)
        if not prompt:
            return {"error": f"Prompt '{prompt_name}' not found."}

        formatted_prompt = prompt.format(action=action_type, user_query=user_query, context=context)

        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": user_query},
        ]

        try:
            response = self.llm.generate(messages)
            return json.loads(response)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response from the language model."}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {e}"}

    def _get_fallback_prompt(self, action_type: str) -> str:
        """Fallback prompts when main prompts are unavailable"""
        base_prompt = f"""You are an expert code assistant specializing in {action_type}.
        Analyze the user's request and provide helpful, accurate code assistance.
        
        Guidelines:
        - Be precise and technical
        - Provide code examples when relevant
        - Consider best practices and security
        - Offer multiple solutions when appropriate
        - Explain your reasoning
        
        Format your response as JSON with:
        - \"action\": \"{action_type}\" 
        - \"explanation\": \"Clear explanation\"
        - \"code_suggestions\": [{{\"language\": \"lang\", \"code\": \"snippet\", \"description\": \"desc\"}}]
        - \"next_steps\": [\"suggested actions\"]"""
        
        return base_prompt

    def _detect_action_type(self, user_query: str) -> str:
        """Detect the type of code assistance needed"""
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ["explain", "what does", "how does"]):
            return "explain"
        elif any(word in query_lower for word in ["refactor", "clean up", "improve code"]):
            return "refactor"
        elif any(word in query_lower for word in ["debug", "error", "fix", "why isn't"]):
            return "debug"
        elif any(word in query_lower for word in ["generate", "create", "write code"]):
            return "generate"
        elif any(word in query_lower for word in ["optimize", "make faster", "performance"]):
            return "optimize"
        elif any(word in query_lower for word in ["translate", "convert to", "rewrite in"]):
            return "translate"
        elif any(word in query_lower for word in ["document", "add docs", "create documentation"]):
            return "document"
        elif any(word in query_lower for word in ["test", "write tests", "create tests"]):
            return "test"
        elif any(word in query_lower for word in ["review", "code review", "critique code"]):
            return "review"
        else:
            return "explain"  # Default action

    def _execute_code_tools(self, action_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute relevant code tools based on action type"""
        tool_results = {}
        executed_tools = []
        
        try:
            if action_type == "refactor" and self.tool_registry.has_tool("code_refactor_tool"):
                result = self.tool_registry.execute_tool("code_refactor_tool", context)
                if result.status == ToolExecutionStatus.SUCCESS:
                    tool_results["refactored_code"] = result.result
                    executed_tools.append("code_refactor_tool")
            
            elif action_type == "debug" and self.tool_registry.has_tool("code_debug_tool"):
                result = self.tool_registry.execute_tool("code_debug_tool", context)
                if result.status == ToolExecutionStatus.SUCCESS:
                    tool_results["debug_analysis"] = result.result
                    executed_tools.append("code_debug_tool")
            
            # Add more tool executions as needed
            
        except Exception as e:
            logger.error(f"Tool execution failed for {action_type}: {e}")
        
        return {"tool_results": tool_results, "executed_tools": executed_tools}

    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate the structure of the code assist response"""
        required_keys = {"action", "explanation"}
        return all(key in response for key in required_keys)

    def assist_code(self, user_query: str, state: ConversationState) -> Dict[str, Any]:
        """Advanced code assistance with context awareness"""
        logger.info(f"Processing code assistance request: {user_query[:100]}...")
        
        # Detect action type from query
        action_type = self._detect_action_type(user_query)
        
        # Get context from conversation state
        context = self._build_context(state, action_type)
        
        for attempt in range(self._max_retries):
            try:
                # Execute relevant tools first
                tool_results = self._execute_code_tools(action_type, context)
                
                # Generate LLM response with context
                system_prompt = self._get_system_prompt(action_type)
                messages = self._build_messages(system_prompt, user_query, context, tool_results)
                
                llm_response = self.llm_service.generate(messages, use_tools=False)
                parsed_response = safe_json_extract(llm_response) or self._parse_text_response(llm_response)
                
                if self._validate_response(parsed_response):
                    return self._format_success_response(parsed_response, tool_results, action_type)
                
                logger.warning(f"Invalid response format on attempt {attempt + 1}")
                
            except Exception as e:
                logger.error(f"Code assistance attempt {attempt + 1} failed: {e}")
                if attempt == self._max_retries - 1:
                    return self._format_error_response(action_type, str(e))
        
        return self._format_error_response(action_type, "Max retries exceeded")

    def assist_code_streaming(self, user_query: str, state: ConversationState) -> Generator[Dict[str, Any], None, None]:
        """Streaming version for real-time code assistance"""
        logger.info(f"Starting streaming code assistance: {user_query[:100]}...")
        
        action_type = self._detect_action_type(user_query)
        context = self._build_context(state, action_type)
        
        try:
            # Yield initial status
            yield {"type": "status", "action": action_type, "message": "Analyzing your code request..."}
            
            # Execute tools
            tool_results = self._execute_code_tools(action_type, context)
            if tool_results["executed_tools"]:
                yield {"type": "tool_result", "tools": tool_results["executed_tools"]}
            
            # Stream LLM response
            system_prompt = self._get_system_prompt(action_type)
            messages = self._build_messages(system_prompt, user_query, context, tool_results)
            
            # Assuming llm_service supports streaming
            for chunk in self.llm_service.generate_stream(messages, use_tools=False):
                yield {"type": "chunk", "content": chunk}
            
            yield {"type": "complete", "status": "success"}
            
        except Exception as e:
            logger.error(f"Streaming code assistance failed: {e}")
            yield {"type": "error", "message": str(e)}

    def _build_context(self, state: ConversationState, action_type: str) -> Dict[str, Any]:
        """Build context from conversation state"""
        context = {
            "action_type": action_type,
            "conversation_phase": state.current_phase,
            "user_turn": state.turn,
            "has_extracted_info": bool(state.extracted_info),
            "module_status": state.module_status
        }
        
        # Add code-specific context if available
        if state.extracted_info and "code_context" in state.extracted_info:
            context["code_context"] = state.extracted_info["code_context"]
        
        if state.user_context and "programming_language" in state.user_context:
            context["preferred_language"] = state.user_context["programming_language"]
        
        return context

    def _build_messages(self, system_prompt: str, user_query: str, 
                       context: Dict[str, Any], tool_results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build messages for LLM"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context information
        context_str = f"Context: {json.dumps(context, indent=2)}" if context else ""
        if tool_results.get("tool_results"):
            context_str += f"\nTool Results: {json.dumps(tool_results['tool_results'], indent=2)}"
        
        if context_str:
            messages.append({"role": "user", "content": f"{context_str}\n\nUser Query: {user_query}"})
        else:
            messages.append({"role": "user", "content": user_query})
        
        return messages

    def _parse_text_response(self, text_response: str) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails"""
        # Try to extract code blocks and structure the response
        code_blocks = re.findall(r'```(?:\[w+)?\n(.*?)```', text_response, re.DOTALL)
        
        return {
            "action": "explain",  # Default action
            "explanation": text_response,
            "code_suggestions": [{"code": block, "language": "auto"} for block in code_blocks] if code_blocks else None
        }

    def _format_success_response(self, parsed_response: Dict[str, Any], 
                               tool_results: Dict[str, Any], action_type: str) -> Dict[str, Any]:
        """Format successful response"""
        return {
            "type": "code_assist_response",
            "action": action_type,
            "message": parsed_response.get("explanation", "Code assistance completed."),
            "code_suggestions": parsed_response.get("code_suggestions", []),
            "executed_tools": tool_results.get("executed_tools", []),
            "tool_results": tool_results.get("tool_results", {}),
            "next_steps": parsed_response.get("next_steps", []),
            "success": True
        }

    def _format_error_response(self, action_type: str, error_msg: str) -> Dict[str, Any]:
        """Format error response"""
        return {
            "type": "code_assist_response",
            "action": action_type,
            "message": f"Sorry, I encountered an error while processing your {action_type} request: {error_msg}",
            "code_suggestions": [],
            "executed_tools": [],
            "tool_results": {},
            "next_steps": ["Please try rephrasing your request", "Check your code syntax"],
            "success": False
        }