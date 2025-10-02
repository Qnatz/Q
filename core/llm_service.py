
import json
import re
from typing import List, Tuple, Dict, Optional, Any
from abc import ABC, abstractmethod

# Assuming these classes exist in the project environment
# from memory.prompt_manager import PromptManager 
# from qllm.unified_llm import UnifiedLLM
# from utils.ui_helpers import say_error

# Placeholder for external dependencies to make the code runnable and professional
class UnifiedLLM:
    """Placeholder for a unified LLM interface."""
    def generate(self, messages, use_tools=False):
        """Simulates LLM generation."""
        return {"content": "Simulated LLM response."}

class PromptManager:
    """Placeholder for a prompt management utility."""
    pass

def say_error(message: str):
    """Placeholder for error logging utility."""
    print(f"ERROR: {message}")

# --- Dynamic Template Service Placeholder ---

class BaseTemplateService(ABC):
    """Abstract base class for template generation services."""
    def __init__(self, llm_service: 'LLMService'):
        self.llm_service = llm_service

    @abstractmethod
    def generate_project_template(self, **kwargs) -> Dict[str, str]:
        """Generates a dynamic project template."""
        pass

    @abstractmethod
    def _is_code_file(self, file_path: str) -> bool:
        """Determines if a file is a code file."""
        pass
    
    @abstractmethod
    def _has_error_handling(self, content: str, language: str) -> bool:
        """Checks for basic error handling in code content."""
        pass
    
    @abstractmethod
    def _has_basic_structure(self, content: str, language: str) -> bool:
        """Checks for basic structural integrity in code content."""
        pass


class DynamicTemplateService(BaseTemplateService):
    """
    Service responsible for advanced, multi-file project template generation.
    (Actual complex logic would reside here).
    """
    def generate_project_template(
        self,
        language: str,
        project_type: str,
        requirements: str,
        framework: str = None,
        database: str = None,
        auth_method: str = None,
        deployment: str = None
    ) -> Dict[str, str]:
        """
        Generates a project template (Simulated for completion).
        """
        # In a real implementation, this would call the LLM to generate
        # the file structure and contents based on the comprehensive system message.
        return {
            'README.md': f"# {language.upper()} {project_type.capitalize()} Project",
            '.gitignore': "# OS and Language defaults",
            f'src/main.{self.llm_service.language_configs.get(language, {}).get("extensions", ["py"])[0]}': 
                "// Generated basic file structure."
        }
    
    def _is_code_file(self, file_path: str) -> bool:
        """Simple check for common code extensions."""
        return any(file_path.endswith(ext) for ext in 
                   ['.py', '.js', '.ts', '.java', '.cs', '.cpp', '.rs', '.go', '.php', '.rb', '.swift', '.kt', '.scala', '.dart'])

    def _has_error_handling(self, content: str, language: str) -> bool:
        """Simplified check for error handling keywords."""
        if language == 'python':
            return 'try:' in content or 'except' in content
        return True # Placeholder

    def _has_basic_structure(self, content: str, language: str) -> bool:
        """Simplified check for core structure keywords."""
        if language == 'python':
            return 'def ' in content or 'class ' in content
        return True # Placeholder

# --- LLM Service ---

class LLMService:
    """
    A professional service layer for interacting with a Unified LLM,
    specializing in expert code generation, review, and dynamic template creation.
    """
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager):
        """Initializes the LLM Service with core dependencies."""
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.language_configs: Dict[str, Dict[str, Any]] = self._get_language_configs()
        self.best_practices: Dict[str, List[str]] = self._get_best_practices()
        self.template_service = DynamicTemplateService(self)

    # --- Configuration and Helpers ---

    def _get_language_configs(self) -> Dict[str, Dict[str, Any]]:
        """Configuration for different programming languages."""
        return {
            'python': {
                'extensions': ['.py'],
                'keywords': ['def', 'class', 'import', 'from', 'if', 'for', 'while'],
                'style_guide': 'PEP 8',
                'testing_framework': 'pytest',
                'package_manager': 'pip'
            },
            'javascript': {
                'extensions': ['.js', '.jsx', '.ts', '.tsx'],
                'keywords': ['function', 'const', 'let', 'var', 'class', 'import', 'export'],
                'style_guide': 'ESLint/Prettier',
                'testing_framework': 'Jest',
                'package_manager': 'npm/yarn'
            },
            'java': {
                'extensions': ['.java'],
                'keywords': ['public', 'private', 'class', 'interface', 'import', 'package'],
                'style_guide': 'Google Java Style',
                'testing_framework': 'JUnit',
                'package_manager': 'Maven/Gradle'
            },
            'csharp': {
                'extensions': ['.cs'],
                'keywords': ['public', 'private', 'class', 'interface', 'using', 'namespace'],
                'style_guide': 'Microsoft C# Guidelines',
                'testing_framework': 'NUnit/xUnit',
                'package_manager': 'NuGet'
            },
            'cpp': {
                'extensions': ['.cpp', '.hpp', '.cc', '.h'],
                'keywords': ['#include', 'class', 'struct', 'namespace', 'template'],
                'style_guide': 'Google C++ Style',
                'testing_framework': 'Google Test',
                'package_manager': 'Conan/vcpkg'
            },
            'rust': {
                'extensions': ['.rs'],
                'keywords': ['fn', 'struct', 'enum', 'impl', 'use', 'mod'],
                'style_guide': 'Rust Style Guide',
                'testing_framework': 'Built-in',
                'package_manager': 'Cargo'
            },
            'go': {
                'extensions': ['.go'],
                'keywords': ['func', 'struct', 'interface', 'package', 'import'],
                'style_guide': 'Go Style Guide',
                'testing_framework': 'Built-in',
                'package_manager': 'Go modules'
            },
            'php': {
                'extensions': ['.php'],
                'keywords': ['function', 'class', 'interface', 'namespace', 'use'],
                'style_guide': 'PSR Standards',
                'testing_framework': 'PHPUnit',
                'package_manager': 'Composer'
            },
            'ruby': {
                'extensions': ['.rb'],
                'keywords': ['def', 'class', 'module', 'require', 'include'],
                'style_guide': 'Ruby Style Guide',
                'testing_framework': 'RSpec',
                'package_manager': 'Gem'
            },
            'swift': {
                'extensions': ['.swift'],
                'keywords': ['func', 'class', 'struct', 'protocol', 'import'],
                'style_guide': 'Swift Style Guide',
                'testing_framework': 'XCTest',
                'package_manager': 'Swift Package Manager'
            },
            'kotlin': {
                'extensions': ['.kt', '.kts'],
                'keywords': ['fun', 'class', 'data class', 'object', 'interface', 'import', 'package'],
                'style_guide': 'Kotlin Coding Conventions',
                'testing_framework': 'JUnit/Kotest',
                'package_manager': 'Gradle/Maven'
            },
            'scala': {
                'extensions': ['.scala'],
                'keywords': ['def', 'class', 'object', 'trait', 'import', 'package'],
                'style_guide': 'Scala Style Guide',
                'testing_framework': 'ScalaTest',
                'package_manager': 'SBT'
            },
            'dart': {
                'extensions': ['.dart'],
                'keywords': ['void', 'class', 'abstract', 'interface', 'import', 'library'],
                'style_guide': 'Dart Style Guide',
                'testing_framework': 'Built-in test',
                'package_manager': 'pub'
            }
        }

    def _get_best_practices(self) -> Dict[str, List[str]]:
        """Universal best practices for code generation."""
        return {
            'general': [
                'Write clean, readable, and maintainable code',
                'Use meaningful variable and function names',
                'Follow single responsibility principle',
                'Include comprehensive error handling',
                'Add appropriate comments and documentation',
                'Implement proper logging where applicable',
                'Follow language-specific naming conventions',
                'Use appropriate design patterns',
                'Ensure code is testable and modular'
            ],
            'security': [
                'Validate all inputs',
                'Use parameterized queries for database operations',
                'Implement proper authentication and authorization',
                'Handle sensitive data securely',
                'Follow secure coding practices'
            ],
            'performance': [
                'Optimize for readability first, then performance',
                'Use appropriate data structures and algorithms',
                'Avoid premature optimization',
                'Consider memory usage and efficiency',
                'Implement proper caching where beneficial'
            ]
        }

    def _detect_language(self, text: str) -> str:
        """Detect programming language from the given text (prompt or code)."""
        text_lower = text.lower()
        
        # Direct language mentions
        language_mentions = {
            'python': ['python', 'py', 'django', 'flask', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular', 'typescript', 'ts'],
            'java': ['java', 'spring', 'maven', 'gradle', 'jvm'],
            'csharp': ['c#', 'csharp', 'dotnet', '.net', 'asp.net'],
            'cpp': ['c++', 'cpp', 'cmake'],
            'rust': ['rust', 'cargo'],
            'go': ['golang', 'go'],
            'php': ['php', 'laravel', 'symfony'],
            'ruby': ['ruby', 'rails'],
            'swift': ['swift', 'ios', 'xcode'],
            'kotlin': ['kotlin', 'kt', 'android', 'jetbrains'],
            'scala': ['scala', 'akka', 'play framework'],
            'dart': ['dart', 'flutter']
        }
        
        for lang, indicators in language_mentions.items():
            if any(indicator in text_lower for indicator in indicators):
                return lang
        
        # Check for file extensions
        for lang, config in self.language_configs.items():
            for ext in config['extensions']:
                if ext in text_lower:
                    return lang
        
        # Check for language-specific keywords
        for lang, config in self.language_configs.items():
            keyword_count = sum(1 for keyword in config['keywords'] if keyword in text_lower)
            if keyword_count >= 2:
                return lang
        
        return 'python'  # Default fallback

    def generate(self, messages: List[Dict], use_tools: bool = False) -> str:
        """Generic text generation method, wrapping the underlying LLM."""
        try:
            response = self.llm.generate(messages, use_tools=use_tools)
            return self._extract_summary_text(response).strip()
        except Exception as e:
            say_error(f"LLM generation failed: {e}")
            return ""

    def _build_prompt(self, prompt: str, language: str, system_message: Optional[str] = None) -> List[Dict]:
        """Build a comprehensive prompt with a system message and user message."""
        if system_message is None:
            config = self.language_configs.get(language, self.language_configs['python'])
            
            general_practices = '\n'.join('- ' + practice for practice in self.best_practices['general'])
            security_practices = '\n'.join('- ' + practice for practice in self.best_practices['security'])
            performance_practices = '\n'.join('- ' + practice for practice in self.best_practices['performance'])
            
            system_message = f"""You are an expert {language.upper()} programmer and software architect with deep knowledge of:

LANGUAGE EXPERTISE:
- Advanced {language} programming concepts and idioms
- {config['style_guide']} coding standards and conventions  
- {config['testing_framework']} for comprehensive testing
- {config['package_manager']} for dependency management
- Popular frameworks and libraries in the {language} ecosystem

BEST PRACTICES (GENERAL):
{general_practices}

SECURITY & PERFORMANCE:
{security_practices}
{performance_practices}

CODE GENERATION REQUIREMENTS:
1. Generate production-ready, well-structured code
2. Include comprehensive error handling and edge cases
3. Add clear, concise comments explaining complex logic
4. Follow language-specific naming conventions strictly
5. Implement appropriate design patterns where beneficial
6. Include type hints/annotations where applicable
7. Structure code for maximum readability and maintainability
8. Consider scalability and extensibility in design
9. Include example usage and basic tests when appropriate
10. Optimize for the specific language's strengths and idioms

RESPONSE FORMAT:
- Provide complete, runnable code solutions
- Explain key design decisions and trade-offs
- Suggest improvements or alternative approaches when relevant
- Include setup/installation instructions if needed"""

        config = self.language_configs.get(language, self.language_configs['python'])
        
        enhanced_prompt = f"""
TASK: {prompt}

LANGUAGE CONTEXT:
- Target Language: {language.upper()}
- Style Guide: {config['style_guide']}
- Testing Framework: {config['testing_framework']}

REQUIREMENTS:
- Generate complete, production-ready code
- Include error handling and input validation
- Add comprehensive documentation/comments
- Follow {language} best practices and idioms
- Make code modular and testable
- Consider edge cases and potential issues

Please provide a complete solution with explanations of key design decisions.
"""
        
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": enhanced_prompt},
        ]

    def _extract_summary_text(self, response: Any) -> str:
        """Extract summary text from various response formats."""
        if isinstance(response, dict):
            return response.get("content") or response.get("text") or ""
        elif isinstance(response, str):
            return response
        return str(response)

    def _create_fallback_summary(self, old_messages: List[Dict]) -> str:
        """Create a fallback summary when LLM fails."""
        key_messages = (
            old_messages[:3] + old_messages[-2:]
        )  # First 3 and last 2 messages
        return " | ".join(
            msg.get("content", "")[:100].replace("\n", " ")
            for msg in key_messages
            if msg.get("content")
        )

    def _detect_project_type(self, prompt: str) -> str:
        """Detect project type from prompt."""
        prompt_lower = prompt.lower()
        
        project_types = {
            'web': ['website', 'web app', 'web application', 'frontend', 'backend', 'fullstack'],
            'mobile': ['mobile', 'android', 'ios', 'react native', 'flutter', 'app'],
            'cli': ['cli', 'command line', 'terminal', 'script', 'tool'],
            'microservice': ['microservice', 'api', 'rest', 'graphql', 'service'],
            'desktop': ['desktop', 'gui', 'application', 'windows', 'mac', 'linux'],
            'library': ['library', 'package', 'module', 'sdk'],
            'data': ['data', 'analysis', 'processing', 'etl', 'pipeline', 'machine learning'],
            'game': ['game', 'unity', 'unreal', '3d', '2d'],
        }
        
        for project_type, indicators in project_types.items():
            if any(indicator in prompt_lower for indicator in indicators):
                return project_type
        
        return 'web'  # Default fallback

    def _extract_technical_specs(self, prompt: str) -> Dict[str, str]:
        """Extract technical specifications from prompt."""
        prompt_lower = prompt.lower()
        
        specs: Dict[str, str] = {}
        
        # Detect framework
        frameworks = {
            'django': ['django'], 'flask': ['flask'], 'fastapi': ['fastapi'],
            'react': ['react'], 'vue': ['vue'], 'angular': ['angular'],
            'spring': ['spring'], 'express': ['express'],
        }
        
        for framework, indicators in frameworks.items():
            if any(indicator in prompt_lower for indicator in indicators):
                specs['framework'] = framework
                break
        
        # Detect database
        databases = {
            'postgresql': ['postgres', 'postgresql'], 'mongodb': ['mongo', 'mongodb'],
            'mysql': ['mysql'], 'sqlite': ['sqlite'], 'redis': ['redis'],
        }
        
        for database, indicators in databases.items():
            if any(indicator in prompt_lower for indicator in indicators):
                specs['database'] = database
                break
        
        # Detect authentication
        auth_methods = {
            'jwt': ['jwt', 'json web token'], 'oauth': ['oauth'],
            'firebase': ['firebase auth', 'firebase authentication'],
        }
        
        for auth, indicators in auth_methods.items():
            if any(indicator in prompt_lower for indicator in indicators):
                specs['auth_method'] = auth
                break
        
        # Detect deployment
        deployments = {
            'docker': ['docker', 'container'], 'aws': ['aws', 'amazon web services'],
            'heroku': ['heroku'], 'netlify': ['netlify'],
        }
        
        for deployment, indicators in deployments.items():
            if any(indicator in prompt_lower for indicator in indicators):
                specs['deployment'] = deployment
                break
        
        return specs

    def _calculate_template_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate template quality score (0-100)."""
        score = 0
        
        if analysis['file_count'] >= 3:
            score += 20
        if analysis['code_files'] >= 1:
            score += 20
        if analysis['has_readme']:
            score += 20
        if analysis['has_gitignore']:
            score += 20
        if analysis['has_requirements']:
            score += 20
        
        # Deduct for issues
        score -= min(len(analysis['issues']) * 5, 40)
        
        return max(0, min(100, score))

    # --- Core LLM Interaction Methods ---

    def summarize_old_history(
        self,
        old_messages: List[Dict],
        max_summary_tokens: int,
    ) -> str:
        """Generate concise conversation summary with caching."""
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
                    f"Keep it factual and under {max_summary_tokens} tokens."
                ),
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

    def generate_code(self, prompt: str, system_message: Optional[str] = None, language: Optional[str] = None) -> str:
        """
        Generates expert-level code based on a given prompt, with auto-detection.
        """
        try:
            # Auto-detect language if not specified
            if language is None:
                language = self._detect_language(prompt)
            
            # Build the prompt
            messages = self._build_prompt(prompt, language, system_message)
            
            # Generate code using the existing LLM interface
            response = self.llm.generate(messages, use_tools=False)
            
            # Extract code from response
            code_result = self._extract_summary_text(response)
            
            return code_result.strip()
            
        except Exception as e:
            say_error(f"Code generation failed: {e}")
            return ""

    def generate_multilingual_solution(self, prompt: str, languages: Optional[List[str]] = None) -> Dict[str, str]:
        """Generate code solutions in multiple programming languages."""
        if languages is None:
            languages = ['python', 'javascript', 'java']
        
        solutions: Dict[str, str] = {}
        for lang in languages:
            try:
                solution = self.generate_code(prompt, language=lang)
                solutions[lang] = solution
            except Exception as e:
                say_error(f"Failed to generate {lang} solution: {e}")
                solutions[lang] = f"Error generating {lang} solution: {str(e)}"
        
        return solutions

        def review_code(self, code: str, language: Optional[str] = None) -> str:
            """Provide expert code review with suggestions for improvement."""
            if language is None:
                language = self._detect_language(code)
            
            system_message = f"""You are an expert {language.upper()} code reviewer. 
            Analyze the provided code and provide:
            1. Code quality assessment
            2. Best practices compliance
            3. Security considerations
            4. Performance optimization suggestions
            5. Refactoring recommendations
            6. Testing suggestions
            
            Be constructive and specific in your feedback."""
            
            review_prompt = f"""Please review this {language} code:
    
    ```{language}
    {code}
    
    Provide detailed feedback on improvements, best practices, and potential issues."""
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": review_prompt},
            ]
            
            try:
                response = self.llm.generate(messages, use_tools=False)
                return self._extract_summary_text(response).strip()
            except Exception as e:
                say_error(f"Code review failed: {e}")
                return "Code review failed due to an error."

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
        return self.llm.generate_with_plan(
            prompt,
            system_instruction=system_instruction,
            chunk_size=chunk_size,
            step_size=step_size,
        )

    def explain_code(self, code: str, language: Optional[str] = None) -> str:
        """Provide detailed explanation of code functionality."""
        if language is None:
            language = self._detect_language(code)
        
        system_message = f"""You are an expert {language.upper()} programmer and teacher.
        Explain code in a clear, educational manner covering:
        1. Overall purpose and functionality
        2. Key algorithms and logic flow
        3. Important design patterns used
        4. Language-specific features utilized
        5. Potential improvements or alternatives"""
        
        explanation_prompt = f"""Please explain this {language} code in detail:

{code}

Make the explanation clear for both beginners and intermediate programmers."""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": explanation_prompt},
        ]
        
        try:
            response = self.llm.generate(messages, use_tools=False)
            return self._extract_summary_text(response).strip()
        except Exception as e:
            say_error(f"Code explanation failed: {e}")
            return "Code explanation failed due to an error."
# --- Dynamic Template Generation Methods ---

    def generate_dynamic_template(
        self,
        language: str,
        project_type: str,
        requirements: str,
        framework: Optional[str] = None,
        database: Optional[str] = None,
        auth_method: Optional[str] = None,
        deployment: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate a complete project template dynamically using AI via the template service.
        """
        return self.template_service.generate_project_template(
            language=language,
            project_type=project_type,
            requirements=requirements,
            framework=framework,
            database=database,
            auth_method=auth_method,
            deployment=deployment
        )
    def generate_template_from_prompt(self, user_prompt: str) -> Dict[str, str]:
        """
        Generate template from a natural language prompt with automatic detection of specs.
        """
        # Auto-detect language and project type from prompt
        language = self._detect_language(user_prompt)
        project_type = self._detect_project_type(user_prompt)
        
        # Extract technical specifications
        specs = self._extract_technical_specs(user_prompt)
        
        return self.generate_dynamic_template(
            language=language,
            project_type=project_type,
            requirements=user_prompt,
            **specs
        )
    def analyze_template_quality(self, template: Dict[str, str], language: str) -> Dict[str, Any]:
        """
        Analyze the quality of a generated template for completeness and structure.
        """
        analysis: Dict[str, Any] = {
            'file_count': len(template),
            'code_files': 0,
            'config_files': 0,
            'doc_files': 0,
            'has_readme': 'README.md' in template,
            'has_gitignore': '.gitignore' in template,
            'has_requirements': any('requirements' in f.lower() or 'package.json' in f for f in template),
            'issues': [],
            'score': 0
        }
        
        for file_path, content in template.items():
            if self.template_service._is_code_file(file_path):
                analysis['code_files'] += 1
                
                # Check code quality via template service helpers
                if not self.template_service._has_error_handling(content, language):
                    analysis['issues'].append(f"Missing error handling in {file_path}")
                
                if not self.template_service._has_basic_structure(content, language):
                    analysis['issues'].append(f"Poor structure in {file_path}")
            
            elif any(ext in file_path for ext in ['.json', '.yaml', '.yml', '.toml', '.ini']):
                analysis['config_files'] += 1
            elif any(ext in file_path for ext in ['.md', '.txt', '.rst']):
                analysis['doc_files'] += 1
        
        # Calculate quality score
        analysis['score'] = self._calculate_template_score(analysis)
        
        return analysis


