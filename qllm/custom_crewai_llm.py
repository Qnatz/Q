import json
import re
from crewai.llm import BaseLLM
from qllm.unified_llm import UnifiedLLM
from jsonschema import validate, ValidationError


class CustomCrewAI_LLM(BaseLLM):
    def __init__(self, unified_llm: UnifiedLLM):
        super().__init__(model=unified_llm.cfg.model)
        self.unified_llm = unified_llm

    def _extract_and_validate_json(self, text: str, schema: dict) -> dict:
        """Extracts and validates a JSON object from a string."""
        # Try to find JSON in markdown code block
        json_match = re.search(r"```json\n(.*?)```", text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no markdown, try to find a raw JSON object
            json_match = re.search(r"\{{.*?\}}", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response.")

        parsed = json.loads(json_str)
        validate(instance=parsed, schema=schema)
        return parsed

    def call(self, prompt: any, **kwargs) -> str:
        if isinstance(prompt, dict) and "messages" in prompt:
            # Assuming the last message is the most recent prompt
            messages = prompt["messages"]
        elif isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            # Fallback for unexpected prompt format
            messages = [{"role": "user", "content": str(prompt)}]

        flat_prompt = "\n".join(
            [f"{m.get('role')}: {m.get('content')}" for m in messages]
        )

        schema = kwargs.get("schema")
        if schema:
            # Append schema to the last message's content
            flat_prompt += f"""

Respond only in JSON format, conforming to the following schema:
```json
{json.dumps(schema, indent=2)}
```"""

        # Filter kwargs to only include arguments expected by UnifiedLLM.generate
        unified_llm_kwargs = {
            k: v for k, v in kwargs.items() if k in ["use_tools", "response_format"]
        }

        raw_response = self.unified_llm.generate(
            [{"role": "user", "content": flat_prompt}], **unified_llm_kwargs
        )

        if schema:
            try:
                return json.dumps(self._extract_and_validate_json(raw_response, schema))
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                # If validation fails, return the raw response for now, or handle as needed
                return raw_response
        return raw_response
