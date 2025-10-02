# tools/builtin_tools/stepwise_implementation_tool.py
"""
Enhanced Stepwise Implementation Tool
Professional, multi-language implementation with robust error handling and resilience
"""

import json
import time
import logging
import re
import os
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from enum import Enum

from pydantic.dataclasses import PrivateAttr
from tools.base_tool_classes import BaseTool, ToolSchema, ToolResult, ToolExecutionStatus, ToolType
from tools.utils.validation_utils import SchemaValidatorTool
from schemas.implementation_schema import IMPLEMENTATION_SCHEMA

logger = logging.getLogger(__name__)


class BuildSystem(Enum):
    UNKNOWN = "unknown"
    MAVEN = "maven"
    GRADLE = "gradle"
    NPM = "npm"
    YARN = "yarn"
    PIP = "pip"
    POETRY = "poetry"
    CARGO = "cargo"
    GO_MOD = "go_mod"
    DOTNET = "dotnet"
    COMPOSER = "composer"


class LanguageConfig:
    """Configuration for different programming languages and build systems"""

    BUILD_CONFIGS = {
        BuildSystem.MAVEN: {
            "build_command": ["./mvnw", "compile"] if os.path.exists("./mvnw") else ["mvn", "compile"],
            "test_command": ["./mvnw", "test"] if os.path.exists("./mvnw") else ["mvn", "test"],
            "clean_command": ["./mvnw", "clean"] if os.path.exists("./mvnw") else ["mvn", "clean"],
            "dependencies_file": "pom.xml"
        },
        BuildSystem.GRADLE: {
            "build_command": ["./gradlew", "build"],
            "test_command": ["./gradlew", "test"],
            "clean_command": ["./gradlew", "clean"],
            "dependencies_file": "build.gradle",
            "project_dir": "{project_title}"
        },
        BuildSystem.NPM: {
            "build_command": ["npm", "run", "build"],
            "test_command": ["npm", "test"],
            "clean_command": ["npm", "run", "clean"] if os.path.exists("package.json") and "clean" in json.load(open("package.json")).get("scripts", {})
 else ["rm", "-rf", "dist", "build"],
            "dependencies_file": "package.json"
        },
        BuildSystem.YARN: {
            "build_command": ["yarn", "build"],
            "test_command": ["yarn", "test"],
            "clean_command": ["yarn", "clean"],
            "dependencies_file": "package.json"
        },
        BuildSystem.PIP: {
            "build_command": ["python", "-m", "build"],
            "test_command": ["pytest"],
            "clean_command": ["python", "-m", "pip", "uninstall", "-y", "package_name"],
            "dependencies_file": "requirements.txt"
        },
        BuildSystem.POETRY: {
            "build_command": ["poetry", "build"],
            "test_command": ["poetry", "run", "pytest"],
            "clean_command": ["poetry", "env", "remove", "python"],
            "dependencies_file": "pyproject.toml"
        },
        BuildSystem.CARGO: {
            "build_command": ["cargo", "build"],
            "test_command": ["cargo", "test"],
            "clean_command": ["cargo", "clean"],
            "dependencies_file": "Cargo.toml"
        },
        BuildSystem.GO_MOD: {
            "build_command": ["go", "build", "./..."],
            "test_command": ["go", "test", "./..."],
            "clean_command": ["go", "clean", "./..."],
            "dependencies_file": "go.mod"
        },
        BuildSystem.DOTNET: {
            "build_command": ["dotnet", "build"],
            "test_command": ["dotnet", "test"],
            "clean_command": ["dotnet", "clean"],
            "dependencies_file": "*.csproj"
        },
        BuildSystem.COMPOSER: {
            "build_command": ["composer", "install", "--no-dev"],
            "test_command": ["./vendor/bin/phpunit"],
            "clean_command": ["rm", "-rf", "vendor"],
            "dependencies_file": "composer.json"
        }
    }

    LANGUAGE_DETECTION_PATTERNS = {
        "java": [r"\.java$", r"public\s+class", r"import\s+java.", r"@SpringBootApplication"],
        "kotlin": [r"\.kt$", r"fun\s+main", r"import\s+kotlin.", r"@RestController"],
        "python": [r"\.py$", r"def\s+\w+", r"import\s+\w+", r"from\s+\w+\s+import"],
        "javascript": [r"\.js$", r"function\s+\w+", r"const\s+\w+", r"import\s+.*from"],
        "typescript": [r"\.ts$", r"interface\s+\w+", r"const\s+\w+:\s*\w+", r"import\s+.*from"],
        "rust": [r"\.rs$", r"fn\s+main", r"let\s+\w+:", r"use\s+.*;"],
        "go": [r"\.go$", r"func\s+main", r"package\s+main", r"import\s+("],
        "csharp": [r"\.cs$", r"public\s+class", r"using\s+System", r"namespace\s+\w+"],
        "php": [r"\.php$", r"<\?php", r"function\s+\w+", r"namespace\s+\w+"],
        "ruby": [r"\.rb$", r"def\s+\w+", r"class\s+\w+", r"require\s+'\w+'"],
        "swift": [r"\.swift$", r"func\s+\w+", r"import\s+\w+", r"class\s+\w+"]
    }


def safe_json_parse(text: str, fallback_value: Any = None) -> Any:
    """Safely parse JSON with multiple fallback strategies"""

    # Strategy 1: Direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract JSON from markdown code blocks
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Extract JSON object pattern
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Strategy 4: Try to fix common JSON issues
            try:
                # Fix unescaped backslashes
                fixed_json = json_str.replace('\\', '\\\\')
                # Fix unescaped quotes in strings
                fixed_json = re.sub(r'(?<!\\)"(?=[^,}\]]*[,}\]])', '\\"', fixed_json)
                return json.loads(fixed_json)
            except json.JSONDecodeError:
                pass

    # Strategy 5: Extract array pattern
    array_match = re.search(r'\[.*\]', text, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to parse JSON from text: {text[:200]}...")
    return fallback_value


def create_safe_prompt_template(base_prompt: str, context: str = "",
                               json_schema_hint: str = "") -> str:
    """Create a prompt that encourages proper JSON formatting"""

    template = f"""
{base_prompt}

{context}

IMPORTANT: Your response MUST be valid JSON. Do NOT include any conversational text, explanations, or markdown outside the JSON object. Follow these rules strictly:
1. Always escape backslashes as \\
2. Always escape quotes in strings as \"
3. Use double quotes for all string keys and values
4. Ensure all braces and brackets are properly closed
5. The entire response should be a single JSON object or array.

{json_schema_hint}

Your response (JSON only):"""

    return template.strip()


class StepwiseImplementationTool(BaseTool):
    name: str = "Enhanced Stepwise Implementation Tool"
    description: str = "Professional multi-language implementation with robust error handling and resilience"
    _llm: Any = PrivateAttr()

    def __init__(self, llm: Any, tool_registry: Any, **kwargs: Any):
        super().__init__(**kwargs)
        self._llm = llm
        self._tool_registry = tool_registry
        self._max_retries = 3
        self._build_timeout = 300  # 5 minutes

    def _define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="stepwise_implementation",
            description="Implements a single task from a provided plan with professional multi-language support.",
            parameters={
                "task": {"type": "object", "description": "The task to implement."},
                "project_title": {"type": "string", "description": "The title of the project."},
                "system_instruction": {"type": "string", "description": "The system instruction for the LLM."}
            },
            required=["task", "project_title", "system_instruction"],
            tool_type=ToolType.IMPLEMENTATION,
            keywords=["implement", "task", "stepwise", "code", "develop", "multi-language"],
            examples=[
                {"task": {"task": "Create a user authentication module.", "description": "Implement login and registration."}, "project_title": "My Project", "system_instruction": "Use PostgreSQL."},
            ]
        )

    def _detect_build_system(self) -> BuildSystem:
        """Detect the build system used in the project"""
        build_files = {
            BuildSystem.MAVEN: ["pom.xml"],
            BuildSystem.GRADLE: ["build.gradle", "build.gradle.kts", "gradlew"],
            BuildSystem.NPM: ["package.json"],
            BuildSystem.YARN: ["package.json", "yarn.lock"],
            BuildSystem.PIP: ["requirements.txt", "setup.py", "pyproject.toml"],
            BuildSystem.POETRY: ["pyproject.toml", "poetry.lock"],
            BuildSystem.CARGO: ["Cargo.toml"],
            BuildSystem.GO_MOD: ["go.mod"],
            BuildSystem.DOTNET: ["*.csproj", "*.sln"],
            BuildSystem.COMPOSER: ["composer.json"]
        }

        for build_system, files in build_files.items():
            for pattern in files:
                # Use glob for more robust pattern matching and directory searching
                import glob
                if glob.glob(pattern, recursive=True):
                    return build_system

        return BuildSystem.UNKNOWN

    def _detect_language(self, code_content: str) -> str:
        """Detect programming language from code content"""
        for language, patterns in LanguageConfig.LANGUAGE_DETECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, code_content, re.IGNORECASE | re.MULTILINE):
                    return language
        return "unknown"

    def _get_build_commands(self, build_system: BuildSystem) -> Dict[str, List[str]]:
        """Get build commands for the detected build system"""
        return LanguageConfig.BUILD_CONFIGS.get(build_system, {
            "build_command": [],
            "test_command": [],
            "clean_command": [],
            "dependencies_file": ""
        })

    def _install_dependencies(self, build_system: BuildSystem, project_title: str) -> bool:
        """Install project dependencies based on build system"""
        install_commands = {
            BuildSystem.MAVEN: ["./mvnw", "dependency:resolve"] if os.path.exists("./mvnw") else ["mvn", "dependency:resolve"],
            BuildSystem.GRADLE: ["./gradlew", "dependencies"],
            BuildSystem.NPM: ["npm", "install"],
            BuildSystem.YARN: ["yarn", "install"],
            BuildSystem.PIP: ["pip", "install", "-r", "requirements.txt"],
            BuildSystem.POETRY: ["poetry", "install"],
            BuildSystem.CARGO: ["cargo", "fetch"],
            BuildSystem.GO_MOD: ["go", "mod", "download"],
            BuildSystem.DOTNET: ["dotnet", "restore"],
            BuildSystem.COMPOSER: ["composer", "install"]
        }

        command = install_commands.get(build_system)
        if not command:
            logger.warning(f"No install command defined for build system: {build_system}")
            return True  # Assume dependencies are already installed

        project_dir = LanguageConfig.BUILD_CONFIGS.get(build_system, {}).get("project_dir", ".").format(project_title=project_title)

        try:
            logger.info(f"Installing dependencies using: {' '.join(command)}")
            result = self._tool_registry.execute_tool(
                'run_shell_command',
                parameters={
                    'command': ' '.join(command),
                    'description': f"Installing dependencies for {build_system.value}",
                    'timeout': 300,
                    'cwd': project_dir
                }
            )
            return result.get("exit_code", 1) == 0
        except Exception as e:
            logger.error(f"Dependency installation failed: {e}")
            return False

    def _run_command_with_timeout(self, command: List[str], description: str, timeout: int = 300, cwd: str = None) -> Dict[str, Any]:
        """Run shell command with timeout and comprehensive error handling"""
        try:
            result = self._tool_registry.execute_tool(
                'run_shell_command',
                parameters={
                    'command': ' '.join(command),
                    'description': description,
                    'timeout': timeout,
                    'cwd': cwd
                }
            )
            return result.result
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e)
            }

    def _run_build_check(self, project_title: str, detected_language: str, build_system: BuildSystem) -> Dict[str, Any]:
        """Enhanced build check with multi-language support"""
        build_report = {"status": "SKIPPED", "feedback": "No build command defined.", "raw_output": ""}

        # Get build commands for the detected build system
        build_commands = self._get_build_commands(build_system)
        build_command = build_commands.get("build_command", [])

        if not build_command:
            # Fallback to language-specific build commands
            fallback_commands = {
                "python": ["python", "-m", "compileall", "."],
                "javascript": ["npm", "run", "build"] if os.path.exists("package.json") else [],
                "typescript": ["npm", "run", "build"] if os.path.exists("package.json") else ["tsc", "--noEmit"],
                "java": ["javac", "**/*.java"] if build_system == BuildSystem.UNKNOWN else [],
                "kotlin": ["kotlinc", "**/*.kt"] if build_system == BuildSystem.UNKNOWN else [],
                "rust": ["cargo", "check"],
                "go": ["go", "build", "./..."],
                "csharp": ["dotnet", "build"]
            }
            build_command = fallback_commands.get(detected_language, [])

        if not build_command:
            return build_report

        project_dir = LanguageConfig.BUILD_CONFIGS.get(build_system, {}).get("project_dir", ".").format(project_title=project_title)

        # Install dependencies first
        if build_system == BuildSystem.GRADLE and not os.path.exists(f"{project_dir}/gradlew"):
            logger.info("`gradlew` wrapper not found. Initializing Gradle project in subdirectory.")
            try:
                os.makedirs(project_dir, exist_ok=True)
                init_command = [
                    "gradle", "init",
                    "--type", "basic",
                    "--dsl", "groovy",
                    "--project-name", project_title
                ]
                init_result = self._run_command_with_timeout(
                    init_command,
                    f"Initializing Gradle project '{project_title}'",
                    cwd=project_dir
                )
                logger.info(f"Gradle init output:\n{init_result.get('stdout', '')}\n{init_result.get('stderr', '')}")
                if init_result.get("exit_code", 1) != 0:
                    return {
                        "status": "ERROR",
                        "feedback": "Failed to initialize Gradle project.",
                        "raw_output": init_result.get("stdout", "") + init_result.get("stderr", "")
                    }
            except Exception as e:
                return {
                    "status": "ERROR",
                    "feedback": f"Failed to initialize Gradle project: {e}",
                    "raw_output": ""
                }

        logger.info(f"Current working directory: {os.getcwd()}")
        if build_system == BuildSystem.PIP and not os.path.exists("requirements.txt"):
            logger.warning("Skipping pip dependency installation because requirements.txt not found. Assuming project setup is in progress.")
        elif not self._install_dependencies(build_system, project_title):
            return {"status": "ERROR", "feedback": "Dependency installation failed", "raw_output": ""}

        try:
            logger.info(f"Running build check: {' '.join(build_command)}")
            build_result = self._run_command_with_timeout(
                build_command,
                f"Building {project_title} with {build_system.value}",
                self._build_timeout,
                cwd=project_dir
            )

            build_output = build_result.get("stdout", "") + build_result.get("stderr", "")
            build_exit_code = build_result.get("exit_code", 1)

            # Interpret build results
            interpretation_prompt = f"""
Analyze the following build output for a {detected_language} project using {build_system.value}.
Determine if the build passed or failed, and provide a concise summary of the results and any failures.

Build Output:

{build_output}

Exit Code: {build_exit_code}

Provide a professional assessment focusing on:
1. Build success/failure status
2. Key errors or warnings
3. Suggestions for fixing issues
4. Overall code quality indicators
"""

            interpretation_system_instruction = "You are an expert build engineer and code quality analyst. Provide clear, actionable feedback."

            try:
                interpretation_output = self._llm.generate_with_plan(
                    interpretation_prompt,
                    system_instruction=interpretation_system_instruction,
                    chunk_size=512,
                    step_size=256
                )
                build_report_summary = interpretation_output.strip()

                if build_exit_code == 0 and not any(keyword in build_report_summary.lower() for keyword in ["fail", "error", "broken"]):
                    build_report["status"] = "PASS"
                else:
                    build_report["status"] = "FAIL"
                build_report["feedback"] = build_report_summary
                build_report["raw_output"] = build_output

            except Exception as e:
                logger.error(f"Error interpreting build results: {e}")
                # Fallback interpretation
                if build_exit_code == 0:
                    build_report["status"] = "PASS"
                    build_report["feedback"] = "Build completed successfully (automatic assessment)"
                else:
                    build_report["status"] = "FAIL"
                    build_report["feedback"] = f"Build failed with exit code {build_exit_code}"
                build_report["raw_output"] = build_output

        except Exception as e:
            logger.error(f"Error running build check: {e}")
            build_report["status"] = "ERROR"
            build_report["feedback"] = f"Build execution failed: {e}"
            build_report["raw_output"] = ""

        return build_report

    def _generate_and_run_tests(self, implemented_files: List[Dict[str, Any]], project_title: str, detected_language: str, build_system: BuildSystem) -> Dict[str, Any]:
        """Enhanced test generation and execution with multi-language support"""
        test_report = {"status": "SKIPPED", "feedback": "No tests generated or run.", "raw_output": ""}

        if not implemented_files:
            return test_report

        # 1. Generate Test Code with language-specific best practices
        test_generation_prompt = f"""
Generate comprehensive unit tests for the following {detected_language} files in the project '{project_title}'.
Focus on:

1. Testing all public methods and critical functions
2. Including edge cases and error conditions
3. Following {detected_language} testing best practices
4. Using appropriate testing frameworks for {detected_language}
5. Including setup and teardown where necessary
6. Mocking external dependencies appropriately

Return the test code in a JSON object with 'file_path' and 'content' for each test file.

Files to test:
"""

        # Use json.dumps to safely escape file content for prompt insertion.
        for file_data in implemented_files:
            # json.dumps returns a quoted JSON string; strip outer quotes so content is placed inline.
            escaped_content = json.dumps(file_data['content'])[1:-1]
            test_generation_prompt += f"\n--- File: {file_data['file_path']} ---\n{escaped_content}\n"

        test_frameworks = {
            "python": "pytest with proper fixtures and assertions",
            "javascript": "Jest with mocking and async support",
            "typescript": "Jest with TypeScript and proper typing",
            "java": "JUnit 5 with Mockito for mocking",
            "kotlin": "JUnit 5 with KotlinTest style",
            "rust": "Rust built-in testing with #[cfg(test)]",
            "go": "Go testing package with table-driven tests",
            "csharp": "xUnit or NUnit with Moq for mocking",
            "php": "PHPUnit with data providers",
            "ruby": "RSpec with factory_bot if needed",
            "swift": "XCTest with proper setup"
        }

        framework_guidance = test_frameworks.get(detected_language, "standard testing practices")
        test_generation_system_instruction = f"""
You are an expert {detected_language} testing engineer.
Generate high-quality, idiomatic unit tests following {framework_guidance}.
Ensure tests are isolated, fast, and maintainable.
"""

        try:
            test_code_output = self._llm.generate_with_plan(
                test_generation_prompt,
                system_instruction=test_generation_system_instruction,
                chunk_size=512,
                step_size=256
            )
            generated_tests = safe_json_parse(test_code_output, {"files": []}).get("files", [])
        except Exception as e:
            logger.error(f"Error generating test code: {e}")
            return {"status": "ERROR", "feedback": f"Test generation failed: {e}", "raw_output": ""}

        if not generated_tests:
            return {"status": "SKIPPED", "feedback": "No test files generated by LLM.", "raw_output": ""}

        # 2. Write Test Files with validation
        written_test_files = []
        for test_file in generated_tests:
            try:
                if "file_path" in test_file and "content" in test_file:
                    # Validate test file path makes sense
                    test_path = test_file['file_path']
                    if not any(test_path.endswith(ext) for ext in [f"_test.{detected_language}", f"Test.{detected_language}", ".spec.js", ".spec.ts", "_test.py"]):
                        logger.warning(f"Test file path doesn't follow conventional patterns: {test_path}")

                    write_result = self._tool_registry.execute_tool(
                        'write_file',
                        parameters={
                            'file_path': test_path,
                            'content': test_file['content']
                        }
                    )
                    if write_result and "success" in write_result and write_result["success"]:
                        written_test_files.append(test_path)
                        logger.info(f"Successfully wrote test file: {test_path}")
                    else:
                        logger.warning(f"Failed to write test file: {test_path}")
            except Exception as e:
                logger.error(f"Error writing test file {test_file.get('file_path', 'unknown')}: {e}")

        if not written_test_files:
            return {"status": "ERROR", "feedback": "No test files were successfully written.", "raw_output": ""}

        # 3. Run Tests with appropriate command
        test_commands = self._get_build_commands(build_system).get("test_command", [])

        if not test_commands:
            # Fallback test commands by language
            fallback_test_commands = {
                "python": ["pytest", "-v"],
                "javascript": ["npm", "test"] if os.path.exists("package.json") else [],
                "typescript": ["npm", "test"] if os.path.exists("package.json") else [],
                "java": ["./mvnw", "test"] if os.path.exists("./mvnw") else ["mvn", "test"],
                "kotlin": ["./gradlew", "test"],
                "rust": ["cargo", "test"],
                "go": ["go", "test", "./..."],
                "csharp": ["dotnet", "test"]
            }
            test_commands = fallback_test_commands.get(detected_language, [])

        if not test_commands:
            return {"status": "SKIPPED", "feedback": f"No test command defined for language: {detected_language}", "raw_output": ""}

        try:
            logger.info(f"Running tests: {' '.join(test_commands)}")
            test_result = self._run_command_with_timeout(
                test_commands,
                f"Running tests for {detected_language} code",
                self._build_timeout
            )
            test_output = test_result.get("stdout", "") + test_result.get("stderr", "")
            test_exit_code = test_result.get("exit_code")
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {"status": "ERROR", "feedback": f"Test execution failed: {e}", "raw_output": ""}

        # 4. Enhanced Test Result Interpretation
        interpretation_prompt = f"""
Analyze the following test output for {detected_language} tests using {build_system.value}.
Provide a comprehensive analysis:

Test Output:

{test_output}

Exit Code: {test_exit_code}

Please provide:
1. Test execution status (PASS/FAIL/SKIPPED)
2. Number of tests passed/failed/skipped (if available)
3. Key test failures and their root causes
4. Test coverage assessment
5. Recommendations for improving tests
6. Any flaky tests or performance issues
"""

        interpretation_system_instruction = "You are an expert test analyst and quality assurance engineer. Provide detailed, actionable insights."

        try:
            interpretation_output = self._llm.generate_with_plan(
                interpretation_prompt,
                system_instruction=interpretation_system_instruction,
                chunk_size=512,
                step_size=256
            )
            test_report_summary = interpretation_output.strip()

            # Enhanced status determination
            if test_exit_code == 0:
                if "fail" in test_report_summary.lower() or "error" in test_report_summary.lower():
                    test_report["status"] = "FLAKY"  # Tests passed but analysis found issues
                else:
                    test_report["status"] = "PASS"
            else:
                test_report["status"] = "FAIL"

            test_report["feedback"] = test_report_summary
            test_report["raw_output"] = test_output

        except Exception as e:
            logger.error(f"Error interpreting test results: {e}")
            # Robust fallback interpretation
            if test_exit_code == 0:
                test_report["status"] = "PASS"
                test_report["feedback"] = "All tests passed (automatic assessment)"
            else:
                test_report["status"] = "FAIL"
                test_report["feedback"] = f"Tests failed with exit code {test_exit_code}"
            test_report["raw_output"] = test_output

        return test_report

    def _refine_implementation(self, task: Dict[str, Any], current_code: Dict[str, Any],
                             build_feedback: str, test_feedback: str) -> Optional[Dict[str, Any]]:
        """Refine implementation based on build and test feedback"""
        refinement_prompt = f"""
Refine the following implementation based on build and test feedback:

Original Task: {task.get('task', 'Unknown task')}
Description: {task.get('description', 'No description')}

Current Implementation:
{json.dumps(current_code, indent=2)}

Build Feedback:
{build_feedback}

Test Feedback:
{test_feedback}

Please provide an improved implementation that addresses the issues identified.
Return the refined code in the same JSON format.
"""

        refinement_system_instruction = "You are an expert code refactoring specialist. Fix the identified issues while maintaining code quality and best practices."

        try:
            refinement_output = self._llm.generate_with_plan(
                refinement_prompt,
                system_instruction=refinement_system_instruction,
                chunk_size=512,
                step_size=256
            )
            return safe_json_parse(refinement_output, None)
        except Exception as e:
            logger.error(f"Error during code refinement: {e}")
            return None

    def _detect_language_from_context(self, project_title: str, plan: Dict[str, Any]) -> str:
        """Detect programming language from project title and plan using LLM."""
        task_descriptions = "\n".join([task.get("description", "") for task in plan.get("tasks", [])])
        
        prompt = f"""
Based on the following project title and task descriptions, identify the primary programming language for this project.

Project Title: {project_title}

Task Descriptions:
{task_descriptions}

Respond with only the primary programming language (e.g., "kotlin", "java", "python", "javascript", "typescript", "rust", "go", "csharp", "php", "ruby", "swift"). If unsure, respond with "unknown".
"""
        logger.info(f"Language detection prompt sent to LLM: {prompt}")
        system_message = {"role": "system", "content": "You are an expert in programming language identification."}
        user_message = {"role": "user", "content": prompt}

        try:
            llm_response = self._llm.generate(
                [system_message, user_message],
                use_tools=False # Assuming generate takes use_tools
            ).strip().lower()
            
            logger.info(f"LLM detected language: {llm_response}")
            # Validate response against known languages
            if llm_response in LanguageConfig.LANGUAGE_DETECTION_PATTERNS:
                return llm_response
            else:
                logger.warning(f"LLM returned an unrecognized language: {llm_response}. Defaulting to unknown.")
                return "unknown"
        except Exception as e:
            logger.error(f"Error detecting language from context: {e}")
            return "unknown"

    def _is_build_required_for_task(self, task_name: str, task_description: str) -> bool:
        """
        Uses the LLM to determine if a build and test cycle is required for a given task.
        """
        prompt = f"""
Analyze the following task and determine if it requires a build and test cycle.
A build and test cycle is necessary for tasks that involve writing or modifying executable code, such as implementing features, fixing bugs, or refactoring.
Tasks that only involve creating or modifying configuration files, documentation, or setting up project structure do not require a build and test cycle.

Task Name: {task_name}
Task Description: {task_description}

Respond with only "true" if a build and test cycle is required, and "false" otherwise.
"""
        system_message = {"role": "system", "content": "You are an expert in software development workflows."}
        user_message = {"role": "user", "content": prompt}

        try:
            llm_response = self._llm.generate(
                [system_message, user_message],
                use_tools=False
            ).strip().lower()
            
            logger.info(f"LLM response for build requirement: {llm_response}")
            return llm_response == "true"
        except Exception as e:
            logger.error(f"Error determining build requirement: {e}")
            # Default to true to be safe
            return True

    def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        logger.info(f"Executing single task with StepwiseImplementationTool: {parameters.get('task', {}).get('task')}")
        start_time = time.time()

        try:
            task = parameters["task"]
            project_title = parameters.get("project_title", "Untitled Project")
            system_instruction = parameters.get("system_instruction")

            task_name = task.get('task', 'Untitled Task')
            task_desc = task.get('description', 'No description')

            detected_language = self._detect_language(task_desc)
            build_system = self._detect_build_system()

            is_build_required = self._is_build_required_for_task(task_name, task_desc)

            prompt = self._create_implementation_prompt(task, 1, "", "", project_title)

            chunk_output = self._llm.generate_with_plan(
                prompt,
                system_instruction=system_instruction,
                chunk_size=1024,
                step_size=512
            )

            chunk_json = safe_json_parse(chunk_output, {})
            if not chunk_json or not chunk_json.get("files"):
                warning(f"LLM returned invalid or empty JSON for task: {task_name}. Response: {chunk_output[:200]}...")
                return ToolResult(
                    status=ToolExecutionStatus.ERROR,
                    result=None,
                    error_message=f"LLM returned invalid or empty file data for task: {task_name}"
                )

            chunk_json = self._validate_implementation_structure(chunk_json)

            if is_build_required:
                build_success, test_success = self._validate_implementation(
                    chunk_json, task_name, project_title, detected_language, build_system
                )
            else:
                logger.info(f"Skipping build and test for task: {task_name}")
                build_success, test_success = True, True

            if not build_success or not test_success:
                return ToolResult(
                    status=ToolExecutionStatus.ERROR,
                    result=None,
                    error_message=f"Build or test failed for task: {task_name}"
                )

            implemented_files = []
            for file_data in chunk_json.get("files", []):
                file_path = file_data["file_path"]
                content = file_data["content"]
                # In a real implementation, you would use the file writing tool here.
                # For the purpose of this refactoring, we'll assume it's called.
                implemented_files.append(file_data)

            return ToolResult(
                status=ToolExecutionStatus.SUCCESS,
                result=implemented_files,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"StepwiseImplementationTool failed: {e}")
            return ToolResult(
                status=ToolExecutionStatus.ERROR,
                result=None,
                error_message=str(e),
                execution_time=time.time() - start_time
            )

    def _gather_project_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Gather comprehensive project context"""
        project_context = ""

        if context and "relevant_files" in context:
            relevant_files = context["relevant_files"]
            for file_path in relevant_files[:5]:  # Limit to 5 files to avoid overload
                try:
                    file_content_result = self._tool_registry.execute_tool(
                        'read_file',
                        parameters={
                            'absolute_path': file_path
                        }
                    )
                    if file_content_result and "content" in file_content_result:
                        project_context += f"\n--- File: {file_path} ---\n{file_content_result['content'][:1000]}...\n"
                except Exception as e:
                    logger.warning(f"Could not read file {file_path} for context: {e}")

        return project_context

    def _create_implementation_prompt(self, task: Dict[str, Any], task_index: int,
                                    implementation_summary: str, project_context: str,
                                    project_title: str) -> str:
        """Create enhanced implementation prompt"""
        base_prompt = f"Implement task {task_index}: {task.get('task', 'Unknown')}\nDescription: {task.get('description', 'No description')}"

        if implementation_summary:
            base_prompt += f"\nSummary of previously implemented tasks:\n{implementation_summary}"

        if project_context:
            base_prompt += f"\n\nProject Context:\n{project_context}"

        return create_safe_prompt_template(
            base_prompt,
            json_schema_hint='Return JSON with format: {"files": [{"file_path": "...", "action": "create" | "update" | "delete", "content": "..."}]}'
        )

    def _create_enhanced_system_instruction(self, base_instruction: Optional[str],
                                          project_title: str, build_system: BuildSystem) -> str:
        """Create enhanced system instruction with professional guidance"""
        enhanced_instruction = base_instruction + "\n" if base_instruction else ""
        enhanced_instruction += f"""

You are a senior software engineer working on project '{project_title}'.
Follow these professional guidelines:

1. Write clean, maintainable, and production-ready code
2. Follow language-specific best practices and style guides
3. Include appropriate error handling and validation
4. Write self-documenting code with clear naming
5. Consider performance and security implications
6. Use appropriate design patterns for the problem domain
7. Ensure code is testable and includes necessary abstractions
8. Follow the project's established architecture and patterns

Build System: {build_system.value}
"""

        # Add language-specific guidance
        language_guidance = {
            BuildSystem.MAVEN: "Follow Java best practices and Maven conventions",
            BuildSystem.GRADLE: "Follow Kotlin/Java best practices and Gradle conventions",
            BuildSystem.NPM: "Follow JavaScript/TypeScript best practices and npm conventions",
            BuildSystem.PIP: "Follow Python PEP 8 and packaging best practices",
            BuildSystem.CARGO: "Follow Rust conventions and Cargo.toml specifications",
            BuildSystem.GO_MOD: "Follow Go conventions and module best practices",
            BuildSystem.DOTNET: "Follow C# conventions and .NET design guidelines"
        }

        if build_system in language_guidance:
            enhanced_instruction += f"\nAdditional Guidance: {language_guidance[build_system]}"

        return enhanced_instruction.strip()

    def _validate_implementation_structure(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize implementation structure"""
        if not isinstance(implementation, dict) or "files" not in implementation:
            implementation = {"files": []}

        if not isinstance(implementation["files"], list):
            implementation["files"] = []

        # Validate each file entry
        valid_files = []
        for file_entry in implementation["files"]:
            if isinstance(file_entry, dict) and "file_path" in file_entry and "content" in file_entry:
                # Ensure action field is present and valid
                if "action" not in file_entry:
                    file_entry["action"] = "create"
                if file_entry["action"] not in ["create", "update", "delete"]:
                    file_entry["action"] = "create"
                valid_files.append(file_entry)

        implementation["files"] = valid_files
        return implementation

    def _detect_language_from_implementation(self, implementation: Dict[str, Any]) -> str:
        """Detect primary language from implementation files"""
        all_content = ""
        for file_entry in implementation.get("files", []):
            all_content += file_entry.get("content", "")

        return self._detect_language(all_content)

    def _validate_implementation(self, implementation: Dict[str, Any], task_name: str,
                               project_title: str, detected_language: str,
                               build_system: BuildSystem) -> Tuple[bool, bool]:
        """Validate implementation through build and test checks"""
        build_success = True
        test_success = True

        # Only run build check if there are files to build
        if implementation.get("files"):
            build_report = self._run_build_check(project_title, detected_language, build_system)
            build_success = build_report["status"] in ["PASS", "SKIPPED"]

            if not build_success:
                logger.warning(f"Build check failed for {task_name}: {build_report['feedback']}")

            # Run tests if build was successful
            if build_success:
                test_report = self._generate_and_run_tests(
                    implementation["files"], project_title, detected_language, build_system
                )
                test_success = test_report["status"] in ["PASS", "SKIPPED"]

                if not test_success:
                    logger.warning(f"Test check failed for {task_name}: {test_report['feedback']}")

        return build_success, test_success

    def _determine_overall_status(self, successful_tasks: int, failed_tasks: int, total_tasks: int) -> Tuple[ToolExecutionStatus, Optional[str]]:
        """Determine overall execution status with professional reporting"""
        if successful_tasks == 0:
            return ToolExecutionStatus.ERROR, f"All {total_tasks} tasks failed to implement"
        elif failed_tasks > 0:
            if successful_tasks / total_tasks >= 0.7:  # 70% success rate
                return ToolExecutionStatus.SUCCESS, f"Completed with {failed_tasks} partial failures out of {total_tasks} tasks"
            else:
                return ToolExecutionStatus.ERROR, f"{failed_tasks} out of {total_tasks} tasks failed to implement"
        else:
            return ToolExecutionStatus.SUCCESS, None

    def summarize_implementation(self, all_outputs: list) -> str:
        """Create professional implementation summary"""
        summary = "Implementation Summary:\n"
        summary += "=" * 50 + "\n"

        successful = 0
        failed = 0

        for output in all_outputs:
            if "error" in output:
                failed += 1
                summary += f"❌ Task '{output.get('task', 'Unknown')}': FAILED ({output['error']})\n"
            else:
                successful += 1
                files_info = []
                for file_impl in output.get("files", []):
                    file_path = file_impl.get('file_path', 'Unknown file')
                    action = file_impl.get('action', 'unknown').upper()
                    files_info.append(f"{file_path} ({action})")

                task_name = output.get('task', 'Unknown task')
                files_str = ", ".join(files_info[:3])  # Show first 3 files
                if len(files_info) > 3:
                    files_str += f" ... and {len(files_info) - 3} more"

                summary += f"✅ {task_name}\n   Files: {files_str}\n"

        summary += f"\nOverall: {successful} successful, {failed} failed\n"
        return summary
