# Project State Management Implementation Plan

## Goal
To implement a robust project state management system that allows for:
1.  Persisting project metadata (e.g., project name, creation date, completion rate, status).
2.  Seamless resumption of projects from any point in the workflow (ideation, planning, programming, QA).
3.  Listing all projects with their completion rates on application startup.

## Current State Analysis
*   `ConversationState` is now persisted in TinyDB (`system_state.json`), covering high-level conversation progress.
*   Implemented files are saved to `projects/<project_title-timestamp>` on the filesystem.
*   The generated plan is currently passed directly between agents and not explicitly persisted for long-term retrieval.
*   Completion rate and detailed project status are not explicitly tracked or persisted.

## Step-by-Step Implementation

### Step 1: Define Project Metadata Structure

1.  **Create `ProjectMetadata` dataclass:**
    *   Create a new file `schemas/project_schema.py`.
    *   Define a `dataclass` named `ProjectMetadata` with fields such as:
        *   `project_id: str` (unique identifier, e.g., `project_title-timestamp`)
        *   `project_name: str` (the user-friendly name)
        *   `created_at: str` (timestamp of creation)
        *   `last_updated: str` (timestamp of last update)
        *   `status: str` (e.g., "ideation", "planning", "programming", "qa", "completed", "interrupted")
        *   `completion_rate: float` (0.0 to 1.0)
        *   `plan: Optional[Dict[str, Any]]` (the generated plan, if available)
        *   `refined_prompt: str` (the refined prompt from ideation)
        *   `user_id: str` (the user who owns the project)

### Step 2: Integrate Project Metadata with `UnifiedMemory`

1.  **Add `MemoryType.PROJECT`:**
    *   In `memory/unified_memory.py`, add `PROJECT = "project"` to the `MemoryType` Enum.
2.  **Add `store_project_metadata` to `UnifiedMemory`:**
    *   In `memory/unified_memory.py`, add a method `store_project_metadata(self, metadata: ProjectMetadata)` that serializes the `ProjectMetadata` object and stores it in TinyDB (using `self.tinydb.store_state` or a new dedicated table if needed). The key should be `f"project_metadata_{metadata.project_id}"`.
3.  **Add `get_project_metadata` to `UnifiedMemory`:**
    *   In `memory/unified_memory.py`, add a method `get_project_metadata(self, project_id: str) -> Optional[ProjectMetadata]` that retrieves the serialized metadata from TinyDB and deserializes it back into a `ProjectMetadata` object.
4.  **Add `get_all_project_metadata` to `UnifiedMemory`:**
    *   In `memory/unified_memory.py`, add a method `get_all_project_metadata(self, user_id: str) -> List[ProjectMetadata]` to retrieve all project metadata for a given user.

### Step 3: Update Project Creation Flow

1.  **Modify `core/response_handler.py`:**
    *   In `initiate_build_workflow` and `_continue_ideation_workflow`, after the `project_title_with_timestamp` is determined and the `refined_prompt` is available:
        *   Create an instance of `ProjectMetadata`.
        *   Store this initial `ProjectMetadata` using `self.state_manager.unified_memory.store_project_metadata()`.
        *   Update the `ConversationState` to include the `project_id` of the newly created project.
    *   In `_save_implemented_files`, update the `last_updated` and `status` of the `ProjectMetadata` after files are saved.

### Step 4: Update Project Progress

1.  **Modify `core/workflow_manager.py`:**
    *   **Store Plan:** After `plan = self.planner.generate_plan(...)` is successful, update the `ProjectMetadata` to include the `plan` and set `status` to "planning_complete".
    *   **Update Status during Programming:** Before calling `self.programmer.implement`, update the `ProjectMetadata` status to "programming".
    *   **Update Status during QA/Review:** Similarly, update the `ProjectMetadata` status to "qa" and "review" respectively.
    *   **Update Completion Rate:** Introduce a mechanism to estimate and update the `completion_rate` at various stages (e.g., 25% after planning, 75% after programming, 100% after QA/review).

### Step 5: Load Project List on Startup

1.  **Modify `main.py` or `core/orchestrator.py`:**
    *   On application startup, call `self.state_manager.unified_memory.get_all_project_metadata(user_id)` to retrieve all projects.
    *   Display this list to the user, including project name, status, and completion rate.
    *   Allow the user to select a project to resume.

### Step 6: Resume Project Workflow

1.  **Modify `core/orchestrator.py`:**
    *   When a user selects a project to resume:
        *   Load the `ProjectMetadata` for that project using `self.state_manager.unified_memory.get_project_metadata()`.
        *   Reconstruct the `ConversationState` for that project, populating it with the `refined_prompt`, `plan`, and current `status` from the `ProjectMetadata`.
        *   Set `state.current_phase` based on the project's `status` to guide the `Orchestrator` to the correct point in the workflow.
        *   If the plan is available, pass it to the `workflow_manager` to continue from the appropriate phase.

## Considerations
*   **Error Handling:** Ensure robust error handling at each step, especially during serialization/deserialization and database operations.
*   **User Feedback:** Provide clear feedback to the user about project status, saving, and loading.
*   **Concurrency:** If multiple users or agents can interact with projects, consider concurrency issues.
*   **Data Migration:** If the schema changes, plan for data migration.

This plan provides a comprehensive approach to managing project state for seamless resumption.