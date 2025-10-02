import json
import re
import logging
from typing import List, Tuple, Dict, Optional, Any
from pathlib import Path

from memory.prompt_manager import PromptManager
from qllm.unified_llm import UnifiedLLM
from utils.ui_helpers import say_error

class DynamicTemplateService:
    """Handles dynamic template generation using LLM"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.template_cache = {}
    
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
        """Generate complete project template dynamically"""
        
        # Check cache first
        cache_key = f"{language}_{project_type}_{framework}_{database}"
        if cache_key in self.template_cache:
            return self.template_cache[cache_key]
        
        # Build detailed prompt
        prompt = self._build_template_prompt(
            language, project_type, requirements, 
            framework, database, auth_method, deployment
        )
        
        # Generate template using LLM
        system_message = self._get_architect_system_message(language)
        
        try:
            response = self.llm_service.generate_code(
                prompt=prompt,
                system_message=system_message,
                language=language
            )
            
            # Parse the response
            template = self._parse_template_response(response)
            
            # Validate and enhance the template
            template = self._validate_and_enhance_template(
                template, language, project_type
            )
            
            # Cache the result
            self.template_cache[cache_key] = template
            
            return template
            
        except Exception as e:
            logging.error(f"Dynamic template generation failed: {e}")
            return self._get_fallback_template(language, project_type)
    
    def _build_template_prompt(
        self,
        language: str,
        project_type: str,
        requirements: str,
        framework: str,
        database: str,
        auth_method: str,
        deployment: str
    ) -> str:
        """Build detailed context-aware prompt for template generation"""
        
        context = self._build_project_context(
            language, project_type, framework, database, auth_method, deployment
        )
        
        prompt = f"""
Generate a complete, production-ready {language.upper()} {project_type} project template.

PROJECT SPECIFICATIONS:
- Primary Language: {language}
- Project Type: {project_type}
- Framework: {framework or 'Standard library'}
- Database: {database or 'None'}
- Authentication: {auth_method or 'None'} 
- Deployment: {deployment or 'None'}
- User Requirements: {requirements}

PROJECT CONTEXT:
{context['architecture']}

EXPECTED FILE STRUCTURE:
{context['file_structure']}

KEY TECHNICAL REQUIREMENTS:
{context['technical_requirements']}

OUTPUT FORMAT:
Return ONLY a valid JSON object where:
- Keys are relative file paths (e.g., "src/main.py", "requirements.txt")
- Values are complete file contents

CRITICAL: 
- Include ALL necessary files for a working project
- Follow current security best practices
- Add proper error handling and logging
- Include configuration files and documentation
- Make code modular, testable, and well-documented

Example format:
{{
  "src/main.py": "complete code here...",
  "requirements.txt": "dependencies...",
  "README.md": "# Project\\n\\nDescription...",
  ".gitignore": "*.pyc\\n__pycache__/",
  "config.py": "configuration code..."
}}

Now generate the complete project template:
"""
        return prompt
    
    def _build_project_context(
        self,
        language: str,
        project_type: str,
        framework: str,
        database: str,
        auth_method: str,
        deployment: str
    ) -> Dict[str, str]:
        """Build comprehensive project context"""
        
        return {
            "architecture": self._suggest_architecture(language, project_type, framework),
            "file_structure": self._suggest_file_structure(language, project_type),
            "technical_requirements": self._suggest_technical_requirements(
                language, framework, database, auth_method, deployment
            )
        }
    
    def _suggest_architecture(self, language: str, project_type: str, framework: str) -> str:
        """Suggest appropriate architecture patterns"""
        
        architectures = {
            "web": {
                "python": "MVC/MVT pattern with separation of concerns",
                "javascript": "Component-based architecture with state management",
                "java": "Layered architecture (Controller-Service-Repository)",
            },
            "mobile": {
                "kotlin": "MVVM with Repository pattern and Room database",
                "swift": "MVVM with Combine framework",
                "javascript": "Component-based with state management",
            },
            "microservice": {
                "python": "FastAPI/Flas with dependency injection",
                "java": "Spring Boot with microservices patterns",
                "go": "Clean architecture with goroutines",
            },
            "cli": {
                "python": "Modular command structure with click/argparse",
                "javascript": "Commander.js with plugin system",
                "go": "Cobra-based CLI structure",
            }
        }
        
        arch = architectures.get(project_type, {}).get(language, "Clean architecture with separation of concerns")
        return f"Recommended Architecture: {arch}"
    
    def _suggest_file_structure(self, language: str, project_type: str) -> str:
        """Suggest appropriate file structure"""
        
        structures = {
            "python": {
                "web": "src/, tests/, config/, static/, templates/",
                "cli": "src/package/, cli/, tests/, docs/",
                "microservice": "app/, core/, models/, services/, api/",
            },
            "javascript": {
                "web": "src/components/, src/pages/, src/utils/, public/",
                "mobile": "src/screens/, src/components/, src/navigation/, assets/",
                "backend": "src/controllers/, src/models/, src/routes/, config/",
            },
            "java": {
                "web": "src/main/java/com/example/, src/test/java/, resources/",
                "microservice": "controller/, service/, repository/, model/, config/",
            }
        }
        
        structure = structures.get(language, {}).get(project_type, "Standard project structure")
        return f"Expected Structure: {structure}"
    
    def _suggest_technical_requirements(
        self,
        language: str,
        framework: str,
        database: str,
        auth_method: str,
        deployment: str
    ) -> str:
        """Build technical requirements section"""
        
        requirements = []
        
        if framework:
            requirements.append(f"- Use {framework} framework with best practices")
        
        if database:
            requirements.append(f"- Implement data layer with {database}")
            requirements.append(f"- Include database migrations and models")
        
        if auth_method:
            requirements.append(f"- Implement {auth_method} authentication")
            requirements.append(f"- Add authorization middleware")
        
        if deployment:
            requirements.append(f"- Include {deployment} deployment configuration")
            requirements.append(f"- Add Dockerfile and CI/CD configuration")
        
        # Always include these
        requirements.extend([
            "- Add comprehensive error handling",
            "- Implement proper logging",
            "- Include unit tests and documentation",
            "- Follow security best practices",
            "- Add environment configuration"
        ])
        
        return "\n".join(requirements)
    
    def _get_architect_system_message(self, language: str) -> str:
        """Get system message for software architect role"""
        
        return f"""You are a senior software architect and {language.upper()} expert.

Your role is to generate complete, production-ready project templates that:

1. FOLLOW BEST PRACTICES: Use industry standards, design patterns, and secure coding
2. BE COMPLETE: Include all necessary files - source, config, docs, tests
3. BE MODULAR: Create well-structured, maintainable code
4. BE SECURE: Implement proper authentication, validation, and security measures
5. BE DEPLOYABLE: Include Docker, configuration, and deployment files
6. BE DOCUMENTED: Add comprehensive README, comments, and documentation

CRITICAL REQUIREMENTS:
- Return ONLY valid JSON with file paths and contents
- Do not include any explanations or markdown
- Ensure all code is syntactically correct
- Include proper error handling in all files
- Add environment configuration and setup instructions
- Follow the language/framework specific conventions

You are creating REAL, USABLE project templates that developers can immediately use."""
    
    def _parse_template_response(self, response: str) -> Dict[str, str]:
        """Parse LLM response into template dictionary"""
        
        # First, try to parse as pure JSON
        try:
            if isinstance(response, str):
                return json.loads(response)
            elif isinstance(response, dict):
                return response
        except json.JSONDecodeError:
            pass
        
        # If JSON parsing fails, try to extract from markdown code blocks
        return self._extract_template_from_markdown(response)
    
    def _extract_template_from_markdown(self, response: str) -> Dict[str, str]:
        """Extract template from markdown code blocks"""
        
        template = {}
        
        # Pattern to match code blocks with optional language and filename
        pattern = r'```(?:\w+)?\s*(?:{([^}]*)})?\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            filename_hint, code = match
            filename_hint = filename_hint.strip()
            code = code.strip()
            
            # Try to determine filename
            filename = self._infer_filename(filename_hint, code)
            if filename and code:
                template[filename] = code
        
        # If we found multiple files, return them
        if template:
            return template
        
        # Last resort: treat the entire response as a single file
        return {"main.py": response.strip()}
    
    def _infer_filename(self, filename_hint: str, code: str) -> str:
        """Infer filename from hints and code content"""
        
        if filename_hint:
            return filename_hint
        
        # Analyze code to guess file type
        if re.search(r'from flask|from fastapi|@app\.route', code):
            return "app.py"
        elif re.search(r'package\.json|require|import.*from', code) and 'react' in code.lower():
            return "App.jsx"
        elif re.search(r'public class|@SpringBootApplication', code):
            return "MainApplication.java"
        elif re.search(r'func main|package main', code):
            return "main.go"
        elif 'dockerfile' in code.lower() or 'FROM ' in code:
            return "Dockerfile"
        elif 'requirements' in code.lower() or code.strip().startswith('# requirements'):
            return "requirements.txt"
        elif 'package.json' in code.lower() or '"dependencies"' in code:
            return "package.json"
        
        return "main.py"  # Default fallback
    
    def _validate_and_enhance_template(
        self, 
        template: Dict[str, str], 
        language: str, 
        project_type: str
    ) -> Dict[str, str]:
        """Validate template and add missing essential files"""
        
        # Ensure we have essential files
        template = self._ensure_essential_files(template, language, project_type)
        
        # Validate code structure
        template = self._validate_code_quality(template, language)
        
        # Add missing configuration
        template = self._add_missing_configuration(template, language, project_type)
        
        return template
    
    def _ensure_essential_files(self, template: Dict[str, str], language: str, project_type: str) -> Dict[str, str]:
        """Ensure template has all essential files"""
        
        essential_files = self._get_essential_files(language, project_type)
        
        for file_path, default_content in essential_files.items():
            if file_path not in template:
                template[file_path] = default_content
        
        return template
    
    def _get_essential_files(self, language: str, project_type: str) -> Dict[str, str]:
        """Get default content for essential files"""
        
        base_files = {
            "README.md": "# Project\n\nGenerated project template\n\n## Setup\n\nInstructions here",
            ".gitignore": self._get_gitignore_content(language),
        }
        
        language_specific = {
            "python": {
                "requirements.txt": "# Project dependencies\n",
                "setup.py": "# Setup configuration\n",
            },
            "javascript": {
                "package.json": '{"name": "project", "version": "1.0.0"}',
            },
            "java": {
                "pom.xml": "<project>\n<!-- Maven configuration -->\n</project>",
            }
        }
        
        # Merge base files with language-specific files
        essential_files = base_files.copy()
        essential_files.update(language_specific.get(language, {}))
        
        return essential_files
    
    def _get_gitignore_content(self, language: str) -> str:
        """Get .gitignore content for language"""
        
        gitignores = {
            "python": """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/""",
            
            "javascript": """# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*""",
            
            "java": """# Compiled class file
*.class

# Log file
*.log"""
        }
        
        return gitignores.get(language, "# Project specific gitignore\n")
    
    def _validate_code_quality(self, template: Dict[str, str], language: str) -> Dict[str, str]:
        """Basic code quality validation"""
        
        for file_path, content in template.items():
            if self._is_code_file(file_path):
                # Add basic structure if missing
                if not self._has_basic_structure(content, language):
                    template[file_path] = self._add_basic_structure(content, language, file_path)
                
                # Ensure error handling
                if not self._has_error_handling(content, language):
                    template[file_path] = self._add_basic_error_handling(content, language)
        
        return template
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file"""
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.kt', '.go', '.rs', '.cpp', '.c', '.h'}
        return any(file_path.endswith(ext) for ext in code_extensions)
    
    def _has_basic_structure(self, content: str, language: str) -> bool:
        """Check if code has basic structure"""
        if language == "python":
            return "import" in content or "def " in content or "class " in content
        elif language == "javascript":
            return "import" in content or "function" in content or "const " in content
        elif language == "java":
            return "public class" in content or "import" in content
        return True  # For other languages, assume OK
    
    def _add_basic_structure(self, content: str, language: str, file_path: str) -> str:
        """Add basic structure to code"""
        
        if language == "python":
            return f'"""\n{file_path}\nGenerated file\n"""\n\n{content}'
        elif language == "javascript":
            return f"// {file_path}\n// Generated file\n\n{content}"
        elif language == "java":
            return f"// {file_path}\n// Generated file\n\n{content}"
        
        return content
    
    def _has_error_handling(self, content: str, language: str) -> bool:
        """Check if code has error handling"""
        error_patterns = {
            "python": ["try:", "except", "if .* is None", "if not "],
            "javascript": ["try{", "catch", "if.*=== null", "if.*=== undefined"],
            "java": ["try {", "catch", "if.*== null"],
        }
        
        patterns = error_patterns.get(language, [])
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)
    
    def _add_basic_error_handling(self, content: str, language: str) -> str:
        """Add basic error handling to code"""
        
        # This is a simplified version - in practice, you might want more sophisticated handling
        if language == "python" and "def " in content:
            # Add try-except to functions
            lines = content.split('\n')
            enhanced_lines = []
            for line in lines:
                enhanced_lines.append(line)
                if line.strip().startswith('def ') and not any(l.strip().startswith('try:') for l in enhanced_lines[-3:]):
                    enhanced_lines.append("    try:")
                    enhanced_lines.append("        # TODO: Implement function logic")
                    enhanced_lines.append("        pass")
                    enhanced_lines.append("    except Exception as e:")
                    enhanced_lines.append("        print(f\"Error: {e}\")")
                    enhanced_lines.append("        # Handle error appropriately")
            
            return '\n'.join(enhanced_lines)
        
        return content
    
    def _add_missing_configuration(self, template: Dict[str, str], language: str, project_type: str) -> Dict[str, str]:
        """Add missing configuration files"""
        
        config_files = {
            "docker": "Dockerfile",
            "compose": "docker-compose.yml", 
            "env": ".env.example",
        }
        
        # Add Dockerfile if not present and project type suggests it
        if project_type in ["web", "microservice", "api"] and "Dockerfile" not in template:
            template["Dockerfile"] = self._generate_dockerfile(language)
        
        return template
    
    def _generate_dockerfile(self, language: str) -> str:
        """Generate basic Dockerfile for language"""
        
        dockerfiles = {
            "python": """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]""",
            
            "javascript": """FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "start"]""",
            
            "java": """FROM openjdk:17-jdk-slim

WORKDIR /app

COPY . .

RUN ./mvnw package -DskipTests

CMD ["java", "-jar", "target/app.jar"]"""
        }
        
        return dockerfiles.get(language, f"# Dockerfile for {language}\n# Add appropriate configuration")
    
    def _get_fallback_template(self, language: str, project_type: str) -> Dict[str, str]:
        """Get fallback template when dynamic generation fails"""
        
        fallbacks = {
            "python": {
                "main.py": "#!/usr/bin/env python3\n\"\"\"\nGenerated Python Project\n\"\"\"\n\ndef main():\n    print(\"Hello World!\")\n\nif __name__ == \"__main__\":\n    main()",
                "requirements.txt": "# Add your dependencies here",
                "README.md": f"# {project_type.title()} Project\\n\\nGenerated Python project",
            },
            "javascript": {
                "index.js": "// Generated JavaScript Project\n\nconsole.log('Hello World!');",
                "package.json": '{"name": "project", "version": "1.0.0", "scripts": {"start": "node index.js"}}',
                "README.md": f"# {project_type.title()} Project\\n\\nGenerated JavaScript project",
            }
        }
        
        return fallbacks.get(language, {"main.txt": "Template generation failed. Please try again."})
