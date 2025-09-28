import logging
from core.ui import agent_log, say_system, say_success, say_error
from utils.json_utils import safe_json_extract
from schemas.plan_schema import PLAN_SCHEMA
from utils.validation_utils import validate

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

        say_system(f"🚀 Building: {project_title}")
        
        agent_log("Orchestrator", f"Starting build for '{project_title}'...")
        
        try:
            # Phase 1: Planning
            plan = self.planner.generate_plan(project_title, refined_prompt, self.state_manager.get_conversation_state("default_user").history)
            if plan:
                try:
                    validate(plan, PLAN_SCHEMA)
                except Exception as e:
                    self.logger.warning(f"Plan failed schema validation but will be used as-is. Error: {e}")
            else:
                self.logger.error(f"No plan generated, using fallback.")
                # Create a simple fallback plan
                plan = {
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
            agent_log("Planner", "Comprehensive plan generated successfully.")

            # Phase 2: Management Review
            approval = self.manager.review_plan(plan)
            if not approval.get("approved", False):
                feedback = approval.get('feedback', 'No feedback provided')
                say_error(f"Manager rejected plan: {feedback}. Aborting workflow.")
                return
            agent_log("Manager", "Plan approved and validated.")

            # Phase 3: Implementation
            implemented_files_generator = self.programmer.implement(plan, project_title)
            implemented_files = list(implemented_files_generator)
            agent_log("Programmer", f"Successfully implemented {len(implemented_files)} files.")

            # Phase 4: Quality Assurance
            qa_report_path = self.qa.test(implemented_files, plan=plan)
            agent_log("QA", f"Quality assurance completed: {qa_report_path}")

            # Phase 5: Code Review
            review_report_path = self.reviewer.review(implemented_files)
            agent_log("Reviewer", f"Code review completed: {review_report_path}")

        except Exception as e:
            say_error(f"Workflow execution failed: {e}")
            # Log the full error for debugging
            self.logger.error(f"Workflow error: {str(e)}", exc_info=True)
            return

        say_success(f"✅ {project_title} has been built successfully!")
        say_system("📁 Project files can be found in the 'projects' directory.")
        return implemented_files