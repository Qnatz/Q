import logging
from typing import Optional
from datetime import datetime

from core.state_manager import StateManager
from core.project_context import ProjectContext
from core.llm_service import LLMService
from core.agent_manager import AgentManager
from core.response_handler import ResponseHandler

from core.context_builder import ContextBuilder
from core.git_service import GitService
from core.template_service import DynamicTemplateService

from core.ide_server import IDEServer
from core.router import Router

from agent_processes.ideation_module import IdeationModule
from agent_processes.planning_module import PlanningModule
from agent_processes.programming_module import ProgrammingModule
from agent_processes.qa_module import QAModule
from agent_processes.review_module import ReviewModule
from agent_processes.research_module import ResearchModule
from agent_processes.code_assist_module import CodeAssistModule
from core.ui import agent_log
from utils.ui_helpers import say_system, say_error, say_success

logger = logging.getLogger(__name__)

class WorkflowManager:
    def __init__(self, planner, manager, programmer, qa, reviewer, state_manager):
        self.planner = planner
        self.manager = manager
        self.programmer = programmer
        self.qa = qa
        self.reviewer = reviewer
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)

    def execute_workflow(self, response_dict: dict):
        """
        Execute the complete development workflow with all specialized agents.
        
        Args:
            response_dict: Build response containing project specifications
        """
        project_title = response_dict.get("project_title", "Untitled Project")
        refined_prompt = response_dict.get("refined_prompt", "")
        project_id = response_dict.get("project_id")

        say_system(f"🚀 Building: {project_title}")
        agent_log("Orchestrator", f"Starting build for '{project_title}'...")
        
        try:
            # Get state and project-specific history
            state = self.state_manager.get_conversation_state("default_user", project_id)
            current_project_id = state.get("current_project_id")
            
            # Get project history safely
            project_history = []
            try:
                if hasattr(self.state_manager.unified_memory, 'tinydb'):
                    tinydb = self.state_manager.unified_memory.tinydb
                    if hasattr(tinydb, 'get_conversation_history'):
                        project_history = tinydb.get_conversation_history(
                            user_id="default_user",
                            project_id=current_project_id
                        )
            except Exception as e:
                logger.warning(f"Could not retrieve project history: {e}")

            # Phase 1: Planning
            agent_log("Planner", "Generating comprehensive plan...")
            plan = self.planner.generate_plan(project_title, refined_prompt, project_history)
            
            if not plan:
                self.logger.warning("No plan generated, creating fallback plan")
                say_error("Planning failed, using simplified approach")
                plan = self._create_fallback_plan(project_title, refined_prompt)
            else:
                # Validate plan
                try:
                    from schemas.plan_schema import PLAN_SCHEMA
                    from utils.validation_utils import validate_plan
                    validate_plan(plan)
                    agent_log("Planner", "Plan validated successfully")
                except Exception as e:
                    self.logger.warning(f"Plan failed schema validation but will be used: {e}")
            
            # Update project metadata after planning
            self._update_project_phase(
                current_project_id, 
                plan=plan,
                status="planning_complete",
                completion_rate=0.25
            )
            agent_log("Planner", "Comprehensive plan generated successfully.")

            # Phase 2: Management Review
            agent_log("Manager", "Reviewing plan...")
            approval = self.manager.review_plan(plan)
            if not approval.get("approved", False):
                feedback = approval.get('feedback', 'No feedback provided')
                say_error(f"Manager rejected plan: {feedback}. Aborting workflow.")
                return None
            agent_log("Manager", "Plan approved and validated.")

            # Phase 3: Implementation
            agent_log("Programmer", "Starting implementation...")
            self._update_module_status(state, project_id, "programmer", "running")
            self._update_project_phase(
                current_project_id,
                status="programming",
                completion_rate=0.50
            )

            project_title_from_plan = plan.get("project", {}).get("name", project_title)
            implemented_files_generator = self.programmer.implement(
                plan, 
                project_title_from_plan, 
                "default_user", 
                project_id
            )
            
            all_implemented_files = []
            successful_tasks_count = 0
            failed_tasks_count = 0

            for item in implemented_files_generator:
                if item.get("type") == "task_complete":
                    successful_tasks_count += 1
                    if item.get("files"):
                        all_implemented_files.extend(item["files"])
                elif item.get("type") == "task_error":
                    failed_tasks_count += 1
                # You might want to log other types of items if they exist

            self._update_module_status(state, project_id, "programmer", "idle")
            
            if failed_tasks_count == 0:
                agent_log("Programmer", f"Successfully implemented {successful_tasks_count} tasks, creating {len(all_implemented_files)} files.")
                workflow_status = "complete"
            elif successful_tasks_count > 0:
                agent_log("Programmer", f"Partially implemented {successful_tasks_count} tasks, with {failed_tasks_count} failures. Created {len(all_implemented_files)} files.")
                workflow_status = "partial_success"
            else:
                agent_log("Programmer", f"Failed to implement any tasks. {failed_tasks_count} failures.")
                workflow_status = "failed"

            implemented_files = all_implemented_files # Update implemented_files for QA and Review

            # Phase 4: Quality Assurance
            agent_log("QA", "Running quality assurance...")
            self._update_project_phase(
                current_project_id,
                status="qa",
                completion_rate=0.75
            )
            
            qa_report_path = self.qa.test(implemented_files, plan=plan, project_id=current_project_id)
            agent_log("QA", f"Quality assurance completed: {qa_report_path}")

            # Phase 5: Code Review
            agent_log("Reviewer", "Conducting code review...")
            self._update_project_phase(
                current_project_id,
                status="review",
                completion_rate=0.90
            )
            
            review_report_path = self.reviewer.review(implemented_files, project_id=current_project_id)
            agent_log("Reviewer", f"Code review completed: {review_report_path}")

            # Final: Mark as complete
            self._update_project_phase(
                current_project_id,
                status="complete",
                completion_rate=1.0
            )

        except Exception as e:
            say_error(f"Workflow execution failed: {e}")
            self.logger.error(f"Workflow error: {str(e)}", exc_info=True)
            
            # Update project status to failed
            if current_project_id:
                try:
                    self._update_project_phase(
                        current_project_id,
                        status="failed",
                        completion_rate=None
                    )
                except Exception as update_error:
                    logger.error(f"Failed to update project status: {update_error}")
            
            return None

        if workflow_status == "complete":
            say_success(f"✅ {project_title} has been built successfully!")
        elif workflow_status == "partial_success":
            say_system(f"⚠️ {project_title} built with some failures. Check logs for details.")
        else:
            say_error(f"❌ {project_title} build failed.")
        
        say_system("📁 Project files can be found in the 'projects' directory.")
        return implemented_files

    def _create_fallback_plan(self, project_title: str, refined_prompt: str) -> dict:
        """Create a simple fallback plan when planning fails"""
        return {
            "project": {
                "name": project_title,
                "description": refined_prompt
            },
            "files": [],
            "tasks": [
                {
                    "task": "Implement based on user request",
                    "description": f"Implement: {refined_prompt}",
                    "module": "ProgrammingModule",
                    "output": "Working implementation"
                }
            ]
        }

    def _update_module_status(self, state, project_id, module_name: str, status: str):
        """Update module status safely"""
        try:
            state.module_status[module_name] = status
            self.state_manager.update_conversation_state("default_user", state, project_id)
        except Exception as e:
            logger.error(f"Failed to update module status: {e}")

    def _update_project_phase(
        self, 
        project_id: Optional[str], 
        plan: dict = None,
        status: str = None, 
        completion_rate: float = None
    ):
        """Update project metadata for current phase"""
        if not project_id:
            return
        
        try:
            project_metadata = self.state_manager.unified_memory.get_project_metadata(project_id)
            
            if not project_metadata:
                logger.warning(f"No metadata found for project {project_id}")
                return
            
            # Update fields if provided
            if plan is not None:
                project_metadata['plan'] = plan
            if status is not None:
                project_metadata['status'] = status
            if completion_rate is not None:
                project_metadata['completion_rate'] = completion_rate
            
            project_metadata['last_updated'] = datetime.now().isoformat()
            
            # Store updated metadata
            self.state_manager.unified_memory.store_project_metadata(
                project_id, 
                project_metadata
            )
            logger.info(f"Updated project {project_id} to phase: {status}")
            
        except Exception as e:
            logger.error(f"Failed to update project phase for {project_id}: {e}")
