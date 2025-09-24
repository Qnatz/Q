import logging
from core.ui import agent_log, say_system, say_success, say_error
from utils.json_utils import safe_json_extract
from schemas.plan_schema import PLAN_SCHEMA
from utils.validation_utils import validate

class WorkflowManager:
    def __init__(self, planner, manager, programmer, qa, reviewer):
        self.planner = planner
        self.manager = manager
        self.programmer = programmer
        self.qa = qa
        self.reviewer = reviewer
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
            plan_response = self.planner.plan(refined_prompt)
            plan = safe_json_extract(plan_response)
            if not plan or not validate(plan, PLAN_SCHEMA):
                say_error("Planner failed to return valid plan. Aborting workflow.")
                return
            agent_log("Planner", "Comprehensive plan generated successfully.")

            # Phase 2: Management Review
            approval = self.manager.review_plan(plan)
            if not approval.get("approved", False):
                feedback = approval.get('feedback', 'No feedback provided')
                say_error(f"Manager rejected plan: {feedback}. Aborting workflow.")
                return
            agent_log("Manager", "Plan approved and validated.")

            # Phase 3: Implementation
            implemented_files = self.programmer.execute(plan, project_title)
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
