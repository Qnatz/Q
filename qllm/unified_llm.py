"""UnifiedLLM: unified entrypoint for CrewAI-like agents."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from .backends import (
    GeminiBackend,
    OpenAIHTTPBackend,
    SubprocessBackend,
)
from .config import Config
from .utils import json_dumps_safe

logger = logging.getLogger(__name__)


class UnifiedLLM:
    def __init__(
        self,
        cfg: Config,
        tool_specs: Optional[List[Dict[str, Any]]] = None,
        tool_impls: Optional[Dict[str, Callable[..., Any]]] = None,
    ):
        self.cfg = cfg
        self.tool_specs = tool_specs or []
        self.tool_impls = tool_impls or {}

        backend = cfg.backend.lower()
        if backend == "gemini":
            self.backend_impl = GeminiBackend(cfg, tool_specs=self.tool_specs)
        elif backend in ("openai", "http"):
            self.backend_impl = OpenAIHTTPBackend(cfg, tool_specs=self.tool_specs)
        elif backend in ("cli", "subprocess"):
            self.backend_impl = SubprocessBackend(cfg)
        else:
            raise ValueError(f"Unsupported backend: {cfg.backend}")

    def _run_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        fn = self.tool_impls.get(name)
        if fn is None:
            # logger.warning("Tool requested but not implemented: %s", name)
            return {"error": f"Tool '{name}' not implemented."}
        try:
            if isinstance(arguments, dict):
                return fn(**arguments)
            else:
                return fn(arguments)
        except Exception as e:
            # logger.exception("Tool %s raised an exception", name)
            return {"error": f"Tool '{name}' raised exception: {e}"}

    def _append_function_result_to_messages(
        self,
        messages: List[Dict[str, Any]],
        backend_kind: str,
        name: str,
        result: Any,
    ):
        if backend_kind in ("openai", "http"):
            messages.append(
                {
                    "role": "tool",
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
        elif backend_kind == "gemini":
            messages.append({"role": "tool", "name": name, "content": result})
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": f"[tool-{name}]-> {json_dumps_safe(result)}",
                }
            )

    def generate(
        self,
        messages: List[Dict[str, Any]],
        use_tools: bool = True,
        response_format: Optional[Dict] = None,
    ) -> str:
        backend_kind = self.cfg.backend.lower()
        messages = list(messages)
        loop_count = 0

        try:
            while True:
                loop_count += 1
                if loop_count > max(1, self.cfg.max_tool_loops):
                    # logger.warning(
                    #     "Reached max_tool_loops (%s). Stopping.",
                    #     self.cfg.max_tool_loops,
                    # )
                    break

                if backend_kind == "gemini":
                    resp = self.backend_impl.chat(
                        messages, use_tools=use_tools, response_format=response_format
                    )
                    assistant_text = self.backend_impl.extract_text(resp)
                    function_calls = self.backend_impl.extract_function_calls(resp)
                elif backend_kind in ("openai", "http"):
                    # Do not pass response_format for http backend as it might not support it
                    resp_json = self.backend_impl.chat(messages, use_tools=use_tools)
                    assistant_text = self.backend_impl.extract_text(resp_json)
                    function_calls = self.backend_impl.extract_function_calls(resp_json)
                elif backend_kind in ("cli", "subprocess"):
                    raw_out = self.backend_impl.chat(
                        messages, max_tokens=self.cfg.max_tokens
                    )
                    assistant_text = raw_out
                    function_calls = self.backend_impl.extract_function_calls(raw_out)
                else:
                    raise ValueError("Unsupported backend: " + backend_kind)

                if not function_calls:
                    # logger.debug(
                    #     f"UnifiedLLM.generate: No function calls. Returning assistant_text: {assistant_text}"
                    # )
                    return assistant_text or ""

                fc = function_calls[0]
                name = fc.get("name")
                args = fc.get("arguments", {}) or {}

                # logger.info(
                #     "Executing tool: %s with args: %s",
                #     name,
                #     json_dumps_safe(args),
                # )
                result = self._run_tool(name, args)

                self._append_function_result_to_messages(
                    messages, backend_kind, name, result
                )

            # final call (after loop exit)
            try:
                if backend_kind == "gemini":
                    final = self.backend_impl.chat(
                        messages, use_tools=False, response_format=response_format
                    )
                    return self.backend_impl.extract_text(final) or ""
                elif backend_kind in ("openai", "http"):
                    final_json = self.backend_impl.chat(messages, use_tools=False)
                    return self.backend_impl.extract_text(final_json) or ""
                elif backend_kind in ("cli", "subprocess"):
                    return self.backend_impl.chat(messages, max_tokens=self.cfg.max_tokens)
            except Exception:
                # logger.exception("Final backend call failed")
                pass
            return ""
        except Exception as e:
            # logger.error(f"Error during LLM generation: {e}")
            return json.dumps({
                "error": f"Error during LLM generation: {e}"
            })

    def generate_with_plan(
        self,
        prompt: any,
        system_instruction: Optional[str] = None,
        chunk_size: int = 512,
        step_size: int = 256,
    ) -> str:
        """
        Generates content with a plan, potentially in chunks.
        For now, this will just call the main generate method.
        """
        if isinstance(prompt, str):
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt

        # For now, just call the main generate method.
        # Future: Implement chunking logic if needed.
        return self.generate(messages, use_tools=True)
