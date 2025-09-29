import json
from typing import List, Tuple, Dict, Any, Optional

from memory.prompt_manager import PromptManager
from qllm.unified_llm import UnifiedLLM
from utils.ui_helpers import say_error
import re


class LLMService:
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.language_configs = {
            'python': {'extensions': ['.py'], 'frameworks': ['django', 'flask', 'fastapi', 'pytest', 'numpy', 'pandas'], 'testing_framework': 'pytest'},
            'javascript': {'extensions': ['.js', '.ts', '.jsx', '.tsx'], 'frameworks': ['react', 'vue', 'angular', 'express', 'nextjs', 'jest'], 'testing_framework': 'jest'},
            'java': {'extensions': ['.java'], 'frameworks': ['spring', 'hibernate', 'maven', 'gradle', 'junit'], 'testing_framework': 'junit'},
            'go': {'extensions': ['.go'], 'frameworks': ['gin', 'echo', 'gorilla'], 'testing_framework': 'testing'},
            'rust': {'extensions': ['.rs'], 'frameworks': ['actix', 'warp', 'tokio'], 'testing_framework': 'cargo test'},
            'c#': {'extensions': ['.cs'], 'frameworks': ['asp.net', 'unity'], 'testing_framework': 'nunit'},
            'php': {'extensions': ['.php'], 'frameworks': ['laravel', 'symfony'], 'testing_framework': 'phpunit'},
            'ruby': {'extensions': ['.rb'], 'frameworks': ['rails', 'sinatra'], 'testing_framework': 'rspec'},
            'swift': {'extensions': ['.swift'], 'frameworks': ['ios', 'macos'], 'testing_framework': 'xctest'},
            'kotlin': {'extensions': ['.kt'], 'frameworks': ['android', 'spring'], 'testing_framework': 'junit'},
            'typescript': {'extensions': ['.ts', '.tsx'], 'frameworks': ['react', 'angular', 'nextjs'], 'testing_framework': 'jest'},
            'html': {'extensions': ['.html', '.htm'], 'frameworks': [], 'testing_framework': 'none'},
            'css': {'extensions': ['.css', '.scss', '.less'], 'frameworks': [], 'testing_framework': 'none'},
        }

    def _detect_language(self, text: str) -> str:
        """Basic language detection based on keywords and common patterns."""
        text_lower = text.lower()
        if "python" in text_lower or "pip" in text_lower or "django" in text_lower or "flask" in text_lower:
            return "python"
        if "javascript" in text_lower or "node" in text_lower or "react" in text_lower or "vue" in text_lower:
            return "javascript"
        if "java" in text_lower or "spring" in text_lower or "maven" in text_lower:
            return "java"
        if "go" in text_lower or "golang" in text_lower:
            return "go"
        if "rust" in text_lower or "cargo" in text_lower:
            return "rust"
        if "c#" in text_lower or "dotnet" in text_lower:
            return "c#"
        if "php" in text_lower or "laravel" in text_lower:
            return "php"
        if "ruby" in text_lower or "rails" in text_lower:
            return "ruby"
        if "swift" in text_lower or "ios" in text_lower:
            return "swift"
        if "kotlin" in text_lower or "android" in text_lower:
            return "kotlin"
        if "typescript" in text_lower or "ts" in text_lower:
            return "typescript"
        if "html" in text_lower or "webpage" in text_lower:
            return "html"
        if "css" in text_lower or "stylesheet" in text_lower:
            return "css"
        return "unknown"

    def _detect_language_with_context(self, prompt: str, file_context: str = None) -> str:
        """Enhanced language detection with file context and project structure awareness"""
        # Analyze file extensions in context
        if file_context:
            for lang, config in self.language_configs.items():
                for ext in config['extensions']:
                    if re.search(rf'\b\w+{ext}\b', file_context):
                        return lang
            
        # Detect frameworks and libraries more precisely
        prompt_lower = prompt.lower()
        for lang, config in self.language_configs.items():
            for framework in config['frameworks']:
                if framework in prompt_lower:
                    return lang
        
        return self._detect_language(prompt)

    def detect_project_structure(self, prompt: str) -> Dict:
        """Analyze prompt for project structure requirements"""
        structure_indicators = {
            'microservice': ['microservice', 'api', 'rest', 'endpoint', 'controller'],
            'cli_tool': ['cli', 'command line', 'terminal', 'script'],
            'library': ['library', 'package', 'module', 'import'],
            'web_app': ['web app', 'website', 'frontend', 'backend', 'fullstack'],
            'mobile_app': ['mobile', 'ios', 'android', 'react native', 'flutter'],
            'data_processing': ['data', 'analysis', 'processing', 'etl', 'pipeline']
        }
        
        detected_structures = []
        for structure, indicators in structure_indicators.items():
            if any(indicator in prompt.lower() for indicator in indicators):
                detected_structures.append(structure)
        
        return {
            'structures': detected_structures,
            'primary_structure': detected_structures[0] if detected_structures else 'general'
        }

    def summarize_old_history(
        self,
        old_messages: List[dict],
        max_summary_tokens: int,
    ) -> str:
        """Generate concise summary with caching"""
        if not old_messages:
            return ""

        try:
            combined_content = "\n".join(
                msg.get("content", "") for msg in old_messages if msg.get("content")
            )

            system_prompt = {
                "role": "system",
                "content": (
                    "You are a concise summarizer. Summarize the conversation focusing on: "
                    "- User's main requirements and goals\n"
                    "- Key decisions made\n"
                    "- Outstanding questions or missing information\n"
                    "Keep it factual and under {max_tokens} tokens."
                ).format(max_tokens=max_summary_tokens),
            }

            user_prompt = {
                "role": "user",
                "content": f"Conversation to summarize:\n\n{combined_content}\n\nProvide a concise summary:",
            }

            response = self.llm.generate(
                [system_prompt, user_prompt], use_tools=False
            )
            summary_text = self._extract_summary_text(response)

            return summary_text.strip()

        except Exception as e:
            say_error(f"History summarization failed: {e}")
            return self._create_fallback_summary(old_messages)

    def _extract_summary_text(self, response) -> str:
        """Extract summary text from various response formats"""
        if isinstance(response, dict):
            return response.get("content") or response.get("text") or ""
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    def _create_fallback_summary(self, old_messages: List[dict]) -> str:
        """Create a fallback summary when LLM fails"""
        key_messages = (
            old_messages[:3] + old_messages[-2:]
        )  # First 3 and last 2 messages
        return " | ".join(
            msg.get("content", "")[:100].replace("\n", " ")
            for msg in key_messages
            if msg.get("content")
        )

    def generate_code(self, prompt: str, language: Optional[str] = None, system_message: Optional[str] = None) -> str:
        """Generates code based on a given prompt and target language."""
        if language is None:
            language = self._detect_language_with_context(prompt)
            if language == "unknown":
                language = "Python" # Default to Python if detection fails

        if system_message is None:
            system_message = f"You are an expert {language} programmer. Generate clean, efficient, and well-documented code."

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]
        try:
            # Assuming self.llm is UnifiedLLM and has a generate method
            response = self.llm.generate(messages, use_tools=False)
            return response.strip()
        except Exception as e:
            say_error(f"Code generation failed: {e}")
            return ""

    def analyze_code_quality(self, code: str, language: str) -> Dict:
        """Automated code quality analysis"""
        analysis = {
            'complexity': self._calculate_complexity(code, language),
            'security_risks': self._detect_security_issues(code, language),
            'performance_issues': self._detect_performance_issues(code, language),
            'maintainability': self._assess_maintainability(code, language),
            'best_practices_compliance': self._check_best_practices(code, language)
        }
        
        return analysis

    def _calculate_complexity(self, code: str, language: str) -> Any:
        """Placeholder for code complexity calculation"""
        # This could involve external tools or LLM calls
        return "Not implemented"

    def _detect_security_issues(self, code: str, language: str) -> List[str]:
        """Detect common security vulnerabilities using regex or LLM"""
        security_patterns = {
            'python': [
                (r'eval\s*\(', 'Use of eval() - security risk'),
                (r'exec\s*\(', 'Use of exec() - security risk'),
                (r'pickle\.loads', 'Unsafe deserialization with pickle'),
                (r'subprocess\.call.*shell=True', 'Shell injection risk'),
            ],
            'javascript': [
                (r'eval\s*\(', 'Use of eval() - security risk'),
                (r'innerHTML\s*=', 'Potential XSS vulnerability'),
                (r'localStorage.*password', 'Storing passwords in localStorage'),
            ],
            # Add patterns for other languages
        }
        
        issues = []
        for pattern, message in security_patterns.get(language, []):
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(message)
        
        # Optionally, use LLM for more advanced security analysis
        # if self.llm:
        #     prompt = self.prompt_manager.get_prompt("security_analysis_prompt")
        #     if prompt:
        #         llm_analysis = self.llm.generate([{"role": "system", "content": prompt}, {"role": "user", "content": f"Analyze this {language} code for security issues:\n```\n{code}\n```"}])
        #         # Parse LLM response and add to issues

        return issues

    def _detect_performance_issues(self, code: str, language: str) -> Any:
        """Placeholder for performance issue detection"""
        return "Not implemented"

    def _assess_maintainability(self, code: str, language: str) -> Any:
        """Placeholder for maintainability assessment"""
        return "Not implemented"

    def _check_best_practices(self, code: str, language: str) -> Any:
        """Placeholder for best practices compliance check"""
        return "Not implemented"