"""Backend implementations: - GeminiBackend: wraps google.generativeai (if available) - OpenAIHTTPBackend: talks to OpenAI-compatible HTTP servers (llama.cpp server) - SubprocessBackend: runs CLI-based models (llama.cpp CLI) — naive wrapper"""

import json
import logging
import requests
import subprocess
import os
import re
from typing import Any, Dict, List, Optional
from .utils import json_dumps_safe
from .config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Optional Gemini imports
try:
    import google.generativeai as genai  # type: ignore
    from google.generativeai.types import Tool as GeminiTool  # type: ignore
    from google.generativeai.types import FunctionDeclaration  # type: ignore
except Exception:
    genai = None
    GeminiTool = None
    FunctionDeclaration = None


class OpenAIHTTPBackend:
    """Adapter for OpenAI-compatible HTTP servers (including local llama.cpp HTTP servers). Uses OpenAI-style request/response shapes."""

    def __init__(self, cfg: Config, tool_specs: Optional[List[Dict]] = None):
        self.cfg = cfg
        self.tool_specs = tool_specs or []
        self.session = requests.Session()
        if cfg.api_key:
            self.session.headers.update({"Authorization": f"Bearer {cfg.api_key}"})
        self.session.headers.update({"Content-Type": "application/json"})
        self.base_url = cfg.api_base.rstrip("/")

    def chat(
        self,
        messages: List[Dict[str, Any]],
        use_tools: bool = True,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
        }
        # Many local servers accept an OpenAI-style "functions" field; add if provided
        if self.tool_specs and use_tools:
            payload["functions"] = [
                {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
                for t in self.tool_specs
            ]
            # hint that model can choose functions
            payload["function_call"] = "auto"

        if response_format:
            payload["response_format"] = response_format

        logger.debug("OpenAIHTTPBackend.chat payload: %s", json_dumps_safe(payload))
        resp = self.session.post(url, json=payload, timeout=None)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def extract_text(resp_json: Dict[str, Any]) -> str:
        try:
            return resp_json["choices"][0]["message"].get("content", "") or ""
        except Exception:
            return ""

    @staticmethod
    def extract_function_calls(resp_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract function call(s) from the OpenAI-style response.
        This method is designed to be flexible and handle various response formats.
        """
        out = []
        if not isinstance(resp_json, dict):
            return out

        choices = resp_json.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return out

        message = choices[0].get("message", {})
        if not isinstance(message, dict):
            return out

        # Handle both `tool_calls` and `function_call`
        tool_calls = message.get("tool_calls")
        if tool_calls:
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                function = tool_call.get("function")
                if not isinstance(function, dict):
                    continue
                name = function.get("name")
                arguments_str = function.get("arguments")
                if name and arguments_str:
                    try:
                        arguments = json.loads(arguments_str)
                        out.append({"name": name, "arguments": arguments})
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse arguments for tool {name}: {arguments_str}"
                        )
            return out

        function_call = message.get("function_call")
        if isinstance(function_call, dict):
            name = function_call.get("name")
            arguments_str = function_call.get("arguments")
            if name and arguments_str:
                try:
                    arguments = json.loads(arguments_str)
                    out.append({"name": name, "arguments": arguments})
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse arguments for function {name}: {arguments_str}"
                    )

        return out


class GeminiBackend:
    """Wrapper around google.generativeai; converts OpenAI-style tool specs into Gemini FunctionDeclaration+Tool and performs generate_content."""

    def __init__(self, cfg: Config, tool_specs: Optional[List[Dict]] = None):
        if genai is None or GeminiTool is None or FunctionDeclaration is None:
            raise ImportError(
                "google.generativeai and required types are not available. Install `google-generativeai`."
            )
        self.cfg = cfg
        self.tool_specs = tool_specs or []

        # configure API key from env (caller should set)
        genai.configure(api_key=os.getenv(cfg.gemini_api_key_env))

        # Create model client
        self.client = genai.GenerativeModel(model_name=cfg.gemini_model)

        # Convert tools to Gemini Tools (single Tool object with multiple FunctionDeclaration members)
        func_decls = []
        for t in self.tool_specs:
            try:
                fd = FunctionDeclaration(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters=t.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                )
                func_decls.append(fd)
            except Exception:
                logger.exception("Skipping invalid tool spec for Gemini: %s", t)
        self.gemini_tools = (
            [GeminiTool(function_declarations=func_decls)] if func_decls else None
        )

    @staticmethod
    def _to_gemini_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert OpenAI-style messages to Gemini `contents` format.
        - Map roles: user -> user, assistant -> model, tool -> tool (with functionResponse)
        - System messages are not supported and will raise an error.
        """
        out = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            logger.debug(f"Converting message: {m}")

            if role == "system":
                logger.error("System messages are not supported by the Gemini backend.")
                raise ValueError(
                    "System messages are not supported by the Gemini backend."
                )

            if role == "user":
                out.append({"role": "user", "parts": [str(content)]})
            elif role == "assistant":
                out.append({"role": "model", "parts": [str(content)]})
            elif role == "tool":
                name = m.get("name") or m.get("tool_name")
                if not name:
                    logger.error(f"Tool message missing name: {m}")
                    raise ValueError("Tool message must have a name.")

                resp_payload = m.get("content")
                out.append(
                    {
                        "role": "tool",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": name,
                                    "response": resp_payload,
                                }
                            }
                        ],
                    }
                )
            else:
                logger.warning(
                    f"Unknown role '{role}' in message: {m}. Treating as user message."
                )
                out.append({"role": "user", "parts": [str(content)]})

        logger.debug(f"Converted messages: {out}")
        return out

    def chat(
        self,
        messages: List[Dict[str, Any]],
        use_tools: bool = True,
        response_format: Optional[Dict] = None,
    ) -> Any:
        contents = self._to_gemini_messages(messages)
        gen_cfg = genai.GenerationConfig(
            temperature=self.cfg.temperature, max_output_tokens=self.cfg.max_tokens
        )
        if response_format and response_format.get("type") == "json":
            gen_cfg.response_mime_type = "application/json"

        kwargs = {"contents": contents, "generation_config": gen_cfg}
        if use_tools and self.gemini_tools:
            kwargs["tools"] = self.gemini_tools

        logger.debug(f"GeminiBackend.chat request kwargs: {kwargs}")
        resp = self.client.generate_content(**kwargs, request_options={'timeout': 600})
        logger.debug(f"GeminiBackend.chat raw response: {resp}")
        return resp

    @staticmethod
    def extract_text(resp_obj: Any) -> str:
        logger.debug(f"GeminiBackend.extract_text input: {resp_obj}")
        logger.debug(
            f"GeminiBackend.extract_text prompt_feedback: {getattr(resp_obj, 'prompt_feedback', 'N/A')}"
        )
        logger.debug(
            f"GeminiBackend.extract_text candidates: {getattr(resp_obj, 'candidates', 'N/A')}"
        )
        try:
            text = getattr(resp_obj, "text", "") or ""
            logger.debug(f"GeminiBackend.extract_text output: {text}")
            return text
        except Exception:
            logger.exception("Error extracting text from Gemini response.")
            return ""

    @staticmethod
    def extract_function_calls(resp_obj: Any) -> List[Dict[str, Any]]:
        logger.debug(f"GeminiBackend.extract_function_calls input: {resp_obj}")
        logger.debug(
            f"GeminiBackend.extract_function_calls prompt_feedback: {getattr(resp_obj, 'prompt_feedback', 'N/A')}"
        )
        logger.debug(
            f"GeminiBackend.extract_function_calls candidates: {getattr(resp_obj, 'candidates', 'N/A')}"
        )
        """
        Parse Gemini response candidates for functionCall entries.
        Return list of dicts: {"name": ..., "arguments": {...}}
        """
        out = []
        try:
            candidates = getattr(resp_obj, "candidates", []) or []
            if not candidates:
                logger.debug("No candidates found in Gemini response.")
                return out

            # pick top candidate content.parts
            first = getattr(candidates[0], "content", None)
            if not first:
                logger.debug("First candidate has no content.")
                return out

            parts = getattr(first, "parts", []) or []
            if not parts:
                logger.debug("First candidate content has no parts.")
                return out

            for p in parts:
                # p may be dict-like or object with attributes
                fc = None
                if isinstance(p, dict):
                    fc = p.get("functionCall") or p.get("function_call")
                else:
                    fc = getattr(p, "functionCall", None) or getattr(
                        p, "function_call", None
                    )

                if not fc:
                    continue

                # fc may be dict or an object
                if isinstance(fc, dict):
                    name = fc.get("name")
                    args = fc.get("args", {})
                else:
                    name = getattr(fc, "name", None)
                    args = getattr(fc, "args", {}) or {}

                # args could be JSON string or dict-like
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {"raw": args}
                out.append({"name": name, "arguments": args})
        except Exception:
            logger.exception("Failed to extract function calls from Gemini response")
        return out


class SubprocessBackend:
    """Naive CLI wrapper (llama.cpp style). This flattens messages into a single prompt and returns stdout. Not suitable for production without sanitation."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.cli_path = cfg.cli_path
        self.model_path = cfg.cli_model_path

    def chat(
        self, messages: List[Dict[str, Any]], max_tokens: Optional[int] = None
    ) -> str:
        prompt = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])
        cmd = [self.cli_path, "--prompt", prompt]
        if max_tokens:
            cmd.extend(["--n-predict", str(max_tokens)])
        if self.model_path:
            cmd.extend(["--model", self.model_path])

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"CLI LLM returned error: {proc.stderr.strip()}")
        return proc.stdout.strip()

    @staticmethod
    def extract_function_calls(output: str) -> List[Dict[str, Any]]:
        """
        Extracts a JSON object from a string, even if it's embedded in other text.
        """
        match = re.search(r"\{.*\}", output, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict) and "name" in data and "arguments" in data:
                    return [{"name": data["name"], "arguments": data["arguments"]}]
            except json.JSONDecodeError:
                logger.warning(
                    f"Failed to parse JSON from SubprocessBackend output: {match.group(0)}"
                )
        return []
